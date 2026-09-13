"""
Configuration et persistance des réglages de l'application.
Stocke les clés MusicKit optionnelles et les préférences utilisateur dans ~/.apple_music_to_video/config.json.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict


APP_VERSION = "1.0.1"


class AppConfig:
    """Gestionnaire de configuration persistante."""

    DEFAULT_CONFIG: Dict[str, Any] = {
        "storefront": "fr",
        "demo_mode": False,
        "musickit_developer_token": "",
        "musickit_user_token": "",
        "search_tolerance": 0.85,
        "rate_limit_delay_ms": 200,
        "target_playlist_prefix": "🎬 ",
        "search_local_first": True,
        "window_geometry": None,
    }

    def __init__(self):
        self.config_dir = Path.home() / ".apple_music_to_video"
        self.config_file = self.config_dir / "config.json"
        self._data: Dict[str, Any] = dict(self.DEFAULT_CONFIG)
        self.load()

    def load(self) -> None:
        """Charge la configuration depuis le fichier JSON s'il existe."""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    self._data.update(saved)
                # Migration automatique des seuils de tolérance trop permissifs (< 0.80)
                if self._data.get("search_tolerance", 0) < 0.80:
                    self._data["search_tolerance"] = 0.85
                    self.save()
            except Exception as e:
                print(f"[Config] Erreur lors du chargement: {e}")
        else:
            self.save()

    def save(self) -> None:
        """Enregistre la configuration actuelle sur disque."""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Config] Erreur lors de la sauvegarde: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self.save()

    @property
    def demo_mode(self) -> bool:
        return bool(self._data.get("demo_mode", False))

    @demo_mode.setter
    def demo_mode(self, value: bool) -> None:
        self.set("demo_mode", bool(value))

    @property
    def storefront(self) -> str:
        return str(self._data.get("storefront", "fr"))

    @storefront.setter
    def storefront(self, value: str) -> None:
        self.set("storefront", str(value).lower())

    @property
    def musickit_developer_token(self) -> str:
        return str(self._data.get("musickit_developer_token", ""))

    @musickit_developer_token.setter
    def musickit_developer_token(self, value: str) -> None:
        self.set("musickit_developer_token", str(value).strip())

    @property
    def musickit_user_token(self) -> str:
        return str(self._data.get("musickit_user_token", ""))

    @musickit_user_token.setter
    def musickit_user_token(self, value: str) -> None:
        self.set("musickit_user_token", str(value).strip())

    @property
    def has_musickit_credentials(self) -> bool:
        return bool(self.musickit_developer_token)


# Instance globale partagée
config = AppConfig()
