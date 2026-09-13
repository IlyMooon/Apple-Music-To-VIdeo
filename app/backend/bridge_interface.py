"""
Définitions des structures de données et de l'interface abstraite
pour les fournisseurs d'accès à la bibliothèque Apple Music.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any


@dataclass
class TrackInfo:
    """Représentation d'une piste audio extraite d'une playlist."""
    name: str
    artist: str
    album: str = ""
    duration: float = 0.0
    track_id: str = ""
    media_kind: str = "song"

    def clean_name(self) -> str:
        """Nettoie le titre pour faciliter la recherche de clip (retrait des mentions superflues)."""
        import re
        title = self.name
        # Retrait des mentions du type (feat. ...), [Official Video], (Remastered 2011), etc.
        patterns = [
            r"\(feat\.[^\)]+\)",
            r"\(ft\.[^\)]+\)",
            r"\[feat\.[^\]]+\]",
            r"\[ft\.[^\]]+\]",
            r"\(with[^\)]+\)",
            r"\[remastered[^\]]*\]",
            r"\(remastered[^\)]*\)",
            r"\(deluxe[^\)]*\)",
            r"\(bonus track[^\)]*\)",
            r"\[bonus track[^\]]*\]",
            r"- live$",
            r"- radio edit$",
        ]
        for p in patterns:
            title = re.sub(p, "", title, flags=re.IGNORECASE)
        return title.strip()


@dataclass
class VideoMatch:
    """Représente un clip vidéo trouvé pour une piste audio."""
    track_name: str
    artist_name: str
    video_url: str = ""
    preview_url: str = ""
    artwork_url: str = ""
    track_id: str = ""
    source: str = "itunes_catalog"  # "local", "itunes_catalog", "musickit", "mock"
    confidence_score: float = 1.0
    extra_metadata: Dict[str, Any] = field(default_factory=dict)


class BaseMusicBridge(ABC):
    """Interface abstraite définissant les capacités requises pour dialoguer avec Music."""

    @abstractmethod
    def check_availability(self) -> Tuple[bool, str]:
        """
        Vérifie si le bridge est opérationnel.
        Retourne (is_ready, message_explicatif).
        """
        pass

    @abstractmethod
    def get_playlists(self) -> List[str]:
        """Retourne la liste des noms des playlists utilisateur disponibles."""
        pass

    @abstractmethod
    def get_playlist_tracks(self, playlist_name: str) -> List[TrackInfo]:
        """Retourne la liste des pistes contenues dans la playlist spécifiée."""
        pass

    @abstractmethod
    def create_playlist(self, name: str) -> bool:
        """Crée une nouvelle playlist avec le nom donné si elle n'existe pas déjà."""
        pass

    @abstractmethod
    def add_video_to_playlist(self, playlist_name: str, video_match: VideoMatch) -> bool:
        """Ajoute le clip vidéo trouvé à la playlist cible."""
        pass

    @abstractmethod
    def find_local_video(self, track: TrackInfo) -> Optional[VideoMatch]:
        """Cherche si un clip vidéo est déjà présent dans la bibliothèque locale Music.app."""
        pass

    def clean_playlist_non_videos(self, playlist_name: str) -> int:
        """Supprime les pistes non-vidéo de la playlist. Retourne le nombre de pistes purgées."""
        return 0
