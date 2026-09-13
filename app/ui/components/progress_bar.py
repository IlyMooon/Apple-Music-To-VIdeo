"""
Dynamic progress bar and animated counter for track processing.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtProperty


class AnimatedProgressBar(QWidget):
    """Progress control with dynamic counter and smooth animation."""

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

        # Top row: Title and Counter X / Y
        top_row = QHBoxLayout()
        self.lbl_title = QLabel("Progress", self)
        self.lbl_title.setStyleSheet("font-size: 12px; font-weight: 600; color: #A1A7B7;")
        top_row.addWidget(self.lbl_title)

        top_row.addStretch()

        self.lbl_counter = QLabel("0 / 0 processed (0%)", self)
        self.lbl_counter.setStyleSheet("font-size: 12px; font-weight: 700; color: #FFFFFF;")
        top_row.addWidget(self.lbl_counter)

        layout.addLayout(top_row)

        # Progress bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(10)
        layout.addWidget(self.progress_bar)

        # Bottom row: Quick live stats (Added vs Skipped)
        bottom_row = QHBoxLayout()
        self.lbl_stats = QLabel("Waiting to start", self)
        self.lbl_stats.setStyleSheet("font-size: 11px; color: #6C7282;")
        bottom_row.addWidget(self.lbl_stats)

        bottom_row.addStretch()

        self.lbl_eta = QLabel("", self)
        self.lbl_eta.setStyleSheet("font-size: 11px; color: #6C7282;")
        bottom_row.addWidget(self.lbl_eta)

        layout.addLayout(bottom_row)

    def get_progress_value(self) -> int:
        return self.progress_bar.value()

    def set_progress_value(self, val: int):
        self.progress_bar.setValue(val)

    progress_value = pyqtProperty(int, get_progress_value, set_progress_value)

    def reset(self):
        self._current_val = 0
        self._total_val = 0
        self.progress_bar.setValue(0)
        self.lbl_counter.setText("0 / 0 processed (0%)")
        self.lbl_stats.setText("Ready")
        self.lbl_eta.setText("")

    def set_total(self, total: int):
        self._total_val = total
        self._current_val = 0
        self.progress_bar.setValue(0)
        self.lbl_counter.setText(f"0 / {total} processed (0%)")
        self.lbl_stats.setText("Starting analysis...")

    def update_progress(self, current: int, total: int, added: int = 0, skipped: int = 0):
        self._current_val = current
        self._total_val = total

        percent = int((current / total) * 100) if total > 0 else 0
        self.lbl_counter.setText(f"{current} / {total} processed ({percent}%)")
        self.lbl_stats.setText(f"✓ {added} added  •  ✗ {skipped} skipped")

        if self._anim:
            self._anim.stop()

        self._anim = QPropertyAnimation(self, b"progress_value")
        self._anim.setDuration(160)
        self._anim.setStartValue(self.progress_bar.value())
        self._anim.setEndValue(percent)
        self._anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        self._anim.start()
