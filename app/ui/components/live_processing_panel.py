"""
Panneau d'activité et de traitement en temps réel.
Affiche la liste complète et aérée de toutes les pistes analysées (ajoutées et ignorées)
en direct pendant la conversion, avec filtres par onglets, recherche et export.
"""

import json
import webbrowser
from typing import List, Dict, Any, Optional
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QListWidget, QListWidgetItem, QWidget, QLineEdit,
    QFileDialog, QCheckBox, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from app.backend.bridge_interface import TrackInfo, VideoMatch


class ProcessedTrackRow(QWidget):
    """Ligne d'affichage pour une piste traitée."""

    def __init__(self, track: TrackInfo, status: str, video_match: Optional[VideoMatch], reason: str, parent=None):
        super().__init__(parent)
        self.track = track
        self.status = status
        self.video_match = video_match
        self.reason = reason
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 7, 12, 7)
        layout.setSpacing(12)

        # 1. Badge d'état visuel clair
        badge_lbl = QLabel(self)
        badge_lbl.setFixedWidth(78)
        badge_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if self.status == "added":
            badge_lbl.setText("✓ AJOUTÉ")
            badge_lbl.setStyleSheet("""
                background-color: #13321C;
                color: #30D158;
                font-size: 10px;
                font-weight: 700;
                padding: 3px 6px;
                border-radius: 5px;
                border: 1px solid #1E5C31;
            """)
        else:
            badge_lbl.setText("✕ IGNORÉ")
            badge_lbl.setStyleSheet("""
                background-color: #262A36;
                color: #9DA3B4;
                font-size: 10px;
                font-weight: 700;
                padding: 3px 6px;
                border-radius: 5px;
                border: 1px solid #363C4D;
            """)
        layout.addWidget(badge_lbl)

        # 2. Informations de la piste
        info_box = QVBoxLayout()
        info_box.setSpacing(2)

        title_line = QLabel(f"{self.track.name}  —  {self.track.artist}", self)
        title_line.setStyleSheet("font-size: 12px; font-weight: 600; color: #FFFFFF;")
        info_box.addWidget(title_line)

        # Détail du clip ou raison de l'ignorance
        if self.status == "added" and self.video_match:
            detail_text = f"🎬 Clip vidéo : « {self.video_match.track_name} » par {self.video_match.artist_name}"
            detail_color = "#4CD964"
        else:
            detail_text = self.reason or "Aucun clip vidéo officiel correspondant"
            detail_color = "#7E8699"

        detail_line = QLabel(detail_text, self)
        detail_line.setStyleSheet(f"font-size: 10px; color: {detail_color};")
        info_box.addWidget(detail_line)

        layout.addLayout(info_box, 1)

        # 3. Action directe si URL disponible
        if self.video_match and self.video_match.video_url:
            btn_view = QPushButton("▶ Voir le clip", self)
            btn_view.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_view.setStyleSheet("""
                QPushButton {
                    background-color: #282C38;
                    color: #FC3C44;
                    font-size: 10px;
                    font-weight: 600;
                    border: 1px solid #3F4659;
                    border-radius: 5px;
                    padding: 4px 10px;
                }
                QPushButton:hover {
                    background-color: #333847;
                    border: 1px solid #FC3C44;
                    color: #FFFFFF;
                }
            """)
            url = self.video_match.video_url
            btn_view.clicked.connect(lambda: webbrowser.open(url))
            layout.addWidget(btn_view)


