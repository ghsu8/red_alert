"""Edge popup notification widget."""

from __future__ import annotations

from typing import List

from PySide6.QtCore import QPropertyAnimation, QEasingCurve, Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QVBoxLayout, QWidget


class PopupNotification(QWidget):
    """A small hover popup shown at the right edge of the screen."""

    def __init__(
        self,
        title: str,
        cities: List[str],
        details: str | None = None,
        color: str = "#EF4444",
        duration_ms: int = 8000,
        expand_threshold: int = 3,
        offset_y: int = 0,
    ):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlag(Qt.WindowDoesNotAcceptFocus)

        self.duration_ms = duration_ms
        self._cities = cities
        self._details = details
        self._expand_threshold = expand_threshold
        self._expanded = False
        self._offset_y = offset_y

        self._setup_ui(title, color)
        self._animate_in()

    def _setup_ui(self, title: str, color: str) -> None:
        self.resize(360, 180)
        self.move_to_edge()

        self._container = QWidget(self)
        self._container.setObjectName("popupContainer")
        self._container.setStyleSheet(
            "#popupContainer { background: rgba(24,24,27,0.95); border-radius: 16px; border: 1px solid rgba(255,255,255,0.15); }"
        )

        layout = QVBoxLayout(self._container)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.title_label = QLabel(title)
        self.title_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.title_label.setStyleSheet(f"color: white; background: {color}; padding: 6px; border-radius: 8px;")
        layout.addWidget(self.title_label)

        self._cities_label = QLabel(self._format_cities())
        self._cities_label.setWordWrap(True)
        self._cities_label.setStyleSheet("color: white;")
        self._cities_label.setFont(QFont("Segoe UI", 10))
        layout.addWidget(self._cities_label)

        if len(self._cities) > self._expand_threshold:
            self._toggle_button = QPushButton("הצג עוד")
            self._toggle_button.setStyleSheet(
                "QPushButton { color: white; background: rgba(255,255,255,0.08); border-radius: 10px; }"
                "QPushButton:hover { background: rgba(255,255,255,0.18); }"
            )
            self._toggle_button.clicked.connect(self._toggle_expand)
            layout.addWidget(self._toggle_button, alignment=Qt.AlignLeft)

        if self._details:
            self._details_label = QLabel(self._details)
            self._details_label.setWordWrap(True)
            self._details_label.setStyleSheet("color: #E5E7EB;")
            self._details_label.setFont(QFont("Segoe UI", 9))
            layout.addWidget(self._details_label)

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(26, 26)
        btn_close.setStyleSheet(
            "QPushButton { color: white; background: rgba(255,255,255,0.08); border-radius: 13px; }"
            "QPushButton:hover { background: rgba(255,255,255,0.18); }"
        )
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close, alignment=Qt.AlignRight)

        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self._container)

        self._expire_timer = QTimer(self)
        self._expire_timer.setSingleShot(True)
        self._expire_timer.timeout.connect(self._animate_out)
        if self.duration_ms > 0:
            self._expire_timer.start(self.duration_ms)

    def _format_cities(self) -> str:
        if not self._cities:
            return ""

        if self._expanded or len(self._cities) <= self._expand_threshold:
            return "ערים: " + ", ".join(self._cities)

        short = ", ".join(self._cities[: self._expand_threshold])
        remaining = len(self._cities) - self._expand_threshold
        return f"ערים: {short} ועוד {remaining}"

    def _toggle_expand(self) -> None:
        self._expanded = not self._expanded
        self._cities_label.setText(self._format_cities())
        if hasattr(self, "_toggle_button"):
            self._toggle_button.setText("הצג פחות" if self._expanded else "הצג עוד")

    def move_to_edge(self) -> None:
        screen = QApplication.primaryScreen()
        rect = screen.availableGeometry()
        x = rect.x() + rect.width() - self.width() - 20
        y = rect.y() + 20 + self._offset_y
        self.move(x, y)

    def update_offset(self, new_offset: int) -> None:
        self._offset_y = new_offset
        self.move_to_edge()

    def _animate_in(self) -> None:
        self.setWindowOpacity(0.0)
        self.show()
        self.anim = QPropertyAnimation(self, b"windowOpacity")
        self.anim.setDuration(350)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setEasingCurve(QEasingCurve.InOutCubic)
        self.anim.start()

    def _animate_out(self) -> None:
        self.anim = QPropertyAnimation(self, b"windowOpacity")
        self.anim.setDuration(350)
        self.anim.setStartValue(self.windowOpacity())
        self.anim.setEndValue(0.0)
        self.anim.setEasingCurve(QEasingCurve.InOutCubic)
        self.anim.finished.connect(self.close)
        self.anim.start()


_active_popups: list[PopupNotification] = []


def _cleanup_popup(popup: PopupNotification) -> None:
    try:
        removed_offset = popup._offset_y
        _active_popups.remove(popup)
        # Shift remaining popups up
        for p in _active_popups:
            if p._offset_y > removed_offset:
                p.update_offset(p._offset_y - 190)
    except ValueError:
        pass


def show_notification(
    title: str,
    cities: List[str],
    details: str | None,
    color: str,
    duration_ms: int = 8000,
) -> None:
    """Convenience helper for showing a notification in the current Qt application."""
    # Ensure we do not create a second QApplication if one exists already.
    if not QApplication.instance():
        _ = QApplication([])

    # Shift existing popups down
    for popup in _active_popups:
        popup.update_offset(popup._offset_y + 190)

    # If we have 3 or more, remove the bottom one
    if len(_active_popups) >= 3:
        bottom_popup = _active_popups[0]
        bottom_popup.close()
        _active_popups.remove(bottom_popup)

    popup = PopupNotification(
        title=title,
        cities=cities,
        details=details,
        color=color,
        duration_ms=duration_ms,
        offset_y=0,
    )

    # Keep a reference so Python doesn't garbage-collect the widget immediately.
    _active_popups.append(popup)
    popup.destroyed.connect(lambda: _cleanup_popup(popup))
    popup.show()
