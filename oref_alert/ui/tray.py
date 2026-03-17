"""System tray integration for the Red Alert notifier."""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtGui import QAction, QIcon
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon, QStyle, QMainWindow

from oref_alert.ui.icons import create_lamp_icon


class TrayIcon:
    def __init__(
        self,
        icon_path: str,
        on_open_settings: Callable[[], None],
        on_open_log: Callable[[], None],
        on_exit: Callable[[], None],
        main_window: Optional[QMainWindow] = None,
    ):
        # Use custom red lamp icon
        if icon_path:
            icon = QIcon(icon_path)
        else:
            pixmap = create_lamp_icon(128)
            icon = QIcon(pixmap)

        self.tray = QSystemTrayIcon(icon)
        self.tray.setToolTip("Red Alert - מערכת התראות פיקוד העורף")
        self.main_window = main_window
        self._on_exit = on_exit
        self._on_open_settings = on_open_settings

        # Create menu with parent to ensure proper cleanup
        menu = QMenu()
        menu.setLayoutDirection(Qt.RightToLeft)  # RTL for Hebrew
        
        # Show/Hide window action
        if main_window:
            self.action_toggle = QAction("הראה/הסתר", menu)
            self.action_toggle.triggered.connect(self._toggle_window)
            menu.addAction(self.action_toggle)
            menu.addSeparator()

        action_show = QAction("הגדרות", menu)
        action_show.triggered.connect(on_open_settings)
        menu.addAction(action_show)

        action_log = QAction("יומן התראות", menu)
        action_log.triggered.connect(on_open_log)
        menu.addAction(action_log)

        menu.addSeparator()

        action_exit = QAction("יציאה", menu)
        action_exit.triggered.connect(self._handle_exit)
        menu.addAction(action_exit)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_activated)

    def _toggle_window(self) -> None:
        """Toggle main window visibility."""
        if self.main_window:
            if self.main_window.isVisible():
                self.main_window.hide()
            else:
                self.main_window.show()
                self.main_window.raise_()
                self.main_window.activateWindow()

    def _handle_exit(self) -> None:
        """Handle exit action from menu."""
        if self._on_exit:
            self._on_exit()

    def show(self) -> None:
        self.tray.show()

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Handle tray icon activation (click)."""
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            if self.main_window:
                self._toggle_window()
            else:
                self._on_open_settings()