class LiveProcessingPanel(QFrame):
    """Panneau complet affichant la liste de toutes les pistes en temps réel."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self._items: List[Dict[str, Any]] = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)

        # 1. En-tête : Titre + Champ de recherche rapide
        header = QHBoxLayout()

        title_lbl = QLabel("📋  Détail des pistes traitées", self)
        title_lbl.setStyleSheet("font-size: 13px; font-weight: 700; color: #FFFFFF;")
        header.addWidget(title_lbl)

        header.addStretch()

        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("🔍 Filtrer les pistes...")
        self.search_input.setMinimumWidth(160)
        self.search_input.setMaximumWidth(280)
        self.search_input.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.search_input.textChanged.connect(self._apply_filter)
        header.addWidget(self.search_input)

        layout.addLayout(header)

        # 2. Onglets : Tous | Convertis | Ignorés
        self.tabs = QTabWidget(self)

        self.list_all = QListWidget(self)
        self.list_added = QListWidget(self)
        self.list_skipped = QListWidget(self)

        for lst in [self.list_all, self.list_added, self.list_skipped]:
            lst.setSpacing(3)
            lst.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
            lst.setResizeMode(QListWidget.ResizeMode.Adjust)
            lst.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.tabs.addTab(self.list_all, "Tous (0)")
        self.tabs.addTab(self.list_added, "✓ Convertis (0)")
        self.tabs.addTab(self.list_skipped, "✕ Ignorés (0)")
        self.tabs.currentChanged.connect(self._apply_filter)

        layout.addWidget(self.tabs, 1)

        # 3. Pied de page : Compteurs et boutons d'export
        footer = QHBoxLayout()

        self.lbl_stats = QLabel("En attente de traitement...", self)
        self.lbl_stats.setStyleSheet("font-size: 12px; color: #A1A7B8; font-weight: 500;")
        footer.addWidget(self.lbl_stats)

        footer.addStretch()

        self.chk_autoscroll = QCheckBox("Défilement automatique", self)
        self.chk_autoscroll.setChecked(True)
        self.chk_autoscroll.setStyleSheet("font-size: 11px; color: #8E96AB;")
        footer.addWidget(self.chk_autoscroll)

        self.btn_export = QPushButton("💾 Exporter le rapport", self)
        self.btn_export.setObjectName("secondaryButton")
        self.btn_export.clicked.connect(self._export_report)
        footer.addWidget(self.btn_export)

        layout.addLayout(footer)

    def clear(self):
        """Réinitialise la liste pour une nouvelle conversion."""
        self._items.clear()
        self.list_all.clear()
        self.list_added.clear()
        self.list_skipped.clear()
        self.tabs.setTabText(0, "Tous (0)")
        self.tabs.setTabText(1, "✓ Convertis (0)")
        self.tabs.setTabText(2, "✕ Ignorés (0)")
        self.lbl_stats.setText("Traitement en cours...")

    def add_processed_item(self, track: TrackInfo, status: str, video_match: Optional[VideoMatch], reason: str):
        """Ajoute dynamiquement une piste traitée en direct pendant le scan."""
        record = {
            "track": track,
            "status": status,
            "video_match": video_match,
            "reason": reason
        }
        self._items.append(record)

        # Ajout dans l'onglet Tous
        self._append_row(self.list_all, track, status, video_match, reason)

        # Ajout dans l'onglet spécifique
        if status == "added":
            self._append_row(self.list_added, track, status, video_match, reason)
        else:
            self._append_row(self.list_skipped, track, status, video_match, reason)

        added_count = self.list_added.count()
        skipped_count = self.list_skipped.count()
        total_count = len(self._items)

        self.tabs.setTabText(0, f"Tous ({total_count})")
        self.tabs.setTabText(1, f"✓ Convertis ({added_count})")
        self.tabs.setTabText(2, f"✕ Ignorés ({skipped_count})")

        self.lbl_stats.setText(
            f"Analysés : {total_count}  |  ✓ Ajoutés : {added_count}  |  ✕ Ignorés : {skipped_count}"
        )

        # Auto-scroll si coché
        if self.chk_autoscroll.isChecked():
            current_list = self._get_active_list()
            current_list.scrollToBottom()

    def _append_row(self, list_widget: QListWidget, track: TrackInfo, status: str, video_match: Optional[VideoMatch], reason: str):
        row_widget = ProcessedTrackRow(track, status, video_match, reason, self)
        list_item = QListWidgetItem(list_widget)
        list_item.setSizeHint(row_widget.sizeHint())
        list_widget.addItem(list_item)
        list_widget.setItemWidget(list_item, row_widget)

    def _get_active_list(self) -> QListWidget:
        idx = self.tabs.currentIndex()
        if idx == 1:
            return self.list_added
        elif idx == 2:
            return self.list_skipped
        return self.list_all

    def _apply_filter(self):
        """Filtre les éléments visibles selon le texte de recherche."""
        filter_text = self.search_input.text().lower().strip()
        current_list = self._get_active_list()

        for i in range(current_list.count()):
            item = current_list.item(i)
            widget = current_list.itemWidget(item)
            if isinstance(widget, ProcessedTrackRow):
                track_str = f"{widget.track.name} {widget.track.artist}".lower()
                is_match = filter_text in track_str if filter_text else True
                item.setHidden(not is_match)

    def _export_report(self):
        """Exporte le rapport complet."""
        if not self._items:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter le rapport de conversion",
            "rapport_conversion_apple_music.json",
            "Fichiers JSON (*.json);;Fichiers texte (*.txt)"
        )
        if not file_path:
            return

        added_items = [it for it in self._items if it["status"] == "added"]
        skipped_items = [it for it in self._items if it["status"] != "added"]

        try:
            if file_path.endswith(".json"):
                data = {
                    "total": len(self._items),
                    "added_count": len(added_items),
                    "skipped_count": len(skipped_items),
                    "items": [
                        {
                            "track_name": it["track"].name,
                            "artist": it["track"].artist,
                            "status": it["status"],
                            "reason": it["reason"],
                            "video_url": it["video_match"].video_url if it["video_match"] else None
                        }
                        for it in self._items
                    ]
                }
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            else:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write("=== RAPPORT DE CONVERSION APPLE MUSIC TO VIDEO ===\n\n")
                    f.write(f"Total analysé : {len(self._items)}\n")
                    f.write(f"Clips ajoutés : {len(added_items)}\n")
                    f.write(f"Titres ignorés : {len(skipped_items)}\n\n")
                    f.write("--- LISTE DES PISTES ---\n")
                    for it in self._items:
                        f.write(f"[{it['status'].upper()}] {it['track'].name} — {it['track'].artist} ({it['reason']})\n")
        except Exception as e:
            print(f"Erreur d'export: {e}")
