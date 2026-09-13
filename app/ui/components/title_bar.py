"""
Barre de titre macOS personnalisée avec boutons Traffic Lights,
glisser-déposer pour déplacer la fenêtre, titre centré et boutons d'action rapides.
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QFrame, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt, QPoint, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QBrush, QPen, QFont


class TrafficLightButton(QPushButton):
    """Bouton rond inspiré des traffic lights natifs de macOS."""

    def __init__(self, color_normal: str, color_hover: str, glyph: str = "", parent=None):
        super().__init__(parent)
        self.color_normal = QColor(color_normal)
        self.color_hover = QColor(color_hover)
        self.glyph = glyph
        self._is_hovered = False
        self.setFixedSize(13, 13)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def enterEvent(self, event):
        self._is_hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._is_hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        color = self.color_hover if self._is_hovered else self.color_normal
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(color.darker(115), 0.5))
        painter.drawEllipse(1, 1, 11, 11)

        if self._is_hovered and self.glyph:
            painter.setPen(QPen(QColor(0, 0, 0, 160), 1.2))
            painter.setFont(QFont("Arial", 8, QFont.Weight.Bold))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.glyph)


class MacTitleBar(QFrame):
    """Barre de titre intégrée avec boutons de fenêtre et déplacement fluide."""

    sig_open_settings = pyqtSignal()

    def __init__(self, parent=None, title: str = "Apple Music To Video"):
        super().__init__(parent)
        self.parent_window = parent
        self._drag_pos = QPoint()
        self.setFixedHeight(44)
        self.setObjectName("macTitleBar")
        self.setStyleSheet("""
            #macTitleBar {
                background-color: #161820;
                border-bottom: 1px solid #262A36;
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(10)

        # Traffic Lights (Gauche)
        self.btn_close = TrafficLightButton("#FF5F56", "#E0443E", "×", self)
        self.btn_minimize = TrafficLightButton("#FFBD2E", "#DEA123", "–", self)
        self.btn_maximize = TrafficLightButton("#27C93F", "#1AAB29", "+", self)

        self.btn_close.clicked.connect(self._on_close)
        self.btn_minimize.clicked.connect(self._on_minimize)
        self.btn_maximize.clicked.connect(self._on_maximize)

        layout.addWidget(self.btn_close)
        layout.addWidget(self.btn_minimize)
        layout.addWidget(self.btn_maximize)

        layout.addSpacing(12)

        # Title centered with version
        self.title_label = QLabel(f"🎬  {title}  <span style='font-size: 11px; color: #72798E; font-weight: 500;'>v1.0.1</span>", self)
        self.title_label.setStyleSheet("""
            font-size: 13px;
            font-weight: 600;
            color: #E2E4EC;
            letter-spacing: 0.3px;
        """)
        layout.addWidget(self.title_label)

        layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        # Badge "macOS Native / AppleScript"
        self.badge_backend = QLabel("⚡ AppleScript Bridge", self)
        self.badge_backend.setStyleSheet("""
            background-color: #1F232F;
            color: #8E96AB;
            font-size: 11px;
            font-weight: 500;
            padding: 3px 9px;
            border-radius: 6px;
            border: 1px solid #2F3547;
        """)
        layout.addWidget(self.badge_backend)

        # Settings button (Gear)
        self.btn_settings = QPushButton("⚙️", self)
        self.btn_settings.setFixedSize(28, 28)
        self.btn_settings.setToolTip("Settings & MusicKit API")
        self.btn_settings.setStyleSheet("""
            QPushButton {
                background-color: #212532;
                border: 1px solid #31374A;
                border-radius: 7px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #2E3345;
                border: 1px solid #FC3C44;
            }
        """)
        self.btn_settings.clicked.connect(self.sig_open_settings.emit)
        layout.addWidget(self.btn_settings)

    def set_backend_badge(self, text: str, is_demo: bool = False) -> None:
        """Met à jour le badge d'état du bridge."""
        self.badge_backend.setText(text)
        if is_demo:
            self.badge_backend.setStyleSheet("""
                background-color: #382508;
                color: #FFB340;
                font-size: 11px;
                font-weight: 600;
                padding: 3px 9px;
                border-radius: 6px;
                border: 1px solid #5C3D0E;
            """)
        else:
            self.badge_backend.setStyleSheet("""
                background-color: #182B1E;
                color: #30D158;
                font-size: 11px;
                font-weight: 600;
                padding: 3px 9px;
                border-radius: 6px;
                border: 1px solid #234E2E;
            """)

    def _on_close(self):
        if self.parent_window:
            self.parent_window.close()

    def _on_minimize(self):
        if self.parent_window:
            self.parent_window.showMinimized()

    def _on_maximize(self):
        if self.parent_window:
            if self.parent_window.isMaximized():
                self.parent_window.showNormal()
            else:
                self.parent_window.showMaximized()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.parent_window:
            self._drag_pos = event.globalPosition().toPoint() - self.parent_window.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.parent_window and not self.parent_window.isMaximized():
            self.parent_window.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._on_maximize()
