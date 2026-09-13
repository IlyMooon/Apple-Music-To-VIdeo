"""
Tiroir et panneau de résumé final listant les pistes converties et ignorées.
Intègre le filtrage par onglets, les actions directes (ouvrir dans Musique)
et l'exportation de rapport (JSON ou Texte).
"""

import json
import webbrowser
from typing import List, Dict, Any, Optional
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QListWidget, QListWidgetItem, QWidget, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve


class TrackResultItemWidget(QWidget):
    """Widget personnalisé pour un élément de la liste de résultat."""

    def __init__(self, item_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.item_data = item_data
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(12)

        track = self.item_data["track"]
        status = self.item_data["status"]
        video_match = self.item_data.get("video_match")
        reason = self.item_data.get("reason", "")

        # 1. Icône d'état
        icon_lbl = QLabel(self)
        icon_lbl.setFixedSize(28, 28)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if status == "added":
            icon_lbl.setText("✓")
            icon_lbl.setStyleSheet("""
                background-color: #12301B;
                color: #30D158;
                font-weight: bold;
                border-radius: 14px;
            """)
        else:
            icon_lbl.setText("–")
            icon_lbl.setStyleSheet("""
                background-color: #262A36;
                color: #8E96AB;
                font-weight: bold;
                border-radius: 14px;
            """)
        layout.addWidget(icon_lbl)

        # 2. Textes : Titre & Artiste + Détail
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        title_lbl = QLabel(f"{track.name} — {track.artist}", self)
        title_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #FFFFFF;")
        info_layout.addWidget(title_lbl)

        detail_text = reason
        if video_match and video_match.video_url:
            detail_text = f"🎬 Clip trouvé : {video_match.track_name} ({video_match.source})"
        
        detail_lbl = QLabel(detail_text, self)
        detail_lbl.setStyleSheet("font-size: 11px; color: #8C94A6;")
        info_layout.addWidget(detail_lbl)

        layout.addLayout(info_layout, 1)

        # 3. Bouton action si lien vidéo présent
        if video_match and video_match.video_url:
            btn_open = QPushButton("Voir le clip", self)
            btn_open.setObjectName("secondaryButton")
            btn_open.setFixedHeight(26)
            btn_open.setStyleSheet("""
                font-size: 11px;
                padding: 2px 10px;
                border-radius: 6px;
            """)
            btn_open.clicked.connect(lambda: webbrowser.open(video_match.video_url))
            layout.addWidget(btn_open)


class SummaryDrawer(QFrame):
    """Tiroir de compte-rendu déroulant avec animation fluide."""

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

        # En-tête du tiroir avec statistiques globales et bouton replier
        header = QHBoxLayout()

        self.lbl_title = QLabel("📊  Rapport de conversion", self)
        self.lbl_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #FFFFFF;")
        header.addWidget(self.lbl_title)

        self.lbl_meta = QLabel("", self)
        self.lbl_meta.setStyleSheet("font-size: 12px; color: #8E96AB;")
        header.addWidget(self.lbl_meta)

        header.addStretch()

        self.btn_export = QPushButton("💾 Exporter le rapport", self)
        self.btn_export.setObjectName("secondaryButton")
        self.btn_export.clicked.connect(self._export_report)
        header.addWidget(self.btn_export)

        self.btn_toggle = QPushButton("▲ Replier", self)
        self.btn_toggle.setObjectName("secondaryButton")
        self.btn_toggle.clicked.connect(self.toggle_drawer)
        header.addWidget(self.btn_toggle)

        self.main_layout.addLayout(header)

        # Onglets de classification
        self.tabs = QTabWidget(self)

        self.list_all = QListWidget()
        self.list_added = QListWidget()
        self.list_skipped = QListWidget()

        self.tabs.addTab(self.list_all, "Tous (0)")
        self.tabs.addTab(self.list_added, "✓ Convertis (0)")
        self.tabs.addTab(self.list_skipped, "✗ Ignorés (0)")

        self.main_layout.addWidget(self.tabs)

        # Initialement masqué / compact
        self.setMaximumHeight(0)
        self.setVisible(False)

    def set_summary_data(self, summary: Dict[str, Any]):
        """Injecte les données et prépare les listes."""
        self._current_summary = summary
        items = summary.get("items", [])
        total = summary.get("total", 0)
        added = summary.get("added", 0)
        skipped = summary.get("skipped", 0)
        duration = summary.get("duration", 0)

        status_text = f"• {total} pistes analysées en {duration}s"
        if summary.get("cancelled"):
            status_text += " (Interrompu par l'utilisateur)"
        self.lbl_meta.setText(status_text)

        # Nettoyage des listes existantes
        self.list_all.clear()
        self.list_added.clear()
        self.list_skipped.clear()

        # Remplissage
        for item in items:
            self._add_item_to_list(self.list_all, item)
            if item["status"] == "added":
                self._add_item_to_list(self.list_added, item)
            else:
                self._add_item_to_list(self.list_skipped, item)

        self.tabs.setTabText(0, f"Tous ({len(items)})")
        self.tabs.setTabText(1, f"✓ Convertis ({added})")
        self.tabs.setTabText(2, f"✗ Ignorés ({skipped})")

        self.expand_drawer()

    def _add_item_to_list(self, list_widget: QListWidget, item_data: Dict[str, Any]):
        row_widget = TrackResultItemWidget(item_data, self)
        list_item = QListWidgetItem(list_widget)
        list_item.setSizeHint(row_widget.sizeHint())
        list_widget.addItem(list_item)
        list_widget.setItemWidget(list_item, row_widget)

    def expand_drawer(self):
        """Ouvre le tiroir avec une animation verticale fluide."""
        self.setVisible(True)
        self._is_expanded = True
        self.btn_toggle.setText("▲ Replier")

        self.anim = QPropertyAnimation(self, b"maximumHeight")
        self.anim.setDuration(280)
        self.anim.setStartValue(self.height())
        self.anim.setEndValue(320)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.start()
        self.sig_drawer_toggled.emit(True)

    def collapse_drawer(self):
        """Replie le tiroir."""
        self._is_expanded = False
        self.btn_toggle.setText("▼ Déplier")

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
        """Exporte le compte-rendu dans un fichier JSON ou Texte au choix de l'utilisateur."""
        if not self._current_summary:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter le rapport de conversion",
            "rapport_conversion_apple_music.json",
            "Fichiers JSON (*.json);;Fichiers texte (*.txt)"
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
                    f.write("=== RAPPORT DE CONVERSION APPLE MUSIC TO VIDEO ===\n\n")
                    f.write(f"Total analysé : {self._current_summary['total']}\n")
                    f.write(f"Clips ajoutés : {self._current_summary['added']}\n")
                    f.write(f"Titres ignorés : {self._current_summary['skipped']}\n\n")
                    f.write("--- DÉTAIL PAR PISTE ---\n")
                    for it in self._current_summary.get("items", []):
                        f.write(f"[{it['status'].upper()}] {it['track'].name} - {it['track'].artist} ({it['reason']})\n")
        except Exception as e:
            print(f"Erreur d'export: {e}")
