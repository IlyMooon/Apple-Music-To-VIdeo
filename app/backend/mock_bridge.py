"""
Bridge de simulation (Mock) pour le Mode Démo.
Permet de tester immédiatement l'interface utilisateur, les animations,
la barre de progression et le tiroir de résumé sans dépendre de l'application Musique.
"""

from typing import List, Optional, Tuple, Dict
from .bridge_interface import BaseMusicBridge, TrackInfo, VideoMatch


class MockMusicBridge(BaseMusicBridge):
    """Fournisseur de données factices réalistes pour démonstrations et tests instantanés."""

    SAMPLE_PLAYLISTS: Dict[str, List[TrackInfo]] = {
        "🔥 Hits Essentiels 2024": [
            TrackInfo("Around the World", "Daft Punk", "Homework", 240, "mock_1"),
            TrackInfo("Blinding Lights", "The Weeknd", "After Hours", 200, "mock_2"),
            TrackInfo("Levitating", "Dua Lipa", "Future Nostalgia", 203, "mock_3"),
            TrackInfo("Papaoutai", "Stromae", "Racine Carrée", 232, "mock_4"),
            TrackInfo("Balance ton quoi", "Angèle", "Brol", 198, "mock_5"),
            TrackInfo("D.A.N.C.E.", "Justice", "Cross", 242, "mock_6"),
            TrackInfo("Bohemian Rhapsody", "Queen", "A Night at the Opera", 354, "mock_7"),
            TrackInfo("bad guy", "Billie Eilish", "WHEN WE ALL FALL ASLEEP", 194, "mock_8"),
            TrackInfo("Starboy", "The Weeknd", "Starboy", 230, "mock_9"),
            TrackInfo("Midnight City", "M83", "Hurry Up, We're Dreaming", 243, "mock_10"),
            TrackInfo("Une Piste Inconnue Sans Clip", "Artiste Fantôme", "Album Mystère", 180, "mock_11"),
            TrackInfo("Autre Titre Rare Sans Vidéo", "Groupe Indé Local", "Demo Tape", 150, "mock_12"),
        ],
        "⚡ French Touch & Electro": [
            TrackInfo("Da Funk", "Daft Punk", "Homework", 328, "mock_20"),
            TrackInfo("Genesis", "Justice", "Cross", 234, "mock_21"),
            TrackInfo("Nightcall", "Kavinsky", "OutRun", 259, "mock_22"),
            TrackInfo("Safe and Sound", "Justice", "Woman", 345, "mock_23"),
            TrackInfo("Intro", "The xx", "xx", 127, "mock_24"),
        ],
        "🌙 Découvertes Nocturnes": [
            TrackInfo("Save Your Tears", "The Weeknd", "After Hours", 215, "mock_30"),
            TrackInfo("Get Lucky", "Daft Punk", "Random Access Memories", 369, "mock_31"),
            TrackInfo("Physical", "Dua Lipa", "Future Nostalgia", 193, "mock_32"),
        ]
    }

    def __init__(self):
        self._playlists = dict(self.SAMPLE_PLAYLISTS)

    def check_availability(self) -> Tuple[bool, str]:
        return True, "Mode Démo actif (bibliothèque de démonstration prête)."

    def get_playlists(self) -> List[str]:
        return list(self._playlists.keys())

    def get_playlist_tracks(self, playlist_name: str) -> List[TrackInfo]:
        return self._playlists.get(playlist_name, [])

    def create_playlist(self, name: str) -> bool:
        if name not in self._playlists:
            self._playlists[name] = []
        return True

    def add_video_to_playlist(self, playlist_name: str, video_match: VideoMatch) -> bool:
        if playlist_name not in self._playlists:
            self._playlists[playlist_name] = []
        mock_track = TrackInfo(
            name=video_match.track_name,
            artist=video_match.artist_name,
            album="Music Video",
            media_kind="music video"
        )
        self._playlists[playlist_name].append(mock_track)
        return True

    def find_local_video(self, track: TrackInfo) -> Optional[VideoMatch]:
        # Simuler quelques vidéos trouvées localement
        if "Daft Punk" in track.artist:
            return VideoMatch(
                track_name=track.name,
                artist_name=track.artist,
                video_url="https://music.apple.com/fr/music-video/around-the-world/1600590258",
                preview_url="https://video-ssl.itunes.apple.com/itunes-assets/Video122/v4/06/5f/b9/065fb9f6-ca62-4e37-2358-96143b72dd89/mzvf_524760672341937094.1920w.h264lc.U.p.m4v",
                artwork_url="https://is1-ssl.mzstatic.com/image/thumb/Video122/v4/b9/ef/a4/b9efa412-018a-6941-b784-d269783e46e4/dj.uqlvbbjh.jpg/600x600bb.jpg",
                source="local",
                confidence_score=1.0
            )
        return None

    def clean_playlist_non_videos(self, playlist_name: str) -> int:
        if playlist_name in self._playlists:
            before = len(self._playlists[playlist_name])
            self._playlists[playlist_name] = [t for t in self._playlists[playlist_name] if t.media_kind == "music video"]
            return before - len(self._playlists[playlist_name])
        return 0

