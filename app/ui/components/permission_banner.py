"""
macOS Permissions banner & guidance (Apple Events / Automation).
Appears when macOS requires authorization in System Settings or if Music is closed.
"""

from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, QPushButton
)
from PyQt6.QtCore import Qt, pyqtSignal
from app.backend.applescript_bridge import AppleScriptBridge


class PermissionBanner(QFrame):
    """Elegant alert banner for macOS automation permissions."""

    sig_switch_to_demo = pyqtSignal()
    sig_retry_check = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(54)
        self.setObjectName("permissionBanner")
        self.setStyleSheet("""
            #permissionBanner {
                background-color: #2D1E12;
                border: 1px solid #734516;
                border-radius: 10px;
            }
        """)
        self._init_ui()
        self.setVisible(False)

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(12)

        # Icon
        icon = QLabel("⚠️", self)
        icon.setStyleSheet("font-size: 16px;")
        layout.addWidget(icon)

        # Message
        self.lbl_message = QLabel(
            "macOS Permission Required: Allow control of Music in System Settings > Privacy & Security > Automation.",
            self
        )
        self.lbl_message.setStyleSheet("font-size: 12px; color: #FFD494; font-weight: 500;")
        layout.addWidget(self.lbl_message, 1)

        # Settings button
        self.btn_open_settings = QPushButton("Open System Settings", self)
        self.btn_open_settings.setStyleSheet("""
            background-color: #593510;
            color: #FFFFFF;
            border: 1px solid #8C551C;
            border-radius: 6px;
            padding: 5px 12px;
            font-size: 11px;
            font-weight: 600;
        """)
        self.btn_open_settings.clicked.connect(AppleScriptBridge.open_automation_settings)
        layout.addWidget(self.btn_open_settings)

        # Demo mode button
        self.btn_demo = QPushButton("Switch to Demo Mode", self)
        self.btn_demo.setStyleSheet("""
            background-color: #3B2A1E;
            color: #FFC078;
            border: 1px solid #63452D;
            border-radius: 6px;
            padding: 5px 12px;
            font-size: 11px;
            font-weight: 500;
        """)
        self.btn_demo.clicked.connect(self.sig_switch_to_demo.emit)
        layout.addWidget(self.btn_demo)

        # Retry button
        self.btn_retry = QPushButton("⟳", self)
        self.btn_retry.setToolTip("Re-check permissions")
        self.btn_retry.setFixedSize(26, 26)
        self.btn_retry.setStyleSheet("""
            background-color: #3B2A1E;
            color: #FFFFFF;
            border: 1px solid #63452D;
            border-radius: 6px;
            font-size: 12px;
        """)
        self.btn_retry.clicked.connect(self.sig_retry_check.emit)
        layout.addWidget(self.btn_retry)

    def show_warning(self, message: str):
        self.lbl_message.setText(message)
        self.setVisible(True)

    def hide_warning(self):
        self.setVisible(False)
