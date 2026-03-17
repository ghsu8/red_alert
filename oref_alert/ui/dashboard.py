"""A simple visible UI to confirm the app is running."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QVBoxLayout, QWidget


class DashboardWindow(QWidget):
    """A small window shown on startup to confirm the app is running."""

    def __init__(self, on_open_settings: callable, on_exit: callable):
        super().__init__()
        self.setWindowTitle("Red Alert - רץ")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.WindowCloseButtonHint)
        self.setFixedSize(320, 140)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        label = QLabel("Red Alert רץ ברקע. לחץ על 'הגדרות' או סגור כדי להסתיר.")
        label.setWordWrap(True)
        layout.addWidget(label)

        btn_settings = QPushButton("הגדרות")
        btn_settings.clicked.connect(on_open_settings)
        layout.addWidget(btn_settings)

        btn_hide = QPushButton("הסתר")
        btn_hide.clicked.connect(self.hide)
        layout.addWidget(btn_hide)

        btn_exit = QPushButton("יציאה")
        btn_exit.clicked.connect(on_exit)
        layout.addWidget(btn_exit)

        self.setLayout(layout)

    def show(self) -> None:
        super().show()
        self.raise_()
        self.activateWindow()
