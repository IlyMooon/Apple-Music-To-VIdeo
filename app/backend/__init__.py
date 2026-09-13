"""
Couche backend et bridges d'interaction avec Apple Music.
"""

from .bridge_interface import BaseMusicBridge, TrackInfo, VideoMatch
from .applescript_bridge import AppleScriptBridge
from .catalog_search import CatalogSearchService
from .musickit_bridge import MusicKitBridge
from .mock_bridge import MockMusicBridge

__all__ = [
    "BaseMusicBridge",
    "TrackInfo",
    "VideoMatch",
    "AppleScriptBridge",
    "CatalogSearchService",
    "MusicKitBridge",
    "MockMusicBridge",
]
