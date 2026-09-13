"""
Composant de sélection des playlists : Source -> Flèche animée -> Destination.
Intègre le scan automatique, le rafraîchissement et la création dynamique de playlists.
"""

from typing import List
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, QComboBox,
    QPushButton, QLineEdit, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QPoint


class AnimatedArrowLabel(QLabel):
    """Flèche animée avec translation horizontale douce au survol."""

    def __init__(self, parent=None):
        super().__init__("➔", parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("""
            font-size: 22px;
            color: #FC3C44;
            font-weight: bold;
            padding: 8px;
        """)
        self._anim = None

    def start_pulse(self):
        """Lance une animation de pulsation pour indiquer le flux."""
        pass


class PlaylistSelectorCard(QFrame):
    """Carte principale de sélection Source et Destination."""

    sig_refresh_requested = pyqtSignal()
    sig_selection_changed = pyqtSignal(str, str)  # source, destination

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(10)

        # En-tête de la carte avec titre et bouton rafraîchir
        header_layout = QHBoxLayout()
        title = QLabel("📂  Playlists Apple Music", self)
        title.setStyleSheet("font-size: 13px; font-weight: 700; color: #FFFFFF;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        self.btn_refresh = QPushButton("⟳  Actualiser", self)
        self.btn_refresh.setObjectName("secondaryButton")
        self.btn_refresh.setToolTip("Rescanner les playlists de l'app Musique")
        self.btn_refresh.clicked.connect(self.sig_refresh_requested.emit)
        header_layout.addWidget(self.btn_refresh)

        main_layout.addLayout(header_layout)

        # Zone centrale : Colonne Source | Flèche | Colonne Destination
        cols_layout = QHBoxLayout()
        cols_layout.setSpacing(12)

        # 1. Colonne Source
        source_col = QVBoxLayout()
        source_col.setSpacing(4)
        lbl_source = QLabel("Playlist Source (Morceaux audio)", self)
        lbl_source.setStyleSheet("font-size: 11px; font-weight: 600; color: #A1A7B7;")
        source_col.addWidget(lbl_source)

        self.combo_source = QComboBox(self)
        self.combo_source.setPlaceholderText("Sélectionnez une playlist...")
        self.combo_source.currentIndexChanged.connect(self._on_source_changed)
        source_col.addWidget(self.combo_source)

        cols_layout.addLayout(source_col, 45)

        # 2. Flèche de transition
        arrow_container = QVBoxLayout()
        arrow_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
        arrow_container.addSpacing(8)
        self.arrow = AnimatedArrowLabel(self)
        arrow_container.addWidget(self.arrow)
        cols_layout.addLayout(arrow_container, 10)

        # 3. Colonne Destination
        dest_col = QVBoxLayout()
        dest_col.setSpacing(4)
        lbl_dest = QLabel("Playlist Cible (Clips Vidéo)", self)
        lbl_dest.setStyleSheet("font-size: 11px; font-weight: 600; color: #A1A7B7;")
        dest_col.addWidget(lbl_dest)

        self.combo_dest = QComboBox(self)
        self.combo_dest.setPlaceholderText("Choisir ou créer une playlist...")
        self.combo_dest.currentIndexChanged.connect(self._on_dest_combo_changed)
        dest_col.addWidget(self.combo_dest)

        # Champ de texte pour nouvelle playlist personnalisée
        self.input_custom_dest = QLineEdit(self)
        self.input_custom_dest.setPlaceholderText("Nom de la nouvelle playlist...")
        self.input_custom_dest.textChanged.connect(self._notify_changed)
        dest_col.addWidget(self.input_custom_dest)

        cols_layout.addLayout(dest_col, 45)

        main_layout.addLayout(cols_layout)

    def populate_playlists(self, playlists: List[str]) -> None:
        """Remplit les deux menus déroulants avec la liste des playlists."""
        current_source = self.combo_source.currentText()
        
        self.combo_source.blockSignals(True)
        self.combo_dest.blockSignals(True)

        self.combo_source.clear()
        self.combo_dest.clear()

        if not playlists:
            self.combo_source.addItem("Aucune playlist trouvée")
            self.combo_dest.addItem("✨ Créer une nouvelle playlist...")
        else:
            for p in playlists:
                self.combo_source.addItem(p)

            # Restaure l'ancienne sélection si possible
            idx = self.combo_source.findText(current_source)
            if idx >= 0:
                self.combo_source.setCurrentIndex(idx)
            else:
                self.combo_source.setCurrentIndex(0)

            # Remplissage destination : Création en premier, puis les existantes
            self.combo_dest.addItem("✨ Créer une nouvelle playlist...")
            for p in playlists:
                self.combo_dest.addItem(f"📁 {p}", p)

        self.combo_source.blockSignals(False)
        self.combo_dest.blockSignals(False)

        if self.combo_source.count() > 0:
            self.combo_source.setCurrentIndex(0)
        if self.combo_dest.count() > 0:
            self.combo_dest.setCurrentIndex(0)

        self._on_source_changed()

    def _on_source_changed(self):
        """Met à jour automatiquement le nom proposé pour la nouvelle playlist vidéo."""
        source = self.combo_source.currentText()
        if source and source != "Aucune playlist trouvée":
            default_new_name = f"🎬 {source} (Vidéos)"
            self.input_custom_dest.setText(default_new_name)
        self._notify_changed()

    def _on_dest_combo_changed(self, index: int):
        """Bascule l'affichage du champ de saisie si 'Créer...' est sélectionné."""
        is_create_new = (index <= 0)
        self.input_custom_dest.setVisible(is_create_new)
        self._notify_changed()

    def _notify_changed(self):
        source = self.get_source_playlist()
        dest = self.get_destination_playlist()
        self.sig_selection_changed.emit(source, dest)

    def get_source_playlist(self) -> str:
        text = self.combo_source.currentText()
        return text if text != "Aucune playlist trouvée" else ""

    def get_destination_playlist(self) -> str:
        if self.combo_dest.currentIndex() <= 0:
            return self.input_custom_dest.text().strip()
        data = self.combo_dest.currentData()
        return data if data else self.combo_dest.currentText().replace("📁 ", "").strip()

    def set_enabled_controls(self, enabled: bool):
        """Active ou désactive les sélecteurs pendant la conversion."""
        self.combo_source.setEnabled(enabled)
        self.combo_dest.setEnabled(enabled)
        self.input_custom_dest.setEnabled(enabled)
        self.btn_refresh.setEnabled(enabled)
