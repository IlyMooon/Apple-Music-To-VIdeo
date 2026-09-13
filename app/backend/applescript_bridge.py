"""
Bridge AppleScript pour macOS.
Interagit directement avec l'application native Musique (Music.app)
avec gestion robuste des timeouts, détection des permissions TCC (Automatisation)
et extraction vectorisée haute performance.
"""

import subprocess
import html
import re
from typing import List, Optional, Tuple
from .bridge_interface import BaseMusicBridge, TrackInfo, VideoMatch


class AppleScriptBridge(BaseMusicBridge):
    """Contrôleur AppleScript pour l'application Musique sur macOS."""

    def __init__(self, default_timeout: float = 3.5):
        self.default_timeout = default_timeout
        self._permission_cached: Optional[bool] = None

    def run_script(self, script: str, timeout: Optional[float] = None) -> Tuple[bool, str]:
        """
        Exécute un script AppleScript via osascript avec timeout strict.
        Retourne (succès: bool, sortie_ou_erreur: str).
        """
        actual_timeout = timeout if timeout is not None else self.default_timeout
        try:
            res = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=actual_timeout,
            )
            if res.returncode == 0:
                return True, res.stdout.strip()
            stderr = res.stderr.strip()
            return False, stderr
        except subprocess.TimeoutExpired:
            return False, "TIMEOUT: L'application Musique ne répond pas ou attend une autorisation macOS."
        except Exception as e:
            return False, f"ERREUR: {str(e)}"

    def check_availability(self) -> Tuple[bool, str]:
        """
        Vérifie si Music.app est accessible et si les autorisations Apple Events sont accordées.
        """
        script = """
        tell application "Music"
            return name
        end tell
        """
        success, output = self.run_script(script, timeout=2.5)
        if success and "Music" in output:
            self._permission_cached = True
            return True, "Application Musique connectée et autorisée."

        self._permission_cached = False
        if "TIMEOUT" in output:
            return False, "En attente d'autorisation macOS (Vérifiez les boîtes de dialogue ou Réglages Système)."
        if "-1743" in output or "Not authorized to send Apple events" in output:
            return False, "Autorisation refusée: Vous devez autoriser le contrôle de Musique dans Réglages Système > Confidentialité et sécurité > Automatisation."
        if "-600" in output:
            return False, "L'application Musique est fermée ou en cours d'initialisation."

        return False, f"Impossible de joindre Musique: {output}"

    @staticmethod
    def open_automation_settings() -> None:
        """Ouvre directement le panneau Réglages Système macOS dédié aux permissions d'automatisation."""
        try:
            subprocess.run(
                ["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_Automation"],
                check=False
            )
        except Exception as e:
            print(f"Erreur ouverture réglages: {e}")

    @staticmethod
    def launch_music_app() -> bool:
        """Lance ou active l'application Musique."""
        try:
            subprocess.run(["open", "-a", "Music"], check=False)
            return True
        except Exception:
            return False

    def _sanitize(self, text: str) -> str:
        """Échappe les guillemets et antislashs pour injection sécurisée dans AppleScript."""
        if not text:
            return ""
        return text.replace("\\", "\\\\").replace('"', '\\"')

    def get_playlists(self) -> List[str]:
        """
        Récupère la liste des playlists utilisateur (Playlists créées ou enregistrées).
        Filtre les listes système invisibles.
        """
        script = """
        tell application "Music"
            try
                set pNames to name of every user playlist
                set AppleScript's text item delimiters to "|||"
                return pNames as text
            on error
                set pNames to name of every playlist
                set AppleScript's text item delimiters to "|||"
                return pNames as text
            end try
        end tell
        """
        success, output = self.run_script(script, timeout=4.0)
        if not success or not output:
            return []

        playlists = [p.strip() for p in output.split("|||") if p.strip()]
        # Filtrer les playlists système internes non pertinentes
        ignore_system = {"Library", "Bibliothèque", "Musique", "Music", "Downloaded", "Téléchargé"}
        filtered = [p for p in playlists if p not in ignore_system]
        return filtered if filtered else playlists

    def get_playlist_tracks(self, playlist_name: str) -> List[TrackInfo]:
        """
        Récupère les pistes d'une playlist avec extraction vectorisée rapide.
        """
        safe_name = self._sanitize(playlist_name)
        script = f"""
        tell application "Music"
            try
                tell playlist "{safe_name}"
                    set tNames to name of tracks
                    set tArtists to artist of tracks
                    set tAlbums to album of tracks
                    set tIds to id of tracks
                    set tKinds to media kind of tracks
                end tell
                
                set cnt to count of tNames
                set resList to {{}}
                repeat with i from 1 to cnt
                    set trkName to item i of tNames
                    set trkArtist to item i of tArtists
                    set trkAlbum to item i of tAlbums
                    set trkId to item i of tIds
                    set trkKind to ""
                    try
                        set trkKind to (item i of tKinds) as text
                    end try
                    set end of resList to (trkName & "§§§" & trkArtist & "§§§" & trkAlbum & "§§§" & trkId & "§§§" & trkKind)
                end repeat
                
                set AppleScript's text item delimiters to "¶¶¶"
                return resList as text
            on error errMsg
                return "ERR:" & errMsg
            end try
        end tell
        """
        success, output = self.run_script(script, timeout=6.0)
        if not success or not output or output.startswith("ERR:"):
            return []

        tracks: List[TrackInfo] = []
        raw_items = output.split("¶¶¶")
        for raw in raw_items:
            parts = raw.split("§§§")
            if len(parts) >= 2:
                name = parts[0].strip()
                artist = parts[1].strip() if len(parts) > 1 else ""
                album = parts[2].strip() if len(parts) > 2 else ""
                track_id = parts[3].strip() if len(parts) > 3 else ""
                kind = parts[4].strip() if len(parts) > 4 else "song"
                if name:
                    tracks.append(TrackInfo(
                        name=name,
                        artist=artist,
                        album=album,
                        track_id=track_id,
                        media_kind=kind
                    ))
        return tracks

    def create_playlist(self, name: str) -> bool:
        """Crée une nouvelle playlist utilisateur si elle n'existe pas déjà."""
        safe_name = self._sanitize(name)
        script = f"""
        tell application "Music"
            if not (exists user playlist "{safe_name}") then
                make new user playlist with properties {{name:"{safe_name}"}}
                return "CREATED"
            else
                return "EXISTS"
            end if
        end tell
        """
        success, output = self.run_script(script, timeout=3.5)
        return success and ("CREATED" in output or "EXISTS" in output)

    def find_local_video(self, track: TrackInfo) -> Optional[VideoMatch]:
        """
        Vérifie si un clip vidéo correspondant existe déjà dans la bibliothèque locale Music.
        Exige strictement media kind is music video ET la correspondance de l'artiste (seuil >= 0.78).
        """
        safe_title = self._sanitize(track.clean_name())
        
        script = f"""
        tell application "Music"
            try
                set candidateTracks to (every track of library playlist 1 whose media kind is music video and name contains "{safe_title}")
                set res to ""
                repeat with trk in candidateTracks
                    set vName to name of trk
                    set vArtist to artist of trk
                    set vId to id of trk as string
                    set res to res & vName & "§§§" & vArtist & "§§§" & vId & "¶¶¶"
                end repeat
                return res
            on error
                return ""
            end try
        end tell
        """
        success, output = self.run_script(script, timeout=3.5)
        if success and output and "§§§" in output:
            from .catalog_search import CatalogSearchService
            cs = CatalogSearchService()
            for entry in output.split("¶¶¶"):
                parts = entry.split("§§§")
                if len(parts) >= 3:
                    v_name = parts[0].strip()
                    v_artist = parts[1].strip()
                    v_id = parts[2].strip()
                    title_sim = cs._compute_similarity(track.clean_name(), v_name)
                    artist_sim = cs._compute_artist_similarity(track.artist, v_artist)
                    if title_sim >= 0.80 and artist_sim >= 0.78:
                        return VideoMatch(
                            track_name=v_name,
                            artist_name=v_artist if v_artist else track.artist,
                            track_id=v_id,
                            source="local",
                            confidence_score=round((title_sim * 0.50) + (artist_sim * 0.50), 2)
                        )
        return None

    def add_video_to_playlist(self, playlist_name: str, video_match: VideoMatch) -> bool:
        """
        Ajoute un clip vidéo à la playlist de destination de manière garantie et sans doublon.
        1. Vérifie si le clip existe déjà dans la playlist cible -> si oui, terminé immédiatement.
        2. Vérifie si le clip existe déjà dans la bibliothèque locale -> le duplique directement sans ouvrir le lecteur (zéro plein écran, zéro doublon en bibliothèque).
        3. Si absent de la bibliothèque -> charge discrètement via open location, pause immédiate, duplication vers bibliothèque puis vers la playlist cible.
        """
        safe_playlist = self._sanitize(playlist_name)
        # Obtenir également le nom épuré sans mentions parasites
        clean_title = re.sub(r"\s*[\(\[][^\)\]]*(video|clip|official|4k|hd|soundtrack)[^\)\]]*[\)\]]", "", video_match.track_name, flags=re.IGNORECASE).strip()
        safe_clean_title = self._sanitize(clean_title if clean_title else video_match.track_name)
        safe_full_title = self._sanitize(video_match.track_name)

        # ÉTAPE 1 : Vérifier la bibliothèque locale (library playlist 1)
        # Si le clip est déjà dans la bibliothèque, le dupliquer directement sans ouvrir le lecteur
        track_id_clause = f"or id is {video_match.track_id}" if video_match.track_id and video_match.track_id.isdigit() else ""
        script_check = f"""
        tell application "Music"
            try
                -- S'assurer que la playlist cible existe
                if not (exists user playlist "{safe_playlist}") then
                    make new user playlist with properties {{name:"{safe_playlist}"}}
                end if

                set targetTrk to missing value
                set candidateList to (every track of library playlist 1 whose (name contains "{safe_clean_title}" or name is "{safe_full_title}" {track_id_clause}) and media kind is music video)
                if (count of candidateList) > 0 then
                    set targetTrk to item 1 of candidateList
                end if

                if targetTrk is not missing value then
                    set targetName to name of targetTrk
                    set alreadyIn to (count of (every track of user playlist "{safe_playlist}" whose name is targetName))
                    if alreadyIn is 0 then
                        duplicate targetTrk to user playlist "{safe_playlist}"
                        return "OK_ADDED_FROM_LIBRARY"
                    else
                        return "OK_ALREADY_IN_PLAYLIST"
                    end if
                end if
                return "NOT_IN_LIBRARY"
            on error errMsg
                return "ERR:" & errMsg
            end try
        end tell
        """
        success, out = self.run_script(script_check, timeout=4.0)
        if success and ("OK_ADDED_FROM_LIBRARY" in out or "OK_ALREADY_IN_PLAYLIST" in out):
            return True

        # ÉTAPE 2 : Le clip n'est pas encore dans la bibliothèque locale -> Chargement Apple Music
        if video_match.video_url:
            raw_url = video_match.video_url
            if raw_url.startswith("https://"):
                itmss_url = raw_url.replace("https://", "itmss://")
            elif raw_url.startswith("http://"):
                itmss_url = raw_url.replace("http://", "itmss://")
            else:
                itmss_url = raw_url

            safe_itmss_url = self._sanitize(itmss_url)

            script_stream = f"""
            tell application "Music"
                try
                    -- 1. S'assurer que la playlist cible existe
                    if not (exists user playlist "{safe_playlist}") then
                        make new user playlist with properties {{name:"{safe_playlist}"}}
                    end if

                    -- 2. Couper le son temporairement pour éviter le bruit
                    set prevMute to mute
                    set mute to true

                    -- 3. Charger le flux multimédia
                    open location "{safe_itmss_url}"

                    -- 4. Détecter le chargement et PAUSER IMMÉDIATEMENT pour empêcher le plein écran
                    set isLoaded to false
                    repeat with stepIndex from 1 to 8
                        delay 0.25
                        if exists current track then
                            pause
                            try
                                set full screen to false
                            end try
                            set isLoaded to true
                            exit repeat
                        end if
                    end repeat

                    -- Restaurer le son
                    set mute to prevMute

                    if not isLoaded then
                        return "ERR:Timeout loading current track"
                    end if

                    -- 5. Vérifier formellement que c'est un clip vidéo
                    set curKind to (media kind of current track) as text
                    if curKind does not contain "video" then
                        pause
                        return "ERR:Current track is not a video (" & curKind & ")"
                    end if

                    -- 6. Ajouter à la bibliothèque de l'utilisateur
                    try
                        duplicate current track to source 1
                    end try

                    -- 7. Dupliquer vers la playlist cible depuis library playlist 1
                    delay 0.5
                    set candidateList to (every track of library playlist 1 whose (name contains "{safe_clean_title}" or name is "{safe_full_title}") and media kind is music video)
                    if (count of candidateList) > 0 then
                        set trkToAdd to item 1 of candidateList
                        set targetName to name of trkToAdd
                        set alreadyIn to (count of (every track of user playlist "{safe_playlist}" whose name is targetName))
                        if alreadyIn is 0 then
                            duplicate trkToAdd to user playlist "{safe_playlist}"
                        end if
                    end if

                    pause
                    try
                        set full screen to false
                    end try
                    return "OK"
                on error errMsg
                    try
                        pause
                        set full screen to false
                    end try
                    return "ERR:" & errMsg
                end try
            end tell
            """
            success, output = self.run_script(script_stream, timeout=7.0)
            self.run_script('tell application "Music" to pause', timeout=1.5)
            if success and "OK" in output:
                return True
            print(f"[AppleScriptBridge] Résultat ajout vidéo: {output}")
            return False

        return False

    def clean_playlist_non_videos(self, playlist_name: str) -> int:
        """
        Supprime toutes les pistes qui ne sont pas des clips vidéo de la playlist spécifiée.
        Garantit que la playlist finale contient exclusivement des clips vidéo.
        """
        safe_playlist = self._sanitize(playlist_name)
        script = f"""
        tell application "Music"
            try
                if exists user playlist "{safe_playlist}" then
                    tell user playlist "{safe_playlist}"
                        set badTracks to (every track whose media kind is not music video)
                        set delCount to count of badTracks
                        repeat with t in badTracks
                            delete t
                        end repeat
                        return (delCount as text)
                    end tell
                end if
                return "0"
            on error
                return "0"
            end try
        end tell
        """
        success, out = self.run_script(script, timeout=4.0)
        try:
            return int(out) if success and out.isdigit() else 0
        except Exception:
            return 0

