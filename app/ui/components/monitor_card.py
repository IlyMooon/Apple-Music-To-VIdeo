"""
Zone de prévisualisation en temps réel de la piste en cours de traitement.
Affiche la pochette / miniature du clip, le titre, l'artiste,
et un badge animé à statut dynamique ([Ajouté], [Ignoré], [Recherche...]).
"""

from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QByteArray
from PyQt6.QtGui import QPixmap, QImage
import requests


class StatusBadge(QLabel):
    """Badge d'état avec couleur adaptée et micro-animation de fondu."""

    def __init__(self, parent=None):
        super().__init__("En attente", parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(26)
        self.setMinimumWidth(110)
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)
        self.set_idle()

    def _animate_transition(self):
        anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        anim.setDuration(240)
        anim.setStartValue(0.2)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
        # Conserver la référence pour éviter garbage collection
        self._current_anim = anim

    def set_idle(self):
        self.setText("⏸  En attente")
        self.setStyleSheet("""
            background-color: #212532;
            color: #8E96AB;
            font-size: 11px;
            font-weight: 700;
            padding: 4px 12px;
            border-radius: 13px;
            border: 1px solid #31374A;
        """)
        self._animate_transition()

    def set_searching(self, track_name: str = ""):
        self.setText("🔍  Recherche...")
        self.setStyleSheet("""
            background-color: #16263D;
            color: #5AA9FF;
            font-size: 11px;
            font-weight: 700;
            padding: 4px 12px;
            border-radius: 13px;
            border: 1px solid #234773;
        """)
        self._animate_transition()

    def set_added(self, source_text: str = "Ajouté"):
        self.setText(f"✓  {source_text}")
        self.setStyleSheet("""
            background-color: #12301B;
            color: #30D158;
            font-size: 11px;
            font-weight: 700;
            padding: 4px 12px;
            border-radius: 13px;
            border: 1px solid #1E5C31;
        """)
        self._animate_transition()

    def set_skipped(self, reason: str = "Ignoré"):
        self.setText(f"✕  {reason}")
        self.setStyleSheet("""
            background-color: #2C2023;
            color: #FF7B82;
            font-size: 11px;
            font-weight: 700;
            padding: 4px 12px;
            border-radius: 13px;
            border: 1px solid #57272E;
        """)
        self._animate_transition()


class RealtimeMonitorCard(QFrame):
    """Carte de monitoring en direct du morceau scanné."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.setFixedHeight(82)
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(12)

        # 1. Miniature / Pochette d'album
        self.thumb_label = QLabel(self)
        self.thumb_label.setFixedSize(54, 54)
        self.thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb_label.setStyleSheet("""
            background-color: #242834;
            border: 1px solid #33384A;
            border-radius: 8px;
            color: #8C92A4;
            font-size: 22px;
        """)
        self.thumb_label.setText("🎵")
        layout.addWidget(self.thumb_label)

        # 2. Informations du morceau (Titre & Artiste)
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.lbl_subtitle = QLabel("PRÉVISUALISATION EN TEMPS RÉEL", self)
        self.lbl_subtitle.setStyleSheet("""
            font-size: 9px;
            font-weight: 700;
            color: #FC3C44;
            letter-spacing: 0.8px;
        """)
        info_layout.addWidget(self.lbl_subtitle)

        self.lbl_track = QLabel("En attente de démarrage...", self)
        self.lbl_track.setStyleSheet("""
            font-size: 13px;
            font-weight: 700;
            color: #FFFFFF;
        """)
        info_layout.addWidget(self.lbl_track)

        self.lbl_artist = QLabel("Sélectionnez une playlist et cliquez sur Lancer", self)
        self.lbl_artist.setStyleSheet("""
            font-size: 11px;
            color: #A1A7B7;
            font-weight: 500;
        """)
        info_layout.addWidget(self.lbl_artist)

        self.lbl_details = QLabel("", self)
        self.lbl_details.setStyleSheet("""
            font-size: 10px;
            color: #6C7282;
            font-style: italic;
        """)
        info_layout.addWidget(self.lbl_details)

        layout.addLayout(info_layout, 1)

        # 3. Badge dynamique
        badge_layout = QVBoxLayout()
        badge_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
        self.badge = StatusBadge(self)
        badge_layout.addWidget(self.badge)
        layout.addLayout(badge_layout)

    def set_scanning_track(self, title: str, artist: str):
        """Met à jour l'affichage lors du début de recherche pour un titre."""
        self.lbl_track.setText(title)
        self.lbl_artist.setText(artist)
        self.lbl_details.setText("Interrogation du catalogue...")
        self.thumb_label.setText("🎬")
        self.badge.set_searching()

    def set_result(self, title: str, artist: str, status: str, reason: str, artwork_url: str = ""):
        """Affiche le résultat final pour la piste analysée."""
        self.lbl_track.setText(title)
        self.lbl_artist.setText(artist)
        self.lbl_details.setText(reason)

        if status == "added":
            self.badge.set_added("Clip Ajouté")
        else:
            self.badge.set_skipped("Ignoré")

        # Chargement asynchrone ou direct de la miniature si disponible
        if artwork_url:
            self._load_thumbnail(artwork_url)
        else:
            self.thumb_label.setText("🎬" if status == "added" else "🎵")

    def _load_thumbnail(self, url: str):
        """Tente de charger l'image d'illustration si URL valide."""
        try:
            resp = requests.get(url, timeout=1.5)
            if resp.status_code == 200:
                img = QImage()
                img.loadFromData(QByteArray(resp.content))
                pixmap = QPixmap.fromImage(img)
                scaled = pixmap.scaled(
                    76, 76,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.thumb_label.setPixmap(scaled)
        except Exception:
            self.thumb_label.setText("🎬")

    def reset(self):
        """Réinitialise la carte de monitoring."""
        self.lbl_track.setText("Prêt pour la conversion")
        self.lbl_artist.setText("Cliquez sur 'Lancer la conversion' pour commencer")
        self.lbl_details.setText("")
        self.thumb_label.setText("🎵")
        self.thumb_label.setPixmap(QPixmap())
        self.badge.set_idle()
