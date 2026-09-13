"""
Main Window for the Apple Music To Video macOS application.
Integrates custom macOS title bar, permission banner, playlist selector,
real-time scan monitor, action controls, and live processing panel.
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QGraphicsDropShadowEffect, QMessageBox, QSizeGrip
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor

from .styles import MAIN_STYLE_SHEET, COLOR_ACCENT
from .components import (
    MacTitleBar, PlaylistSelectorCard, RealtimeMonitorCard,
    AnimatedProgressBar, PermissionBanner, LiveProcessingPanel
)
from .dialogs import SettingsDialog

from ..config import config
from ..backend import (
    BaseMusicBridge, AppleScriptBridge, MockMusicBridge,
    CatalogSearchService, MusicKitBridge
)
from ..backend.converter_worker import MusicVideoConverterWorker
from PyQt6.QtCore import QThread, pyqtSignal


class PlaylistScannerThread(QThread):
    """Thread dedicated to asynchronous playlist scanning to keep UI fluid."""
    sig_loaded = pyqtSignal(list, bool, str)

    def __init__(self, bridge: BaseMusicBridge, is_demo: bool, parent=None):
        super().__init__(parent)
        self.bridge = bridge
        self.is_demo = is_demo

    def run(self):
        is_ready = True
        message = ""
        playlists = []

        if not self.is_demo:
            try:
                is_ready, message = self.bridge.check_availability()
            except Exception as e:
                is_ready = False
                message = str(e)

        try:
            playlists = self.bridge.get_playlists()
        except Exception as e:
            if not self.is_demo:
                is_ready = False
                message = f"Read error: {e}"

        self.sig_loaded.emit(playlists, is_ready, message)


class MainWindow(QMainWindow):
    """Main Application Window."""

    sig_playlists_loaded = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Apple Music To Video")
        self.resize(840, 640)
        self.setMinimumSize(780, 560)

        # macOS Frameless style with rounded corners
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        # Bridges and services
        self.bridge: BaseMusicBridge = None
        self.catalog_service = CatalogSearchService(
            storefront=config.storefront,
            tolerance=config.get("search_tolerance", 0.85)
        )
        self.musickit_bridge: Optional[MusicKitBridge] = None
        self.worker: Optional[MusicVideoConverterWorker] = None
        self.scanner_thread: Optional[PlaylistScannerThread] = None

        # Initialize UI
        self._init_ui()
        self.setStyleSheet(MAIN_STYLE_SHEET)

        # Initialize backend bridge
        self._setup_bridge()

        # Launch initial asynchronous scan
        self._refresh_playlists()

    def _init_ui(self):
        # Central container with macOS drop shadow
        self.central_container = QWidget(self)
        self.central_container.setObjectName("centralContainer")
        self.central_container.setStyleSheet("""
            #centralContainer {
                background-color: #121318;
                border: 1px solid #282C38;
                border-radius: 14px;
            }
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 8)
        self.central_container.setGraphicsEffect(shadow)

        self.setCentralWidget(self.central_container)

        main_layout = QVBoxLayout(self.central_container)
        main_layout.setContentsMargins(0, 0, 0, 16)
        main_layout.setSpacing(12)

        # 1. Custom Title Bar
        self.title_bar = MacTitleBar(self, "Apple Music To Video")
        self.title_bar.sig_open_settings.connect(self._open_settings)
        main_layout.addWidget(self.title_bar)

        # Inner content layout
        inner_content = QVBoxLayout()
        inner_content.setContentsMargins(16, 4, 16, 4)
        inner_content.setSpacing(10)

        # 2. macOS Permission Banner
        self.permission_banner = PermissionBanner(self)
        self.permission_banner.sig_switch_to_demo.connect(self._switch_to_demo_mode)
        self.permission_banner.sig_retry_check.connect(self._retry_permission_check)
        inner_content.addWidget(self.permission_banner)

        # 3. Source -> Destination Playlist Selector
        self.playlist_card = PlaylistSelectorCard(self)
        self.playlist_card.sig_refresh_requested.connect(self._refresh_playlists)
        self.playlist_card.sig_selection_changed.connect(self._on_playlist_selection_changed)
        inner_content.addWidget(self.playlist_card)

        # 4. Central Action Card & Controls
        self.action_card = QFrame(self)
        self.action_card.setObjectName("cardFrame")
        action_layout = QVBoxLayout(self.action_card)
        action_layout.setContentsMargins(16, 10, 16, 10)
        action_layout.setSpacing(10)

        # Action buttons
        btn_box = QHBoxLayout()

        self.btn_convert = QPushButton("🚀  Convert to Music Videos", self)
        self.btn_convert.setObjectName("primaryButton")
        self.btn_convert.setFixedHeight(40)
        self.btn_convert.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_convert.clicked.connect(self._start_conversion)
        btn_box.addWidget(self.btn_convert, 1)

        self.btn_cancel = QPushButton("🛑  Cancel", self)
        self.btn_cancel.setObjectName("dangerButton")
        self.btn_cancel.setFixedHeight(40)
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setVisible(False)
        self.btn_cancel.clicked.connect(self._cancel_conversion)
        btn_box.addWidget(self.btn_cancel)

        action_layout.addLayout(btn_box)

        # Progress bar
        self.progress_bar = AnimatedProgressBar(self)
        action_layout.addWidget(self.progress_bar)

        inner_content.addWidget(self.action_card)

        # 5. Real-time Scan Preview Monitor
        self.monitor_card = RealtimeMonitorCard(self)
        inner_content.addWidget(self.monitor_card)

        # 6. Live Processing Panel (Spacious & Responsive)
        self.live_panel = LiveProcessingPanel(self)
        inner_content.addWidget(self.live_panel, 1)

        main_layout.addLayout(inner_content)

        # 7. Subtle resize grip
        bottom_bar = QHBoxLayout()
        bottom_bar.setContentsMargins(14, 0, 6, 2)
        bottom_bar.addStretch()
        self.size_grip = QSizeGrip(self.central_container)
        self.size_grip.setFixedSize(14, 14)
        bottom_bar.addWidget(self.size_grip, 0, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)
        main_layout.addLayout(bottom_bar)

    def _setup_bridge(self):
        """Initialize backend bridge according to settings."""
        if config.demo_mode:
            self.bridge = MockMusicBridge()
            self.title_bar.set_backend_badge("🧪 Demo Mode Active", is_demo=True)
            self.permission_banner.hide_warning()
        else:
            self.bridge = AppleScriptBridge()
            self.title_bar.set_backend_badge("⚡ AppleScript Bridge", is_demo=False)

        if config.has_musickit_credentials:
            self.musickit_bridge = MusicKitBridge(
                developer_token=config.musickit_developer_token,
                user_token=config.musickit_user_token,
                storefront=config.storefront
            )
        else:
            self.musickit_bridge = None

    def _retry_permission_check(self):
        """Recheck AppleScript access."""
        self._refresh_playlists()

    def _switch_to_demo_mode(self):
        """Switch to demo mode to explore offline."""
        config.demo_mode = True
        self._setup_bridge()
        self._refresh_playlists()

    def _refresh_playlists(self):
        """Scan available playlists."""
        self.playlist_card.btn_refresh.setEnabled(False)
        self.playlist_card.btn_refresh.setText("⟳ Scanning...")

        if config.demo_mode:
            playlists = self.bridge.get_playlists()
            self._on_playlists_scanned(playlists, True, "Demo Mode active")
            return

        self.scanner_thread = PlaylistScannerThread(self.bridge, False, self)
        self.scanner_thread.sig_loaded.connect(self._on_playlists_scanned)
        self.scanner_thread.start()

    def _on_playlists_scanned(self, playlists: list, is_ready: bool, message: str):
        """Callback after asynchronous playlist scan completes."""
        if not config.demo_mode:
            if not is_ready:
                self.permission_banner.show_warning(message)
            else:
                self.permission_banner.hide_warning()

        self.playlist_card.populate_playlists(playlists)
        self.playlist_card.btn_refresh.setEnabled(True)
        self.playlist_card.btn_refresh.setText("⟳ Refresh")
        self.sig_playlists_loaded.emit(playlists)

    def _on_playlist_selection_changed(self, source: str, dest: str):
        """Validate start button state."""
        can_start = bool(source and dest and source != dest)
        self.btn_convert.setEnabled(can_start)
        if not source:
            self.btn_convert.setToolTip("Select a source playlist")
        elif not dest:
            self.btn_convert.setToolTip("Specify a target playlist")
        elif source == dest:
            self.btn_convert.setToolTip("Target playlist must have a different name from the source")
        else:
            self.btn_convert.setToolTip("")

    def _start_conversion(self):
        """Start asynchronous conversion worker thread."""
        source = self.playlist_card.get_source_playlist()
        dest = self.playlist_card.get_destination_playlist()

        if not source or not dest:
            QMessageBox.warning(
                self,
                "Selection Required",
                "Please choose a source playlist and a valid destination name."
            )
            return

        if source == dest:
            QMessageBox.warning(
                self,
                "Identical Name",
                "The target playlist must have a different name from the source to avoid overwriting your data."
            )
            return

        # Update UI state
        self.btn_convert.setEnabled(False)
        self.btn_convert.setText("Converting...")
        self.btn_cancel.setVisible(True)
        self.playlist_card.set_enabled_controls(False)
        self.progress_bar.reset()
        self.monitor_card.reset()
        self.live_panel.clear()

        # Start worker thread
        self.worker = MusicVideoConverterWorker(
            bridge=self.bridge,
            catalog_search=self.catalog_service,
            musickit_bridge=self.musickit_bridge,
            source_playlist=source,
            destination_playlist=dest,
            search_local_first=config.get("search_local_first", True),
            delay_ms=config.get("rate_limit_delay_ms", 180)
        )

        self.worker.sig_started.connect(self._on_worker_started)
        self.worker.sig_progress.connect(self._on_worker_progress)
        self.worker.sig_item_processed.connect(self._on_worker_item_processed)
        self.worker.sig_finished.connect(self._on_worker_finished)
        self.worker.sig_error.connect(self._on_worker_error)

        self.worker.start()

    def _cancel_conversion(self):
        """Request worker stop."""
        if self.worker and self.worker.isRunning():
            self.btn_cancel.setEnabled(False)
            self.btn_cancel.setText("Stopping...")
            self.worker.cancel()

    def _on_worker_started(self, total: int):
        self.progress_bar.set_total(total)

    def _on_worker_progress(self, current: int, total: int, track):
        self.monitor_card.set_scanning_track(track.name, track.artist)

    def _on_worker_item_processed(self, track, status: str, video_match, reason: str):
        artwork = video_match.artwork_url if video_match else ""
        self.monitor_card.set_result(track.name, track.artist, status, reason, artwork)
        self.live_panel.add_processed_item(track, status, video_match, reason)

        total = self.progress_bar._total_val
        current = self.live_panel.list_all.count()
        added = self.live_panel.list_added.count()
        skipped = self.live_panel.list_skipped.count()
        self.progress_bar.update_progress(current, total, added, skipped)

    def _on_worker_finished(self, summary: dict):
        """Handle worker completion: restore controls and refresh playlists."""
        self.btn_convert.setEnabled(True)
        self.btn_convert.setText("🚀  Convert to Music Videos")
        self.btn_cancel.setVisible(False)
        self.btn_cancel.setEnabled(True)
        self.btn_cancel.setText("🛑  Cancel")
        self.playlist_card.set_enabled_controls(True)

        total = summary.get("total", 0)
        added = summary.get("added", 0)
        skipped = summary.get("skipped", 0)
        self.progress_bar.update_progress(total, total, added, skipped)

        # Refresh playlists to reflect the newly created playlist
        QTimer.singleShot(1000, self._refresh_playlists)

    def _on_worker_error(self, message: str):
        self.btn_convert.setEnabled(True)
        self.btn_convert.setText("🚀  Convert to Music Videos")
        self.btn_cancel.setVisible(False)
        self.playlist_card.set_enabled_controls(True)
        QMessageBox.critical(self, "Processing Error", message)

    def _open_settings(self):
        """Open settings dialog."""
        dlg = SettingsDialog(self)
        dlg.sig_settings_saved.connect(self._on_settings_saved)
        dlg.exec()

    def _on_settings_saved(self):
        """Reload services after settings change."""
        self.catalog_service.storefront = config.storefront
        self.catalog_service.tolerance = config.get("search_tolerance", 0.85)
        self._setup_bridge()
        self._refresh_playlists()
