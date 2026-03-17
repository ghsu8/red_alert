"""Core application bootstrap for the Red Alert notifier."""

from __future__ import annotations

import sys
from typing import List, Optional

from PySide6.QtWidgets import QApplication

from oref_alert.config import AppConfig, set_autostart
from oref_alert.log import get_logger
from oref_alert.notifier import AlertFetcher
from oref_alert.sound import play_alert_sound
from oref_alert.ui.dashboard import DashboardWindow
from oref_alert.ui.log_viewer import LogViewerDialog
from oref_alert.ui.main_window import SettingsWindow
from oref_alert.ui.popup import show_notification
from oref_alert.ui.tray import TrayIcon


class RedAlertApp:
    """High-level application class.

    This class ties the configuration, UI, and polling logic together.
    """

    def __init__(self) -> None:
        self.config = AppConfig()
        self.config.load()

        self.app = QApplication(sys.argv)
        self.tray_icon: Optional[TrayIcon] = None
        self._settings_window: Optional[SettingsWindow] = None
        self._dashboard_window: Optional[DashboardWindow] = None
        self._log_viewer: Optional[LogViewerDialog] = None

        # Keep track of the most recent alert cities so the map can show them
        self._last_alert_cities: List[str] = []

        self._logger = get_logger()

        self._fetcher = AlertFetcher(config=self.config, logger=self._logger)
        self._fetcher.new_alert.connect(self._on_new_alert)
        self._fetcher.fetch_error.connect(self._on_fetch_error)

    def run(self) -> None:
        self._setup_tray()
        self._apply_autostart()

        # Show a brief startup notification so the user can confirm the app is running.
        show_notification(
            title="Red Alert רץ",
            cities=["היישום פעיל"],
            details="האפליקציה רצה ברקע. לחץ על סמל המנורה במגש המערכת.",
            color="#22C55E",
            duration_ms=4000,
        )

        # Start fetcher but don't show any window initially
        self._fetcher.start()

        # Keep the app running even without a window
        self.app.exec()

    def _setup_tray(self) -> None:
        # Create settings window early so it can be passed to tray for show/hide
        self._settings_window = SettingsWindow(
            config=self.config,
            on_save=self._apply_autostart,
            on_test_alert=self._run_test_alert,
            on_exit=self._exit,
        )

        icon_path = self._get_default_icon_path()
        self.tray_icon = TrayIcon(
            icon_path,
            on_open_settings=self._open_settings,
            on_open_log=self._open_log,
            on_exit=self._exit,
            main_window=self._settings_window,
        )
        self.tray_icon.show()

    def _get_default_icon_path(self) -> str:
        # Provide a simple default icon (can be replaced with a real .ico file)
        # For now use a built-in Qt resource if available, otherwise empty string.
        return ""

    def _apply_autostart(self) -> None:
        set_autostart(self.config.autostart)

    def _on_new_alert(self, summary) -> None:
        """Handle a new alert from the fetcher."""
        # Keep track of what cities are currently in alert so the map preview can highlight them.
        self._last_alert_cities = summary.cities or []
        if self._settings_window:
            self._settings_window.set_alert_cities_for_map(self._last_alert_cities)

        play_alert_sound(self.config)
        duration_ms = 0 if self.config.popup_duration_seconds is None else self.config.popup_duration_seconds * 1000
        show_notification(
            title=summary.title,
            cities=summary.cities,
            details=summary.details,
            color=summary.color,
            duration_ms=duration_ms,
        )

    def _on_fetch_error(self, error: str) -> None:
        # In the future the UI could show a non-intrusive error state or log.
        print("Fetch error:", error)

    def _open_settings(self) -> None:
        if self._settings_window:
            # Ensure the map preview is updated with the latest alert cities
            self._settings_window.set_alert_cities_for_map(self._last_alert_cities)
            self._settings_window.show()
            self._settings_window.raise_()
            self._settings_window.activateWindow()


    def _run_test_alert(self) -> None:
        """Simulate an alert so the user can see the UI / sound without real data."""
        # Build a safe fixed test payload
        summary = type(
            "_",
            (),
            {
                "title": "סימולציית התראה",
                "cities": [self.config.poi_city or "תל אביב"],
                "details": "זו התראה לדוגמה כדי לבדוק את התצוגה והצליל.",
                "color": "#3B82F6",
            },
        )()

        play_alert_sound(self.config)
        show_notification(
            title=summary.title,
            cities=summary.cities,
            details=summary.details,
            color=summary.color,
        )

    def _open_log(self) -> None:
        if self._log_viewer and self._log_viewer.isVisible():
            self._log_viewer.raise_()
            return

        self._log_viewer = LogViewerDialog()
        self._log_viewer.show()

    def _exit(self) -> None:
        self._fetcher.stop()
        QApplication.quit()
