#!/usr/bin/env python3
"""
Apple Music To Video Converter
Point d'entrée principal de l'application macOS.

Usage :
    python3 main.py
    python3 main.py --demo
"""

import sys
import argparse
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from app.config import config
from app.ui.main_window import MainWindow


def parse_arguments():
    parser = argparse.ArgumentParser(description="Apple Music To Video Converter (macOS)")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Active le Mode Démo avec bibliothèque de démonstration sans interaction avec Music.app"
    )
    parser.add_argument(
        "--storefront",
        type=str,
        default=None,
        help="Code pays du catalogue Apple Music (ex: fr, us, gb)"
    )
    return parser.parse_args()


def main():
    args = parse_arguments()

    if args.demo:
        config.demo_mode = True
    if args.storefront:
        config.storefront = args.storefront

    # Initialisation de l'application Qt
    app = QApplication(sys.argv)
    app.setApplicationName("Apple Music To Video")
    app.setOrganizationName("AppleMusicToVideo")

    # Définition de la police système macOS optimisée
    system_font = QFont("Helvetica Neue", 13)
    system_font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(system_font)

    # Création et affichage de la fenêtre principale
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
