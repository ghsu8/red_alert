"""Dialog for viewing the alert fetch log."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QPushButton, QPlainTextEdit, QVBoxLayout, QSpinBox, QLabel

from oref_alert.log import get_logger


class LogViewerDialog(QDialog):
    def __init__(self, parent: Optional[QDialog] = None):
        super().__init__(parent)
        self.setWindowTitle("יומן התראות")
        self.resize(800, 600)

        self._text = QPlainTextEdit(self)
        self._text.setReadOnly(True)
        self._text.setLineWrapMode(QPlainTextEdit.NoWrap)

        # Lines selector
        lines_layout = QHBoxLayout()
        lines_layout.addWidget(QLabel("הצג שורות אחרונות:"))
        self._lines_spin = QSpinBox()
        self._lines_spin.setRange(10, 1000)
        self._lines_spin.setValue(50)
        self._lines_spin.setSingleStep(10)
        lines_layout.addWidget(self._lines_spin)
        lines_layout.addStretch()

        self._btn_refresh = QPushButton("רענן")
        self._btn_refresh.clicked.connect(self._refresh)

        self._btn_close = QPushButton("סגור")
        self._btn_close.clicked.connect(self.close)

        btn_bar = QHBoxLayout()
        btn_bar.addLayout(lines_layout)
        btn_bar.addWidget(self._btn_refresh)
        btn_bar.addStretch(1)
        btn_bar.addWidget(self._btn_close)

        layout = QVBoxLayout(self)
        layout.addWidget(self._text)
        layout.addLayout(btn_bar)

        self._refresh()

        # Auto-refresh every 5 seconds
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(5000)

    def closeEvent(self, event):
        self._timer.stop()
        super().closeEvent(event)

    def _refresh(self) -> None:
        logger = get_logger()
        all_entries = list(logger.entries())
        num_lines = self._lines_spin.value()
        entries = all_entries[-num_lines:] if len(all_entries) > num_lines else all_entries
        # Show newest entries first
        entries = list(reversed(entries))

        lines = []
        for entry in entries:
            ts = entry.get("timestamp", "")
            if entry.get("fetch_success") is False:
                lines.append(f"{ts}  ❌ fetch failed: {entry.get('error', '')}")
                continue

            if not entry.get("alert_present"):
                lines.append(f"{ts}  (no alert)")
                continue

            ctx = []
            mode = entry.get("filter_mode")
            if mode:
                ctx.append(f"מצב: {mode}")

            regs = entry.get("selected_regions") or []
            if regs:
                ctx.append(f"אזורים: {', '.join(regs)}")

            cities = entry.get("selected_cities") or []
            if cities:
                ctx.append(f"ערים: {', '.join(cities)}")

            matched = entry.get("matched_cities") or []
            matched_str = ", ".join(matched) if matched else "(ללא התאמה)"

            lines.append(f"{ts}  ✅ {matched_str}  [{' | '.join(ctx)}]")

        self._text.setPlainText("\n".join(lines))
        # Scroll to top (newest entries first)
        self._text.verticalScrollBar().setValue(self._text.verticalScrollBar().minimum())
