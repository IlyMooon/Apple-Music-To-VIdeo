"""
Worker asynchrone pour la conversion des morceaux en clips vidéo.
S'exécute dans un thread séparé (QThread) pour garantir la fluidité de l'interface
et gère l'annulation réactive en temps réel.
"""

import time
from typing import List, Optional, Dict, Any
from PyQt6.QtCore import QThread, pyqtSignal

from .bridge_interface import BaseMusicBridge, TrackInfo, VideoMatch
from .catalog_search import CatalogSearchService
from .musickit_bridge import MusicKitBridge


class MusicVideoConverterWorker(QThread):
    """Moteur de traitement asynchrone de la playlist."""

    # Signaux émis vers l'interface graphique
    sig_started = pyqtSignal(int)                         # total tracks
    sig_progress = pyqtSignal(int, int, object)           # current, total, TrackInfo
    sig_item_processed = pyqtSignal(object, str, object, str)  # TrackInfo, status, VideoMatch or None, reason
    sig_finished = pyqtSignal(dict)                       # summary dict
    sig_log = pyqtSignal(str, str)                        # message, level (info/success/warning/error)
    sig_error = pyqtSignal(str)                           # error critical message

    def __init__(
        self,
        bridge: BaseMusicBridge,
        catalog_search: CatalogSearchService,
        musickit_bridge: Optional[MusicKitBridge],
        source_playlist: str,
        destination_playlist: str,
        search_local_first: bool = True,
        delay_ms: int = 180,
        parent=None,
    ):
        super().__init__(parent)
        self.bridge = bridge
        self.catalog_search = catalog_search
        self.musickit_bridge = musickit_bridge
        self.source_playlist = source_playlist
        self.destination_playlist = destination_playlist
        self.search_local_first = search_local_first
        self.delay_ms = delay_ms

        self._is_cancelled = False

    def cancel(self) -> None:
        """Déclenche l'annulation coopérative du traitement."""
        self._is_cancelled = True
        self.sig_log.emit("Demande d'annulation reçue... Arrêt en cours.", "warning")

    def run(self) -> None:
        """Boucle principale d'exécution du QThread."""
        start_time = time.time()
        self.sig_log.emit(f"Démarrage de l'analyse : '{self.source_playlist}' → '{self.destination_playlist}'", "info")

        # 1. Vérifier ou créer la playlist de destination
        try:
            self.bridge.create_playlist(self.destination_playlist)
            # Nettoyage préventif : retirer toute piste audio résiduelle
            purged = self.bridge.clean_playlist_non_videos(self.destination_playlist)
            if purged > 0:
                self.sig_log.emit(f"🧹 Nettoyage : {purged} piste(s) non-vidéo retirée(s) de la playlist.", "info")
        except Exception as e:
            self.sig_log.emit(f"Avertissement lors de la création/nettoyage de la playlist: {e}", "warning")

        # 2. Récupérer les pistes de la source
        try:
            tracks: List[TrackInfo] = self.bridge.get_playlist_tracks(self.source_playlist)
        except Exception as e:
            self.sig_error.emit(f"Impossible de lire les pistes de '{self.source_playlist}': {e}")
            return

        total_tracks = len(tracks)
        if total_tracks == 0:
            self.sig_finished.emit({
                "total": 0,
                "added": 0,
                "skipped": 0,
                "cancelled": False,
                "duration": round(time.time() - start_time, 1),
                "items": []
            })
            return

        self.sig_started.emit(total_tracks)

        added_count = 0
        skipped_count = 0
        processed_items: List[Dict[str, Any]] = []

        for index, track in enumerate(tracks, start=1):
            if self._is_cancelled:
                self.sig_log.emit(f"Processus interrompu à la piste {index}/{total_tracks}.", "warning")
                break

            # Notification de progression
            self.sig_progress.emit(index, total_tracks, track)
            self.sig_log.emit(f"[{index}/{total_tracks}] Recherche clip pour : {track.name} - {track.artist}", "info")

            video_match: Optional[VideoMatch] = None

            # Étape A : Recherche locale si demandée
            if self.search_local_first:
                try:
                    video_match = self.bridge.find_local_video(track)
                except Exception as e:
                    self.sig_log.emit(f"Erreur recherche locale: {e}", "warning")

            # Étape B : Recherche catalogue si pas de résultat local
            if not video_match and self.musickit_bridge and self.musickit_bridge.is_configured:
                try:
                    video_match = self.musickit_bridge.search_catalog_music_video(track)
                except Exception:
                    video_match = None

            if not video_match:
                try:
                    video_match = self.catalog_search.search_music_video(track)
                except Exception as e:
                    self.sig_log.emit(f"Erreur recherche catalogue: {e}", "warning")

            # Étape C : Traitement du résultat (SEULS les clips vidéo confirmés sont ajoutés)
            if video_match:
                try:
                    success = self.bridge.add_video_to_playlist(self.destination_playlist, video_match)
                    if success:
                        added_count += 1
                        status = "added"
                        reason = f"Clip officiel ({video_match.source}) : {video_match.track_name}"
                        self.sig_log.emit(f"✓ Ajouté : {video_match.track_name} ({video_match.artist_name})", "success")
                    else:
                        skipped_count += 1
                        status = "skipped"
                        reason = "Piste rejetée : seul le format clip vidéo est accepté"
                        self.sig_log.emit(f"✗ Rejeté : {video_match.track_name} (non vidéo)", "warning")
                except Exception as e:
                    skipped_count += 1
                    status = "error"
                    reason = f"Clip trouvé mais échec d'ajout : {str(e)}"
                    self.sig_log.emit(f"✗ Erreur d'ajout : {e}", "error")
            else:
                skipped_count += 1
                status = "skipped"
                reason = "Aucun clip vidéo officiel correspondant (seuil strict)"
                self.sig_log.emit(f"- Ignoré : Aucun clip pour {track.name}", "info")

            item_record = {
                "track": track,
                "status": status,
                "video_match": video_match,
                "reason": reason
            }
            processed_items.append(item_record)
            self.sig_item_processed.emit(track, status, video_match, reason)

            # Temporisation pour micro-animation et respect des quotas réseau
            if self.delay_ms > 0:
                self.msleep(self.delay_ms)

        duration = round(time.time() - start_time, 1)
        summary = {
            "total": total_tracks,
            "processed": len(processed_items),
            "added": added_count,
            "skipped": skipped_count,
            "cancelled": self._is_cancelled,
            "duration": duration,
            "items": processed_items,
        }
        self.sig_finished.emit(summary)
        self.sig_log.emit(
            f"Traitement terminé en {duration}s : {added_count} clips ajoutés, {skipped_count} ignorés.",
            "success" if not self._is_cancelled else "warning"
        )
