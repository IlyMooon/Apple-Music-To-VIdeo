"""
Barre de progression dynamique et compteur animé pour le traitement des pistes.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtProperty


class AnimatedProgressBar(QWidget):
    """Contrôle de progression avec compteur dynamique et animation fluide."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_val = 0
        self._total_val = 0
        self._anim = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(6)

        # Ligne supérieure : Titre et Compteur X / Y
        top_row = QHBoxLayout()
        self.lbl_title = QLabel("Progression", self)
        self.lbl_title.setStyleSheet("font-size: 12px; font-weight: 600; color: #A1A7B7;")
        top_row.addWidget(self.lbl_title)

        top_row.addStretch()

        self.lbl_counter = QLabel("0 / 0 traités (0%)", self)
        self.lbl_counter.setStyleSheet("font-size: 12px; font-weight: 700; color: #FFFFFF;")
        top_row.addWidget(self.lbl_counter)

        layout.addLayout(top_row)

        # Barre de progression
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(10)
        layout.addWidget(self.progress_bar)

        # Ligne inférieure : Résumé rapide en direct (Ajoutés vs Ignorés)
        bottom_row = QHBoxLayout()
        self.lbl_stats = QLabel("En attente de démarrage", self)
        self.lbl_stats.setStyleSheet("font-size: 11px; color: #6C7282;")
        bottom_row.addWidget(self.lbl_stats)

        bottom_row.addStretch()

        self.lbl_eta = QLabel("", self)
        self.lbl_eta.setStyleSheet("font-size: 11px; color: #6C7282;")
        bottom_row.addWidget(self.lbl_eta)

        layout.addLayout(bottom_row)

    # Propriété Qt pour animation fluide de la valeur de la barre
    def get_progress_value(self) -> int:
        return self.progress_bar.value()

    def set_progress_value(self, val: int):
        self.progress_bar.setValue(val)

    progress_value = pyqtProperty(int, get_progress_value, set_progress_value)

    def reset(self):
        self._current_val = 0
        self._total_val = 0
        self.progress_bar.setValue(0)
        self.lbl_counter.setText("0 / 0 traités (0%)")
        self.lbl_stats.setText("Prêt")
        self.lbl_eta.setText("")

    def set_total(self, total: int):
        self._total_val = total
        self._current_val = 0
        self.progress_bar.setValue(0)
        self.lbl_counter.setText(f"0 / {total} traités (0%)")
        self.lbl_stats.setText("Démarrage de l'analyse...")

    def update_progress(self, current: int, total: int, added: int = 0, skipped: int = 0):
        self._current_val = current
        self._total_val = total

        percent = int((current / total) * 100) if total > 0 else 0
        self.lbl_counter.setText(f"{current} / {total} traités ({percent}%)")
        self.lbl_stats.setText(f"✓ {added} ajouté{'s' if added > 1 else ''}  •  ✗ {skipped} ignoré{'s' if skipped > 1 else ''}")

        # Animation douce de la barre vers le nouveau pourcentage
        if self._anim:
            self._anim.stop()

        self._anim = QPropertyAnimation(self, b"progress_value")
        self._anim.setDuration(160)
        self._anim.setStartValue(self.progress_bar.value())
        self._anim.setEndValue(percent)
        self._anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        self._anim.start()
