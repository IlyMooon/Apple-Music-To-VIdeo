"""
Fenêtre principale de l'application Apple Music To Video.
Assemble la barre de titre macOS, le bandeau de permissions, la sélection de playlists,
le monitoring en temps réel, le déclencheur de conversion et le tiroir de résumé.
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
    """Thread dédié au scan asynchrone des playlists pour ne jamais figer l'interface."""
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
                message = f"Erreur de lecture: {e}"

        self.sig_loaded.emit(playlists, is_ready, message)


class MainWindow(QMainWindow):
    """Fenêtre principale de l'application."""

    sig_playlists_loaded = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Apple Music To Video")
        self.resize(840, 640)
        self.setMinimumSize(780, 560)

        # Style macOS Frameless avec bords arrondis
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        # Bridges et services
        self.bridge: BaseMusicBridge = None
        self.catalog_service = CatalogSearchService(
            storefront=config.storefront,
            tolerance=config.get("search_tolerance", 0.85)
        )
        self.musickit_bridge: Optional[MusicKitBridge] = None
        self.worker: Optional[MusicVideoConverterWorker] = None
        self.scanner_thread: Optional[PlaylistScannerThread] = None

        # Initialisation UI
        self._init_ui()
        self.setStyleSheet(MAIN_STYLE_SHEET)

        # Initialisation du bridge approprié
        self._setup_bridge()

        # Lancement immédiat du scan asynchrone (non-bloquant grâce au QThread)
        self._refresh_playlists()

    def _init_ui(self):
        # Conteneur principal avec ombre portée douce macOS
        self.central_container = QWidget(self)
        self.central_container.setObjectName("centralContainer")
        self.central_container.setStyleSheet("""
            #centralContainer {
                background-color: #121318;
                border: 1px solid #282C38;
                border-radius: 14px;
            }
        """)

        # Ombre portée de la fenêtre
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 8)
        self.central_container.setGraphicsEffect(shadow)

        self.setCentralWidget(self.central_container)

        main_layout = QVBoxLayout(self.central_container)
        main_layout.setContentsMargins(0, 0, 0, 16)
        main_layout.setSpacing(12)

        # 1. Barre de titre personnalisée
        self.title_bar = MacTitleBar(self, "Apple Music To Video")
        self.title_bar.sig_open_settings.connect(self._open_settings)
        main_layout.addWidget(self.title_bar)

        # Contenu intérieur avec marges
        inner_content = QVBoxLayout()
        inner_content.setContentsMargins(16, 4, 16, 4)
        inner_content.setSpacing(10)

        # 2. Bandeau d'assistance des permissions macOS
        self.permission_banner = PermissionBanner(self)
        self.permission_banner.sig_switch_to_demo.connect(self._switch_to_demo_mode)
        self.permission_banner.sig_retry_check.connect(self._retry_permission_check)
        inner_content.addWidget(self.permission_banner)

        # 3. Sélecteur Source -> Destination
        self.playlist_card = PlaylistSelectorCard(self)
        self.playlist_card.sig_refresh_requested.connect(self._refresh_playlists)
        self.playlist_card.sig_selection_changed.connect(self._on_playlist_selection_changed)
        inner_content.addWidget(self.playlist_card)

        # 4. Zone d'Action Centrale & Contrôle
        self.action_card = QFrame(self)
        self.action_card.setObjectName("cardFrame")
        action_layout = QVBoxLayout(self.action_card)
        action_layout.setContentsMargins(16, 10, 16, 10)
        action_layout.setSpacing(10)

        # Boutons Lancer / Annuler
        btn_box = QHBoxLayout()

        self.btn_convert = QPushButton("🚀  Lancer la conversion en Clips Vidéo", self)
        self.btn_convert.setObjectName("primaryButton")
        self.btn_convert.setFixedHeight(40)
        self.btn_convert.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_convert.clicked.connect(self._start_conversion)
        btn_box.addWidget(self.btn_convert, 1)

        self.btn_cancel = QPushButton("🛑  Annuler", self)
        self.btn_cancel.setObjectName("dangerButton")
        self.btn_cancel.setFixedHeight(40)
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setVisible(False)
        self.btn_cancel.clicked.connect(self._cancel_conversion)
        btn_box.addWidget(self.btn_cancel)

        action_layout.addLayout(btn_box)

        # Barre de progression
        self.progress_bar = AnimatedProgressBar(self)
        action_layout.addWidget(self.progress_bar)

        inner_content.addWidget(self.action_card)

        # 5. Zone de prévisualisation en temps réel (Morceau en cours, pochette, badge)
        self.monitor_card = RealtimeMonitorCard(self)
        inner_content.addWidget(self.monitor_card)

        # 6. Panneau d'activité en temps réel complet et aéré
        self.live_panel = LiveProcessingPanel(self)
        inner_content.addWidget(self.live_panel, 1)

        main_layout.addLayout(inner_content)

        # 7. Poignée de redimensionnement discrète
        bottom_bar = QHBoxLayout()
        bottom_bar.setContentsMargins(14, 0, 6, 2)
        bottom_bar.addStretch()
        self.size_grip = QSizeGrip(self.central_container)
        self.size_grip.setFixedSize(14, 14)
        bottom_bar.addWidget(self.size_grip, 0, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)
        main_layout.addLayout(bottom_bar)

    def _setup_bridge(self):
        """Initialise le bridge selon la configuration utilisateur."""
        if config.demo_mode:
            self.bridge = MockMusicBridge()
            self.title_bar.set_backend_badge("🧪 Mode Démo Actif", is_demo=True)
            self.permission_banner.hide_warning()
        else:
            self.bridge = AppleScriptBridge()
            self.title_bar.set_backend_badge("⚡ AppleScript Bridge", is_demo=False)

        # Configuration optionnelle MusicKit
        if config.has_musickit_credentials:
            self.musickit_bridge = MusicKitBridge(
                developer_token=config.musickit_developer_token,
                user_token=config.musickit_user_token,
                storefront=config.storefront
            )
        else:
            self.musickit_bridge = None

    def _retry_permission_check(self):
        """Vérifie à nouveau l'accès AppleScript."""
        self._refresh_playlists()

    def _switch_to_demo_mode(self):
        """Bascule vers le mode démo pour explorer l'interface immédiatement."""
        config.demo_mode = True
        self._setup_bridge()
        self._refresh_playlists()

    def _refresh_playlists(self):
        """Scanne les playlists disponibles."""
        self.playlist_card.btn_refresh.setEnabled(False)
        self.playlist_card.btn_refresh.setText("⟳ Scan...")

        if config.demo_mode:
            playlists = self.bridge.get_playlists()
            self._on_playlists_scanned(playlists, True, "Mode Démo actif")
            return

        self.scanner_thread = PlaylistScannerThread(self.bridge, False, self)
        self.scanner_thread.sig_loaded.connect(self._on_playlists_scanned)
        self.scanner_thread.start()

    def _on_playlists_scanned(self, playlists: list, is_ready: bool, message: str):
        """Callback après la fin du scan asynchrone des playlists."""
        if not config.demo_mode:
            if not is_ready:
                self.permission_banner.show_warning(message)
            else:
                self.permission_banner.hide_warning()

        self.playlist_card.populate_playlists(playlists)
        self.playlist_card.btn_refresh.setEnabled(True)
        self.playlist_card.btn_refresh.setText("⟳ Actualiser")
        self.sig_playlists_loaded.emit(playlists)

    def _on_playlist_selection_changed(self, source: str, dest: str):
        """Valide la cohérence du bouton de démarrage."""
        can_start = bool(source and dest and source != dest)
        self.btn_convert.setEnabled(can_start)
        if not source:
            self.btn_convert.setToolTip("Sélectionnez une playlist source")
        elif not dest:
            self.btn_convert.setToolTip("Indiquez une playlist de destination")
        elif source == dest:
            self.btn_convert.setToolTip("La destination doit être différente de la source")
        else:
            self.btn_convert.setToolTip("")

    def _start_conversion(self):
        """Lance le thread de traitement asynchrone."""
        source = self.playlist_card.get_source_playlist()
        dest = self.playlist_card.get_destination_playlist()

        if not source or not dest:
            QMessageBox.warning(
                self,
                "Sélection requise",
                "Veuillez choisir une playlist source et un nom de destination valide."
            )
            return

        if source == dest:
            QMessageBox.warning(
                self,
                "Nom identique",
                "La playlist de destination doit avoir un nom distinct de la source pour éviter d'écraser vos données."
            )
            return

        # Mise à jour des états graphiques
        self.btn_convert.setEnabled(False)
        self.btn_convert.setText("Traitement en cours...")
        self.btn_cancel.setVisible(True)
        self.playlist_card.set_enabled_controls(False)
        self.progress_bar.reset()
        self.monitor_card.reset()
        self.live_panel.clear()

        # Démarrage du QThread
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
        """Demande l'arrêt du worker."""
        if self.worker and self.worker.isRunning():
            self.btn_cancel.setEnabled(False)
            self.btn_cancel.setText("Arrêt...")
            self.worker.cancel()

    def _on_worker_started(self, total: int):
        self.progress_bar.set_total(total)

    def _on_worker_progress(self, current: int, total: int, track):
        self.monitor_card.set_scanning_track(track.name, track.artist)

    def _on_worker_item_processed(self, track, status: str, video_match, reason: str):
        artwork = video_match.artwork_url if video_match else ""
        self.monitor_card.set_result(track.name, track.artist, status, reason, artwork)

        # Ajout immédiat dans le panneau en direct (accessible et défilable)
        self.live_panel.add_processed_item(track, status, video_match, reason)

        # Mise à jour dynamique de la barre de progression
        total = self.progress_bar._total_val
        current = self.live_panel.list_all.count()
        added = self.live_panel.list_added.count()
        skipped = self.live_panel.list_skipped.count()
        self.progress_bar.update_progress(current, total, added, skipped)

    def _on_worker_finished(self, summary: dict):
        """Traitement de fin : réactivation des contrôles et actualisation finale."""
        self.btn_convert.setEnabled(True)
        self.btn_convert.setText("🚀  Lancer la conversion en Clips Vidéo")
        self.btn_cancel.setVisible(False)
        self.btn_cancel.setEnabled(True)
        self.btn_cancel.setText("🛑  Annuler")
        self.playlist_card.set_enabled_controls(True)

        # Mise à jour barre finale
        total = summary.get("total", 0)
        added = summary.get("added", 0)
        skipped = summary.get("skipped", 0)
        self.progress_bar.update_progress(total, total, added, skipped)

        # Rafraîchir les playlists pour que la nouvelle playlist apparaisse dans la liste
        QTimer.singleShot(1000, self._refresh_playlists)

    def _on_worker_error(self, message: str):
        self.btn_convert.setEnabled(True)
        self.btn_convert.setText("🚀  Lancer la conversion en Clips Vidéo")
        self.btn_cancel.setVisible(False)
        self.playlist_card.set_enabled_controls(True)
        QMessageBox.critical(self, "Erreur de traitement", message)

    def _open_settings(self):
        """Ouvre la boîte de dialogue des préférences."""
        dlg = SettingsDialog(self)
        dlg.sig_settings_saved.connect(self._on_settings_saved)
        dlg.exec()

    def _on_settings_saved(self):
        """Recharge les services suite à une modification des réglages."""
        self.catalog_service.storefront = config.storefront
        self.catalog_service.tolerance = config.get("search_tolerance", 0.85)
        self._setup_bridge()
        self._refresh_playlists()
