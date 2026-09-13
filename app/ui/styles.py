"""
Design System et feuilles de style QSS pour l'application macOS.
Thème sombre premium inspiré de macOS Sonoma / Sequoia et d'Apple Music.
"""

# Palette de couleurs principale
COLOR_BG_DARK = "#121318"
COLOR_BG_CARD = "#1A1C24"
COLOR_BG_CARD_ALT = "#21242E"
COLOR_BG_SURFACE = "#282C38"
COLOR_BORDER = "#2E3342"
COLOR_BORDER_HOVER = "#FC3C44"

# Accents Apple Music
COLOR_ACCENT = "#FC3C44"
COLOR_ACCENT_HOVER = "#FF4E58"
COLOR_ACCENT_DARK = "#D61F2E"
COLOR_ACCENT_PURPLE = "#AF52DE"

# Statuts
COLOR_SUCCESS = "#30D158"
COLOR_SUCCESS_BG = "#132E1C"
COLOR_WARNING = "#FF9F0A"
COLOR_WARNING_BG = "#382508"
COLOR_DANGER = "#FF453A"
COLOR_DANGER_BG = "#351416"
COLOR_INFO = "#0A84FF"

# Typographie
COLOR_TEXT_PRIMARY = "#F5F5F7"
COLOR_TEXT_SECONDARY = "#A1A7B7"
COLOR_TEXT_MUTED = "#6B7280"

# Feuille de style globale QSS
MAIN_STYLE_SHEET = f"""
QMainWindow {{
    background-color: {COLOR_BG_DARK};
    color: {COLOR_TEXT_PRIMARY};
}}

QWidget {{
    font-family: "SF Pro Text", "Helvetica Neue", Arial, sans-serif;
    color: {COLOR_TEXT_PRIMARY};
}}

/* Cartes & Conteneurs */
QFrame#cardFrame {{
    background-color: {COLOR_BG_CARD};
    border: 1px solid {COLOR_BORDER};
    border-radius: 14px;
}}

QFrame#cardFrame:hover {{
    border: 1px solid #3B4254;
}}

QFrame#activeCardFrame {{
    background-color: {COLOR_BG_CARD};
    border: 1px solid {COLOR_ACCENT};
    border-radius: 14px;
}}

/* Boutons principaux */
QPushButton#primaryButton {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #FC3C44, stop:1 #E01A4F);
    color: #FFFFFF;
    font-weight: 600;
    font-size: 14px;
    border: none;
    border-radius: 10px;
    padding: 10px 22px;
}}

QPushButton#primaryButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #FF525B, stop:1 #F5265E);
}}

QPushButton#primaryButton:pressed {{
    background: #D1143F;
}}

QPushButton#primaryButton:disabled {{
    background: #333642;
    color: #6C7282;
}}

/* Boutons secondaires */
QPushButton#secondaryButton {{
    background-color: {COLOR_BG_SURFACE};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER};
    border-radius: 10px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 500;
}}

QPushButton#secondaryButton:hover {{
    background-color: #333847;
    border: 1px solid #484F63;
}}

QPushButton#secondaryButton:pressed {{
    background-color: #242732;
}}

/* Bouton Danger / Annuler */
QPushButton#dangerButton {{
    background-color: #32161A;
    color: #FF5E63;
    border: 1px solid #5C2227;
    border-radius: 10px;
    padding: 8px 18px;
    font-size: 13px;
    font-weight: 600;
}}

QPushButton#dangerButton:hover {{
    background-color: #4A1E24;
    border: 1px solid #8C2C35;
    color: #FFFFFF;
}}

/* Listes déroulantes QComboBox */
QComboBox {{
    background-color: {COLOR_BG_CARD_ALT};
    border: 1px solid {COLOR_BORDER};
    border-radius: 9px;
    padding: 8px 14px;
    color: {COLOR_TEXT_PRIMARY};
    font-size: 13px;
    min-height: 22px;
}}

QComboBox:hover {{
    border: 1px solid #484F63;
    background-color: #272B38;
}}

QComboBox:focus {{
    border: 1px solid {COLOR_ACCENT};
}}

QComboBox::drop-down {{
    border: none;
    width: 28px;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {COLOR_TEXT_SECONDARY};
    margin-right: 10px;
}}

QComboBox QAbstractItemView {{
    background-color: {COLOR_BG_CARD_ALT};
    border: 1px solid {COLOR_BORDER};
    border-radius: 9px;
    selection-background-color: {COLOR_ACCENT};
    selection-color: #FFFFFF;
    color: {COLOR_TEXT_PRIMARY};
    padding: 4px;
    outline: none;
}}

/* Champs de texte QLineEdit */
QLineEdit {{
    background-color: {COLOR_BG_CARD_ALT};
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    padding: 8px 12px;
    color: {COLOR_TEXT_PRIMARY};
    font-size: 13px;
}}

QLineEdit:focus {{
    border: 1px solid {COLOR_ACCENT};
    background-color: #272B38;
}}

/* Barre de progression */
QProgressBar {{
    background-color: #20232E;
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    text-align: center;
    color: transparent;
    height: 12px;
}}

QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FC3C44, stop:0.7 #FF525B, stop:1 #AF52DE);
    border-radius: 7px;
}}

/* Listes et tableaux */
QListWidget {{
    background-color: transparent;
    border: none;
    outline: none;
}}

QListWidget::item {{
    background-color: {COLOR_BG_CARD_ALT};
    border: 1px solid {COLOR_BORDER};
    border-radius: 10px;
    margin-bottom: 6px;
    padding: 8px 12px;
}}

QListWidget::item:hover {{
    background-color: #282C3A;
    border: 1px solid #3F4659;
}}

QListWidget::item:selected {{
    background-color: #2F3342;
    border: 1px solid {COLOR_ACCENT};
}}

/* Scrollbars modernes macOS */
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 4px 0 4px 0;
}}

QScrollBar::handle:vertical {{
    background: #3B4050;
    min-height: 24px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical:hover {{
    background: #535A70;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}

/* Onglets QTabWidget */
QTabWidget::pane {{
    border: 1px solid {COLOR_BORDER};
    border-radius: 12px;
    background-color: {COLOR_BG_CARD};
    top: -1px;
}}

QTabBar::tab {{
    background: transparent;
    color: {COLOR_TEXT_SECONDARY};
    padding: 8px 18px;
    margin-right: 4px;
    font-size: 13px;
    font-weight: 500;
    border-bottom: 2px solid transparent;
}}

QTabBar::tab:selected {{
    color: #FFFFFF;
    border-bottom: 2px solid {COLOR_ACCENT};
    font-weight: 600;
}}

QTabBar::tab:hover:!selected {{
    color: {COLOR_TEXT_PRIMARY};
}}

/* Tooltips */
QToolTip {{
    background-color: #21242E;
    color: #FFFFFF;
    border: 1px solid #3D4456;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}}
"""
