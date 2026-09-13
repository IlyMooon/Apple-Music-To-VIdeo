"""
Asynchronous worker for converting tracks to music videos.
Runs in a background QThread to ensure UI responsiveness
and handles cooperative real-time cancellation.
"""

import time
from typing import List, Optional, Dict, Any
from PyQt6.QtCore import QThread, pyqtSignal

from .bridge_interface import BaseMusicBridge, TrackInfo, VideoMatch
from .catalog_search import CatalogSearchService
from .musickit_bridge import MusicKitBridge


class MusicVideoConverterWorker(QThread):
    """Background engine processing the playlist conversion."""

    # UI Signals
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
        """Trigger cooperative cancellation."""
        self._is_cancelled = True
        self.sig_log.emit("Cancellation request received... Stopping.", "warning")

    def run(self) -> None:
        """Main QThread execution loop."""
        start_time = time.time()
        self.sig_log.emit(f"Starting analysis: '{self.source_playlist}' → '{self.destination_playlist}'", "info")

        # 1. Create target playlist if needed and purge any residual non-videos
        try:
            self.bridge.create_playlist(self.destination_playlist)
            purged = self.bridge.clean_playlist_non_videos(self.destination_playlist)
            if purged > 0:
                self.sig_log.emit(f"🧹 Cleanup: {purged} non-video track(s) removed from playlist.", "info")
        except Exception as e:
            self.sig_log.emit(f"Warning during playlist creation/cleanup: {e}", "warning")

        # 2. Retrieve source tracks
        try:
            tracks: List[TrackInfo] = self.bridge.get_playlist_tracks(self.source_playlist)
        except Exception as e:
            self.sig_error.emit(f"Unable to read tracks from '{self.source_playlist}': {e}")
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
                self.sig_log.emit(f"Process interrupted at track {index}/{total_tracks}.", "warning")
                break

            # Progress notification
            self.sig_progress.emit(index, total_tracks, track)
            self.sig_log.emit(f"[{index}/{total_tracks}] Searching video for: {track.name} - {track.artist}", "info")

            video_match: Optional[VideoMatch] = None

            # Step A: Local search if enabled
            if self.search_local_first:
                try:
                    video_match = self.bridge.find_local_video(track)
                except Exception as e:
                    self.sig_log.emit(f"Local search error: {e}", "warning")

            # Step B: Catalog search if not found locally
            if not video_match and self.musickit_bridge and self.musickit_bridge.is_configured:
                try:
                    video_match = self.musickit_bridge.search_catalog_music_video(track)
                except Exception:
                    video_match = None

            if not video_match:
                try:
                    video_match = self.catalog_search.search_music_video(track)
                except Exception as e:
                    self.sig_log.emit(f"Catalog search error: {e}", "warning")

            # Step C: Result processing (ONLY strictly verified music videos are added)
            if video_match:
                try:
                    success = self.bridge.add_video_to_playlist(self.destination_playlist, video_match)
                    if success:
                        added_count += 1
                        status = "added"
                        reason = f"Official music video ({video_match.source}): {video_match.track_name}"
                        self.sig_log.emit(f"✓ Added: {video_match.track_name} ({video_match.artist_name})", "success")
                    else:
                        skipped_count += 1
                        status = "skipped"
                        reason = "Rejected: only music video format is accepted"
                        self.sig_log.emit(f"✗ Rejected: {video_match.track_name} (non-video)", "warning")
                except Exception as e:
                    skipped_count += 1
                    status = "error"
                    reason = f"Video found but failed to add: {str(e)}"
                    self.sig_log.emit(f"✗ Add error: {e}", "error")
            else:
                skipped_count += 1
                status = "skipped"
                reason = "No matching official music video found (strict threshold)"
                self.sig_log.emit(f"- Skipped: No video for {track.name}", "info")

            item_record = {
                "track": track,
                "status": status,
                "video_match": video_match,
                "reason": reason
            }
            processed_items.append(item_record)
            self.sig_item_processed.emit(track, status, video_match, reason)

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
            f"Finished in {duration}s: {added_count} videos added, {skipped_count} skipped.",
            "success" if not self._is_cancelled else "warning"
        )
