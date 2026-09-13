"""
Module d'intégration avec l'API officielle Apple Music (MusicKit).
Permet de requêter directement l'API REST Apple Music si un Developer Token (JWT)
et un Music User Token sont configurés.
"""

from typing import List, Optional, Tuple, Dict, Any
import requests

from .bridge_interface import BaseMusicBridge, TrackInfo, VideoMatch


class MusicKitBridge(BaseMusicBridge):
    """Bridge vers l'API Apple Music / MusicKit REST."""

    BASE_URL = "https://api.music.apple.com/v1"

    def __init__(self, developer_token: str, user_token: str = "", storefront: str = "fr"):
        self.developer_token = developer_token
        self.user_token = user_token
        self.storefront = storefront

    @property
    def is_configured(self) -> bool:
        return bool(self.developer_token.strip())

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.developer_token}",
            "Content-Type": "application/json"
        }
        if self.user_token:
            headers["Music-User-Token"] = self.user_token
        return headers

    def check_availability(self) -> Tuple[bool, str]:
        if not self.is_configured:
            return False, "Aucun Developer Token MusicKit n'est renseigné."
        try:
            resp = requests.get(
                f"{self.BASE_URL}/catalog/{self.storefront}/songs/1440857781",
                headers=self._headers(),
                timeout=4.0
            )
            if resp.status_code == 200:
                return True, "MusicKit API connectée avec succès."
            return False, f"Erreur d'authentification MusicKit (HTTP {resp.status_code})."
        except Exception as e:
            return False, f"Impossible de contacter l'API Apple Music: {e}"

    def get_playlists(self) -> List[str]:
        if not self.user_token:
            return []
        try:
            resp = requests.get(
                f"{self.BASE_URL}/me/library/playlists",
                headers=self._headers(),
                timeout=5.0
            )
            if resp.status_code == 200:
                data = resp.json()
                return [item["attributes"]["name"] for item in data.get("data", [])]
        except Exception as e:
            print(f"[MusicKit] Erreur récupération playlists: {e}")
        return []

    def get_playlist_tracks(self, playlist_name: str) -> List[TrackInfo]:
        # Nécessite un ID de playlist cloud, retourne vide si non trouvé
        return []

    def create_playlist(self, name: str) -> bool:
        if not self.user_token:
            return False
        try:
            payload = {
                "attributes": {
                    "name": name,
                    "description": "Créée par Apple Music To Video"
                }
            }
            resp = requests.post(
                f"{self.BASE_URL}/me/library/playlists",
                headers=self._headers(),
                json=payload,
                timeout=5.0
            )
            return resp.status_code in (200, 201)
        except Exception as e:
            print(f"[MusicKit] Erreur création playlist: {e}")
            return False

    def add_video_to_playlist(self, playlist_name: str, video_match: VideoMatch) -> bool:
        # L'ajout via API nécessite l'ID de la playlist de l'utilisateur
        return False

    def find_local_video(self, track: TrackInfo) -> Optional[VideoMatch]:
        return None

    def search_catalog_music_video(self, track: TrackInfo) -> Optional[VideoMatch]:
        """Recherche spécifique d'un clip vidéo via l'API MusicKit Catalog."""
        if not self.is_configured:
            return None
        query = f"{track.clean_name()} {track.artist}".strip()
        try:
            params = {
                "term": query,
                "types": "music-videos",
                "limit": 3
            }
            resp = requests.get(
                f"{self.BASE_URL}/catalog/{self.storefront}/search",
                headers=self._headers(),
                params=params,
                timeout=5.0
            )
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("results", {}).get("music-videos", {}).get("data", [])
                if items:
                    first = items[0]
                    attr = first.get("attributes", {})
                    art_url = attr.get("artwork", {}).get("url", "")
                    if art_url:
                        art_url = art_url.replace("{w}x{h}", "600x600")
                    return VideoMatch(
                        track_name=attr.get("name", ""),
                        artist_name=attr.get("artistName", ""),
                        video_url=attr.get("url", ""),
                        preview_url=attr.get("previews", [{}])[0].get("hlsUrl", ""),
                        artwork_url=art_url,
                        track_id=first.get("id", ""),
                        source="musickit",
                        confidence_score=0.95
                    )
        except Exception as e:
            print(f"[MusicKit] Erreur recherche: {e}")
        return None
