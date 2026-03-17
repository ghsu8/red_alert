"""Configuration and persistence for the Red Alert notifier."""

from __future__ import annotations

import json
import os
import platform
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, TypedDict


def _get_app_dir() -> Path:
    """Return the directory used for storing config and caches."""

    if platform.system() == "Windows":
        base = os.getenv("APPDATA")
        if base:
            return Path(base) / "RedAlert"
    # fallback for other OS or if APPDATA not set
    return Path.home() / ".redalert"


def _ensure_app_dir() -> Path:
    path = _get_app_dir()
    path.mkdir(parents=True, exist_ok=True)
    return path


class AlertSound(str):
    DEFAULT = "default"
    SILENT = "silent"
    CUSTOM = "custom"


class AlertMode(str):
    ALL = "all"
    CUSTOM = "custom"
    POI = "נקודת ייחוס"


class ConfigPayload(TypedDict, total=False):
    sound_mode: str
    custom_sound_path: str
    alert_mode: str
    selected_region: str
    selected_city: str
    selected_regions: list[str]
    selected_cities: list[str]
    poi_city: str
    poi_distance_km: float
    google_maps_api_key: str
    use_google_maps: bool
    autostart: bool
    last_seen_alert_id: str
    popup_duration_seconds: Optional[int]


DEFAULT_CONFIG: ConfigPayload = {
    "sound_mode": AlertSound.DEFAULT,
    "custom_sound_path": "",
    "alert_mode": AlertMode.ALL,
    "selected_region": "כל האזורים",
    "selected_city": "",
    "selected_regions": ["כל האזורים"],
    "selected_cities": [],
    "poi_city": "",
    "poi_distance_km": 30.0,
    "google_maps_api_key": "",
    "use_google_maps": True,
    "autostart": False,
    "last_seen_alert_id": "",
    "popup_duration_seconds": 10,
}


@dataclass
class AppConfig:
    sound_mode: str = DEFAULT_CONFIG["sound_mode"]
    custom_sound_path: str = DEFAULT_CONFIG["custom_sound_path"]

    # Alert filtering
    alert_mode: str = DEFAULT_CONFIG["alert_mode"]
    selected_region: str = DEFAULT_CONFIG["selected_region"]
    selected_city: str = DEFAULT_CONFIG["selected_city"]
    selected_regions: list[str] = field(default_factory=lambda: DEFAULT_CONFIG["selected_regions"].copy())
    selected_cities: list[str] = field(default_factory=lambda: DEFAULT_CONFIG["selected_cities"].copy())

    # Point of interest (POI) matching
    poi_city: str = DEFAULT_CONFIG["poi_city"]
    poi_distance_km: float = DEFAULT_CONFIG["poi_distance_km"]
    google_maps_api_key: str = DEFAULT_CONFIG["google_maps_api_key"]
    use_google_maps: bool = DEFAULT_CONFIG["use_google_maps"]

    # Startup behavior
    autostart: bool = DEFAULT_CONFIG["autostart"]

    # Popup behavior
    popup_duration_seconds: Optional[int] = DEFAULT_CONFIG["popup_duration_seconds"]

    # Internal state
    last_seen_alert_id: str = DEFAULT_CONFIG["last_seen_alert_id"]

    path: Path = field(default_factory=_ensure_app_dir)

    @property
    def config_file(self) -> Path:
        return self.path / "config.json"

    def load(self) -> None:
        """Load configuration from disk (if exists)."""
        try:
            with self.config_file.open("r", encoding="utf-8") as f:
                raw = json.load(f)
        except FileNotFoundError:
            raw = {}
        except json.JSONDecodeError:
            raw = {}

        if isinstance(raw, dict):
            payload: ConfigPayload = {**DEFAULT_CONFIG, **raw}
            self.sound_mode = payload.get("sound_mode", self.sound_mode)
            self.custom_sound_path = payload.get("custom_sound_path", self.custom_sound_path)
            self.alert_mode = payload.get("alert_mode", self.alert_mode)

            # Backwards-compatible: read old single-selection keys if the new list keys don't exist.
            self.selected_regions = payload.get(
                "selected_regions",
                [payload.get("selected_region", self.selected_region) or "כל האזורים"],
            )
            self.selected_cities = payload.get(
                "selected_cities", [payload.get("selected_city", self.selected_city)]
            )

            self.selected_region = self.selected_regions[0] if self.selected_regions else "כל האזורים"
            self.selected_city = self.selected_cities[0] if self.selected_cities else ""

            self.poi_city = payload.get("poi_city", self.poi_city)
            self.poi_distance_km = float(payload.get("poi_distance_km", self.poi_distance_km))
            self.google_maps_api_key = payload.get(
                "google_maps_api_key",
                os.getenv("REDALERT_GOOGLE_MAPS_API_KEY", self.google_maps_api_key),
            )
            self.use_google_maps = bool(payload.get("use_google_maps", self.use_google_maps))
            self.autostart = bool(payload.get("autostart", self.autostart))
            self.last_seen_alert_id = str(payload.get("last_seen_alert_id", self.last_seen_alert_id))

    def save(self) -> None:
        """Persist configuration to disk."""
        payload: ConfigPayload = {
            "sound_mode": self.sound_mode,
            "custom_sound_path": self.custom_sound_path,
            "alert_mode": self.alert_mode,
            "selected_region": self.selected_region,
            "selected_city": self.selected_city,
            "selected_regions": self.selected_regions,
            "selected_cities": self.selected_cities,
            "poi_city": self.poi_city,
            "poi_distance_km": self.poi_distance_km,
            "google_maps_api_key": self.google_maps_api_key,
            "use_google_maps": self.use_google_maps,
            "autostart": self.autostart,
            "last_seen_alert_id": self.last_seen_alert_id,
        }

        with self.config_file.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)


def set_autostart(enabled: bool) -> None:
    """Enable or disable auto-start on Windows for the current user."""
    # This is Windows specific. It is safe to call on other platforms (no-op).
    try:
        if platform.system() != "Windows":
            return

        import winreg  # type: ignore

        exe_path = Path(__file__).resolve().parents[1] / "main.py"
        exe_path = str(exe_path)

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE,
        )

        if enabled:
            winreg.SetValueEx(key, "RedAlert", 0, winreg.REG_SZ, f'"{exe_path}"')
        else:
            try:
                winreg.DeleteValue(key, "RedAlert")
            except FileNotFoundError:
                pass

        winreg.CloseKey(key)
    except Exception:
        # Autostart is best-effort; failures should not crash the app.
        pass
