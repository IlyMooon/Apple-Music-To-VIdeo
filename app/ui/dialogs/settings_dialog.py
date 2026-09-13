"""
Boîte de dialogue des Réglages.
Permet de configurer le mode de fonctionnement (AppleScript réel vs Démo),
le pays du storefront Apple Music, la tolérance de correspondance
et les identifiants MusicKit API optionnels.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QCheckBox, QComboBox, QSlider, QPushButton, QGroupBox, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from app.config import config


class SettingsDialog(QDialog):
    """Fenêtre modale des paramètres."""

    sig_settings_saved = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Préférences — Apple Music To Video")
        self.setFixedSize(480, 520)
        self.setStyleSheet("""
            QDialog {
                background-color: #1A1C24;
                color: #FFFFFF;
            }
            QGroupBox {
                border: 1px solid #2E3342;
                border-radius: 10px;
                margin-top: 14px;
                padding-top: 14px;
                font-size: 12px;
                font-weight: 700;
                color: #FC3C44;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding-left: 10px;
                padding-right: 10px;
            }
        """)
        self._init_ui()
        self._load_values()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # 1. Groupe Général
        grp_general = QGroupBox("GÉNÉRAL & MOTEUR", self)
        v_general = QVBoxLayout(grp_general)
        v_general.setSpacing(10)

        self.chk_demo_mode = QCheckBox("Activer le Mode Démo (sans interaction avec Music.app)", self)
        self.chk_demo_mode.setStyleSheet("font-size: 13px; font-weight: 500; color: #FFFFFF;")
        v_general.addWidget(self.chk_demo_mode)

        # Storefront
        h_store = QHBoxLayout()
        lbl_store = QLabel("Pays du Store Apple Music :", self)
        lbl_store.setStyleSheet("font-size: 12px; color: #A1A7B7;")
        h_store.addWidget(lbl_store)

        self.combo_store = QComboBox(self)
        self.combo_store.addItem("France (fr)", "fr")
        self.combo_store.addItem("États-Unis (us)", "us")
        self.combo_store.addItem("Royaume-Uni (gb)", "gb")
        self.combo_store.addItem("Canada (ca)", "ca")
        self.combo_store.addItem("Allemagne (de)", "de")
        self.combo_store.addItem("Japon (jp)", "jp")
        h_store.addWidget(self.combo_store)
        v_general.addLayout(h_store)

        # Tolérance de recherche
        h_tol = QHBoxLayout()
        self.lbl_tol_text = QLabel("Tolérance de similarité titre/clip : 85% (Haute précision)", self)
        self.lbl_tol_text.setStyleSheet("font-size: 12px; color: #A1A7B7;")
        h_tol.addWidget(self.lbl_tol_text)

        self.slider_tol = QSlider(Qt.Orientation.Horizontal, self)
        self.slider_tol.setRange(75, 98)
        self.slider_tol.setValue(85)
        self.slider_tol.valueChanged.connect(self._on_slider_changed)
        h_tol.addWidget(self.slider_tol)
        v_general.addLayout(h_tol)

        layout.addWidget(grp_general)

        # 2. Groupe MusicKit API (Optionnel)
        grp_api = QGroupBox("API APPLE MUSIC / MUSICKIT (OPTIONNEL)", self)
        v_api = QVBoxLayout(grp_api)
        v_api.setSpacing(8)

        lbl_api_desc = QLabel(
            "Non obligatoire. L'application utilise par défaut l'API de recherche iTunes gratuite et AppleScript local.",
            self
        )
        lbl_api_desc.setWordWrap(True)
        lbl_api_desc.setStyleSheet("font-size: 11px; color: #788094;")
        v_api.addWidget(lbl_api_desc)

        lbl_dev_token = QLabel("Developer Token (JWT) :", self)
        lbl_dev_token.setStyleSheet("font-size: 11px; color: #A1A7B7;")
        v_api.addWidget(lbl_dev_token)

        self.input_dev_token = QLineEdit(self)
        self.input_dev_token.setPlaceholderText("Bearer eyJhbGciOi...")
        v_api.addWidget(self.input_dev_token)

        lbl_user_token = QLabel("Music User Token :", self)
        lbl_user_token.setStyleSheet("font-size: 11px; color: #A1A7B7;")
        v_api.addWidget(lbl_user_token)

        self.input_user_token = QLineEdit(self)
        self.input_user_token.setPlaceholderText("Optionnel (pour modification cloud)")
        v_api.addWidget(self.input_user_token)

        layout.addWidget(grp_api)

        layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # Boutons d'action
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Annuler", self)
        self.btn_cancel.setObjectName("secondaryButton")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("Enregistrer", self)
        self.btn_save.setObjectName("primaryButton")
        self.btn_save.clicked.connect(self._save_values)
        btn_layout.addWidget(self.btn_save)

        layout.addLayout(btn_layout)

    def _on_slider_changed(self, value: int):
        self.lbl_tol_text.setText(f"Tolérance de similarité titre/clip : {value}% (Haute précision)")

    def _load_values(self):
        self.chk_demo_mode.setChecked(config.demo_mode)
        current_store = config.storefront
        idx = self.combo_store.findData(current_store)
        if idx >= 0:
            self.combo_store.setCurrentIndex(idx)

        val = int(config.get("search_tolerance", 0.85) * 100)
        self.slider_tol.setValue(val)
        self.lbl_tol_text.setText(f"Tolérance de similarité titre/clip : {val}% (Haute précision)")

        self.input_dev_token.setText(config.musickit_developer_token)
        self.input_user_token.setText(config.musickit_user_token)

    def _save_values(self):
        config.demo_mode = self.chk_demo_mode.isChecked()
        config.storefront = self.combo_store.currentData()
        config.set("search_tolerance", round(self.slider_tol.value() / 100.0, 2))
        config.musickit_developer_token = self.input_dev_token.text().strip()
        config.musickit_user_token = self.input_user_token.text().strip()
        self.sig_settings_saved.emit()
        self.accept()
