"""
Drawer and final summary panel listing converted and skipped tracks.
Features tab filtering, direct video links, and report export (JSON or Text).
"""

import json
import webbrowser
from typing import List, Dict, Any, Optional
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QListWidget, QListWidgetItem, QWidget, QFileDialog, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QSize


class TrackResultItemWidget(QFrame):
    """Spacious card for a track in the summary report."""

    def __init__(self, item_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.item_data = item_data
        self.setObjectName("trackRow")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(68)
        self._init_ui()

    def sizeHint(self) -> QSize:
        return QSize(0, 72)

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(14)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        track = self.item_data["track"]
        status = self.item_data["status"]
        video_match = self.item_data.get("video_match")
        reason = self.item_data.get("reason", "")

        # 1. Status badge
        badge_lbl = QLabel(self)
        badge_lbl.setFixedSize(86, 28)
        badge_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if status == "added":
            badge_lbl.setText("✓ ADDED")
            badge_lbl.setStyleSheet("""
                background-color: #13321C;
                color: #30D158;
                font-size: 11px;
                font-weight: 700;
                padding: 4px 8px;
                border-radius: 6px;
                border: 1px solid #1E5C31;
            """)
        else:
            badge_lbl.setText("✕ SKIPPED")
            badge_lbl.setStyleSheet("""
                background-color: #262A36;
                color: #9DA3B4;
                font-size: 11px;
                font-weight: 700;
                padding: 4px 8px;
                border-radius: 6px;
                border: 1px solid #363C4D;
            """)
        layout.addWidget(badge_lbl)

        # 2. Text info with clean hierarchy
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        title_lbl = QLabel(track.name, self)
        title_lbl.setStyleSheet("font-size: 13px; font-weight: 700; color: #FFFFFF;")
        info_layout.addWidget(title_lbl)

        artist_lbl = QLabel(f"by  {track.artist}", self)
        artist_lbl.setStyleSheet("font-size: 11px; font-weight: 500; color: #9DA3B4;")
        info_layout.addWidget(artist_lbl)

        if video_match and video_match.video_url:
            detail_text = f"🎬 Music Video: “{video_match.track_name}” ({video_match.source})"
            detail_color = "#30D158"
        else:
            detail_text = reason or "No matching official music video found"
            detail_color = "#7E8699"

        detail_lbl = QLabel(detail_text, self)
        detail_lbl.setStyleSheet(f"font-size: 11px; color: {detail_color};")
        info_layout.addWidget(detail_lbl)

        layout.addLayout(info_layout, 1)

        # 3. Action button
        if video_match and video_match.video_url:
            btn_open = QPushButton("▶ Watch Video", self)
            btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_open.setFixedSize(115, 30)
            btn_open.setStyleSheet("""
                QPushButton {
                    background-color: #282C38;
                    color: #FC3C44;
                    font-size: 11px;
                    font-weight: 600;
                    border: 1px solid #3F4659;
                    border-radius: 6px;
                    padding: 4px 10px;
                }
                QPushButton:hover {
                    background-color: #333847;
                    border: 1px solid #FC3C44;
                    color: #FFFFFF;
                }
            """)
            btn_open.clicked.connect(lambda: webbrowser.open(video_match.video_url))
            layout.addWidget(btn_open)


class SummaryDrawer(QFrame):
    """Slide-out drawer with summary report."""

    sig_drawer_toggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self._is_expanded = False
        self._current_summary: Optional[Dict[str, Any]] = None
        self._init_ui()

    def _init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(16, 14, 16, 14)
        self.main_layout.setSpacing(12)

        # Header with statistics and toggle button
        header = QHBoxLayout()

        self.lbl_title = QLabel("📊  Conversion Report", self)
        self.lbl_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #FFFFFF;")
        header.addWidget(self.lbl_title)

        self.lbl_meta = QLabel("", self)
        self.lbl_meta.setStyleSheet("font-size: 12px; color: #8E96AB;")
        header.addWidget(self.lbl_meta)

        header.addStretch()

        self.btn_export = QPushButton("💾 Export Report", self)
        self.btn_export.setObjectName("secondaryButton")
        self.btn_export.clicked.connect(self._export_report)
        header.addWidget(self.btn_export)

        self.btn_toggle = QPushButton("▲ Collapse", self)
        self.btn_toggle.setObjectName("secondaryButton")
        self.btn_toggle.clicked.connect(self.toggle_drawer)
        header.addWidget(self.btn_toggle)

        self.main_layout.addLayout(header)

        # Tabs
        self.tabs = QTabWidget(self)

        self.list_all = QListWidget()
        self.list_added = QListWidget()
        self.list_skipped = QListWidget()

        for lst in [self.list_all, self.list_added, self.list_skipped]:
            lst.setSpacing(8)
            lst.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
            lst.setResizeMode(QListWidget.ResizeMode.Adjust)

        self.tabs.addTab(self.list_all, "All (0)")
        self.tabs.addTab(self.list_added, "✓ Added (0)")
        self.tabs.addTab(self.list_skipped, "✕ Skipped (0)")

        self.main_layout.addWidget(self.tabs)

        self.setMaximumHeight(0)
        self.setVisible(False)

    def set_summary_data(self, summary: Dict[str, Any]):
        """Inject summary data and populate lists."""
        self._current_summary = summary
        items = summary.get("items", [])
        total = summary.get("total", 0)
        added = summary.get("added", 0)
        skipped = summary.get("skipped", 0)
        duration = summary.get("duration", 0)

        status_text = f"• {total} tracks analyzed in {duration}s"
        if summary.get("cancelled"):
            status_text += " (Cancelled by user)"
        self.lbl_meta.setText(status_text)

        self.list_all.clear()
        self.list_added.clear()
        self.list_skipped.clear()

        for item in items:
            self._add_item_to_list(self.list_all, item)
            if item["status"] == "added":
                self._add_item_to_list(self.list_added, item)
            else:
                self._add_item_to_list(self.list_skipped, item)

        self.tabs.setTabText(0, f"All ({len(items)})")
        self.tabs.setTabText(1, f"✓ Added ({added})")
        self.tabs.setTabText(2, f"✕ Skipped ({skipped})")

        self.expand_drawer()

    def _add_item_to_list(self, list_widget: QListWidget, item_data: Dict[str, Any]):
        row_widget = TrackResultItemWidget(item_data, self)
        list_item = QListWidgetItem(list_widget)
        list_item.setSizeHint(QSize(0, 76))
        list_widget.addItem(list_item)
        list_widget.setItemWidget(list_item, row_widget)

    def expand_drawer(self):
        """Expand drawer smoothly."""
        self.setVisible(True)
        self._is_expanded = True
        self.btn_toggle.setText("▲ Collapse")

        self.anim = QPropertyAnimation(self, b"maximumHeight")
        self.anim.setDuration(280)
        self.anim.setStartValue(self.height())
        self.anim.setEndValue(320)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.start()
        self.sig_drawer_toggled.emit(True)

    def collapse_drawer(self):
        """Collapse drawer smoothly."""
        self._is_expanded = False
        self.btn_toggle.setText("▼ Expand")

        self.anim = QPropertyAnimation(self, b"maximumHeight")
        self.anim.setDuration(240)
        self.anim.setStartValue(self.height())
        self.anim.setEndValue(54)
        self.anim.setEasingCurve(QEasingCurve.Type.InQuad)
        self.anim.start()
        self.sig_drawer_toggled.emit(False)

    def toggle_drawer(self):
        if self._is_expanded:
            self.collapse_drawer()
        else:
            self.expand_drawer()

    def _export_report(self):
        """Export report to JSON or Text."""
        if not self._current_summary:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Conversion Report",
            "apple_music_conversion_report.json",
            "JSON Files (*.json);;Text Files (*.txt)"
        )
        if not file_path:
            return

        try:
            if file_path.endswith(".json"):
                exportable = {
                    "total": self._current_summary["total"],
                    "added": self._current_summary["added"],
                    "skipped": self._current_summary["skipped"],
                    "duration_seconds": self._current_summary["duration"],
                    "cancelled": self._current_summary.get("cancelled", False),
                    "items": [
                        {
                            "track_name": it["track"].name,
                            "artist": it["track"].artist,
                            "status": it["status"],
                            "reason": it["reason"],
                            "video_url": it.get("video_match").video_url if it.get("video_match") else None,
                        }
                        for it in self._current_summary.get("items", [])
                    ]
                }
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(exportable, f, indent=2, ensure_ascii=False)
            else:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write("=== APPLE MUSIC TO VIDEO CONVERSION REPORT ===\n\n")
                    f.write(f"Total analyzed: {self._current_summary['total']}\n")
                    f.write(f"Videos added: {self._current_summary['added']}\n")
                    f.write(f"Tracks skipped: {self._current_summary['skipped']}\n\n")
                    f.write("--- TRACK LIST ---\n")
                    for it in self._current_summary.get("items", []):
                        f.write(f"[{it['status'].upper()}] {it['track'].name} - {it['track'].artist} ({it['reason']})\n")
        except Exception as e:
            print(f"Export error: {e}")
