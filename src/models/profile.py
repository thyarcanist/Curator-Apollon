# Curator Apollon: Profile management (list/create/select current profile)
from __future__ import annotations

from pathlib import Path
import json
import os
from typing import List


def _get_app_base_dir() -> Path:
    if os.name == 'nt':
        app_data_base = Path(os.getenv('APPDATA', ''))
    else:
        app_data_base = Path(os.getenv('XDG_DATA_HOME', Path.home() / ".local" / "share"))
    base = app_data_base / "CuratorApollon"
    base.mkdir(parents=True, exist_ok=True)
    return base


class ProfileManager:
    CONFIG_NAME = "profiles.json"

    def __init__(self):
        self.base_dir = _get_app_base_dir()
        self.config_path = self.base_dir / self.CONFIG_NAME
        self._config = self._load_config()

    def _load_config(self) -> dict:
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
            except Exception:
                pass
        return {"current_profile": "default"}

    def _save_config(self):
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2)
        except Exception:
            pass

    def list_profiles(self) -> List[str]:
        profiles = []
        for child in self.base_dir.iterdir():
            if child.is_dir() and child.name not in {self.CONFIG_NAME}:
                profiles.append(child.name)
        if "default" not in profiles:
            profiles.append("default")
        return sorted(set(profiles))

    def ensure_profile(self, name: str) -> Path:
        profile_dir = self.base_dir / name
        profile_dir.mkdir(parents=True, exist_ok=True)
        return profile_dir

    def get_current_profile(self) -> str:
        return self._config.get("current_profile", "default")

    def set_current_profile(self, name: str):
        self.ensure_profile(name)
        self._config["current_profile"] = name
        self._save_config()


