"""Settings window for the Red Alert notifier."""

from __future__ import annotations

import os
import sys
import csv
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, List

from PySide6.QtCore import Qt, QUrl, QTimer
from PySide6.QtGui import QAction, QKeySequence, QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QHeaderView,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from oref_alert.config import AppConfig, AlertMode, AlertSound
from oref_alert.data import all_cities, city_coordinates, city_regions, regions
from oref_alert.log import get_logger
from oref_alert.map import known_locations_with_coordinates, resolve_location_coordinates
from oref_alert.ui.map_view import InteractiveMapWidget
from oref_alert.utils import compute_distance_km
from oref_alert import __version__


def format_timestamp(ts: str) -> str:
    """Format ISO timestamp to 'YYYY-MM-DD HH:MM' format."""
    if not ts:
        return ""
    try:
        dt = datetime.fromisoformat(ts)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ts


class SettingsWindow(QDialog):
    """Main configuration window for the application."""

    def __init__(
        self,
        config: AppConfig,
        on_save: Callable[[], None] | None = None,
        on_test_alert: Callable[[], None] | None = None,
        on_exit: Callable[[], None] | None = None,
    ):
        super().__init__()
        self.setWindowTitle("Red Alert - הגדרות")
        self.setWindowFlag(Qt.WindowStaysOnTopHint)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setMinimumSize(760, 620)
        self.resize(860, 700)

        self._config = config
        self._on_save = on_save
        self._on_test_alert = on_test_alert
        self._on_exit = on_exit

        self._tabs = QTabWidget(self)
        self._tabs.setLayoutDirection(Qt.RightToLeft)
        self._tabs.addTab(self._build_sound_tab(), "צלילים והתראות")
        self._tabs.addTab(self._build_filters_tab(), "סינון ומיקום")
        self._tabs.addTab(self._build_log_tab(), "יומן")
        self._tabs.addTab(self._build_misc_tab(), "כללי")
        self._tabs.addTab(self._build_about_tab(), "אודות")
        self._tabs.currentChanged.connect(self._on_tab_changed)

        self._log_auto_refresh_timer = QTimer(self)
        self._log_auto_refresh_timer.timeout.connect(self._on_log_auto_refresh_tick)

        # Track the latest alert cities for map display
        self._alert_cities_for_map: List[str] = []

        layout = QVBoxLayout(self)
        layout.addWidget(self._tabs)

        self._button_save = QPushButton("שמור")
        self._button_save.clicked.connect(self._on_save_clicked)
        layout.addWidget(self._button_save, alignment=Qt.AlignRight)

        # Add Alt+F4 to force close the application
        self._setup_keyboard_shortcuts()

        self._load_config_state()

    def closeEvent(self, event):
        """Ask whether to minimize to tray or exit when the user closes the window."""
        
        # Save current state before closing
        self._save_current_state_to_config()

        msg = QMessageBox(self)
        msg.setWindowTitle("האם ברצונך לצאת או למזער את האפליקציה?")
        msg.setText("בחר פעולה:")
        msg.setIcon(QMessageBox.Question)

        btn_minimize = msg.addButton("מזער", QMessageBox.AcceptRole)
        btn_exit = msg.addButton("צא", QMessageBox.DestructiveRole)

        msg.exec()

        if msg.clickedButton() == btn_minimize:
            event.ignore()
            self.hide()
        else:
            event.accept()
            if self._on_exit:
                self._on_exit()

    def _save_current_state_to_config(self) -> None:
        """Save current UI state to config without triggering save callbacks."""
        self._config.sound_mode = self._sound_mode.currentText()
        self._config.custom_sound_path = self._custom_sound_path.text() or ""
        self._config.alert_mode = self._alert_mode.currentText()
        self._config.selected_regions = self._selected_regions() or ["כל האזורים"]
        self._config.selected_cities = self._selected_cities()
        self._config.selected_region = self._config.selected_regions[0]
        self._config.selected_city = self._config.selected_cities[0] if self._config.selected_cities else ""
        self._config.poi_city = self._poi_city.currentText()
        self._config.poi_distance_km = float(self._poi_distance.value())
        self._config.google_maps_api_key = self._google_maps_api_key.text().strip()
        self._config.use_google_maps = self._use_google_maps_checkbox.isChecked()
        self._config.autostart = self._autostart_checkbox.isChecked()
        self._config.debug_logging = self._debug_logging_checkbox.isChecked()
        self._config.log_auto_refresh_enabled = self._log_auto_refresh_checkbox.isChecked()
        self._config.log_auto_refresh_interval_seconds = self._log_refresh_interval_seconds_from_ui()
        self._config.popup_duration_seconds = None if self._popup_manual.isChecked() else self._popup_duration.value()
        self._config.save()
        self._update_log_auto_refresh_timer()

    def _setup_keyboard_shortcuts(self) -> None:
        """Setup keyboard shortcuts like Alt+F4 for closing."""
        action_close = QAction(self)
        action_close.setShortcut(QKeySequence.Quit)  # Alt+F4 or Cmd+Q on Mac
        action_close.triggered.connect(self._force_close)
        self.addAction(action_close)

    def _force_close(self) -> None:
        """Force close the application completely."""
        if self._on_exit:
            self._on_exit()

    def _build_sound_tab(self) -> QWidget:
        container = QWidget()
        form = QFormLayout(container)

        self._sound_mode = QComboBox()
        self._sound_mode.addItems([AlertSound.DEFAULT, AlertSound.SILENT, AlertSound.CUSTOM])
        form.addRow("מצב צליל:", self._sound_mode)

        self._custom_sound_path = QLineEdit()
        self._btn_browse_sound = QPushButton("בחר קובץ")
        self._btn_browse_sound.clicked.connect(self._browse_sound)

        row = QWidget()
        row_layout = QVBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.addWidget(self._custom_sound_path)
        row_layout.addWidget(self._btn_browse_sound)
        form.addRow("צליל מותאם אישית:", row)

        # Popup settings
        popup_group = QGroupBox("התראות פופאפ")
        popup_layout = QFormLayout(popup_group)

        self._popup_manual = QCheckBox("עד לסגירה ידנית")
        self._popup_manual.stateChanged.connect(self._on_popup_manual_changed)
        popup_layout.addRow("", self._popup_manual)

        self._popup_duration = QSpinBox()
        self._popup_duration.setRange(1, 60)
        self._popup_duration.setValue(10)
        self._popup_duration.setSuffix(" שניות")
        popup_layout.addRow("זמן הצגה:", self._popup_duration)

        form.addRow(popup_group)

        container.setLayout(form)
        return container

    def _build_filters_tab(self) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)

        # Left: filters
        filters_container = QWidget()
        filters_layout = QVBoxLayout(filters_container)

        region_group = QGroupBox("סינון לפי אזור / עיר")
        region_layout = QFormLayout(region_group)

        self._alert_mode = QComboBox()
        self._alert_mode.addItems([AlertMode.ALL, AlertMode.CUSTOM, AlertMode.POI])
        self._alert_mode.currentTextChanged.connect(self._on_alert_mode_changed)
        region_layout.addRow("הצג התראות:", self._alert_mode)

        self._region_label = QLabel("נבחרים: כל האזורים")
        region_layout.addRow("נבחרים:", self._region_label)

        self._region_selector = QListWidget()
        self._region_selector.setSelectionMode(QAbstractItemView.MultiSelection)
        for r in regions:
            self._region_selector.addItem(QListWidgetItem(r))
        self._region_selector.itemSelectionChanged.connect(self._on_region_changed)
        region_layout.addRow("אזור:", self._region_selector)

        self._city_search = QLineEdit()
        self._city_search.setPlaceholderText("חפש עיר...")
        self._city_search.textChanged.connect(self._on_city_search_changed)
        region_layout.addRow("חיפוש עיר:", self._city_search)

        self._city_selector = QListWidget()
        self._city_selector.setSelectionMode(QAbstractItemView.MultiSelection)
        self._city_selector.addItems(sorted(all_cities))
        region_layout.addRow("עיר:", self._city_selector)

        self._select_all_cities_btn = QPushButton("בחר את כל הערים באזור/אזורים")
        self._select_all_cities_btn.clicked.connect(self._select_all_cities_in_selected_regions)
        region_layout.addRow("", self._select_all_cities_btn)

        filters_layout.addWidget(region_group)

        poi_group = QGroupBox("נקודת ייחוס")
        poi_layout = QFormLayout(poi_group)

        self._poi_city = QComboBox()
        self._poi_city.addItems(sorted(all_cities))
        self._poi_city.currentTextChanged.connect(lambda _: self._update_map_preview())
        poi_layout.addRow("עיר:", self._poi_city)

        self._poi_distance = QSpinBox()
        self._poi_distance.setRange(1, 500)
        self._poi_distance.setSuffix(" ק""מ")
        self._poi_distance.valueChanged.connect(lambda _: self._update_map_preview())
        poi_layout.addRow("מרחק:", self._poi_distance)

        filters_layout.addWidget(poi_group)

        # Map preview
        map_group = QGroupBox("מפה")
        map_layout = QVBoxLayout(map_group)
        self._map_widget = InteractiveMapWidget()
        self._map_widget.setMinimumSize(360, 360)
        map_layout.addWidget(self._map_widget)

        layout.addWidget(filters_container, stretch=2)
        layout.addWidget(map_group, stretch=1)

        container.setLayout(layout)
        return container

    def _selected_regions(self) -> List[str]:
        return [item.text() for item in self._region_selector.selectedItems()]

    def _selected_cities(self) -> List[str]:
        return [item.text() for item in self._city_selector.selectedItems()]

    def _cities_for_regions(self, regions: List[str]) -> List[str]:
        """Return the list of cities for the given region(s)."""

        if not regions or "כל האזורים" in regions:
            return sorted(all_cities)

        cities = set()
        for region in regions:
            cities.update({city for city, grp in city_regions.items() if grp == region})
        return sorted(cities)

    def _filtered_cities(self) -> List[str]:
        """Return cities that match the selected regions and the search text."""

        cities = self._cities_for_regions(self._selected_regions())
        query = self._city_search.text().strip().lower()
        if not query:
            return cities

        return [c for c in cities if query in c.lower()]

    def _on_region_changed(self) -> None:
        """Update the list of cities when the selected regions change."""

        selected_regions = self._selected_regions()
        display_label = ", ".join(selected_regions) if selected_regions else "כל האזורים"
        self._region_label.setText(f"נבחרים: {display_label}")

        current_selected_cities = set(self._selected_cities())
        cities = self._filtered_cities()

        self._city_selector.clear()
        self._city_selector.addItems(cities)

        # Restore previously selected cities when still available.
        for i in range(self._city_selector.count()):
            item = self._city_selector.item(i)
            if item.text() in current_selected_cities:
                item.setSelected(True)

        self._update_map_preview()

    def _on_popup_manual_changed(self, state: int) -> None:
        self._popup_duration.setEnabled(state == 0)  # Enabled when not checked

    def _on_city_search_changed(self) -> None:
        """Re-filter city list when the search text changes."""

        current_selected_cities = set(self._selected_cities())
        cities = self._filtered_cities()

        self._city_selector.clear()
        self._city_selector.addItems(cities)

        # Restore selections that are still visible.
        for i in range(self._city_selector.count()):
            item = self._city_selector.item(i)
            if item.text() in current_selected_cities:
                item.setSelected(True)

    def _select_all_cities_in_selected_regions(self) -> None:
        """Toggle select all visible cities (based on region and search filter)."""
        cities_to_select = set(self._filtered_cities())
        all_selected = all(
            self._city_selector.item(i).isSelected()
            for i in range(self._city_selector.count())
            if self._city_selector.item(i).text() in cities_to_select
        )
        if all_selected:
            # Deselect all
            for i in range(self._city_selector.count()):
                item = self._city_selector.item(i)
                if item.text() in cities_to_select:
                    item.setSelected(False)
        else:
            # Select all
            for i in range(self._city_selector.count()):
                item = self._city_selector.item(i)
                item.setSelected(item.text() in cities_to_select)

    def _build_log_tab(self) -> QWidget:
        container = QWidget()
        container.setLayoutDirection(Qt.RightToLeft)
        self._log_tab = container
        layout = QVBoxLayout(container)

        def make_field_pair(label_text: str, field: QWidget, *, stretch: int = 0) -> QWidget:
            pair = QWidget()
            pair.setLayoutDirection(Qt.LeftToRight)
            pair_layout = QHBoxLayout(pair)
            pair_layout.setContentsMargins(0, 0, 0, 0)
            pair_layout.setSpacing(6)
            pair_layout.setDirection(QHBoxLayout.LeftToRight)
            label = QLabel(label_text)
            label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if stretch:
                pair_layout.addWidget(field, stretch)
            else:
                pair_layout.addWidget(field)
            pair_layout.addWidget(label)
            return pair

        # Status label
        self._log_status = QLabel("סטטוס: מחכה לבדיקה...")
        layout.addWidget(self._log_status)

        top_controls_layout = QHBoxLayout()
        top_controls_layout.setDirection(QHBoxLayout.RightToLeft)
        top_controls_layout.setAlignment(Qt.AlignRight)

        self._log_lines_spin = QSpinBox()
        self._log_lines_spin.setRange(10, 1000)
        self._log_lines_spin.setValue(50)
        self._log_lines_spin.setSingleStep(10)
        self._log_lines_spin.valueChanged.connect(lambda: self._refresh_log())

        top_controls_layout.addWidget(make_field_pair("הצג שורות:", self._log_lines_spin))

        self._log_prev_match_btn = QPushButton("◀")
        self._log_prev_match_btn.setToolTip("התאמה קודמת")
        self._log_prev_match_btn.clicked.connect(lambda: self._jump_to_highlight(-1))
        self._log_prev_match_btn.setEnabled(False)
        top_controls_layout.addWidget(self._log_prev_match_btn)

        self._log_next_match_btn = QPushButton("▶")
        self._log_next_match_btn.setToolTip("התאמה הבאה")
        self._log_next_match_btn.clicked.connect(lambda: self._jump_to_highlight(1))
        self._log_next_match_btn.setEnabled(False)
        top_controls_layout.addWidget(self._log_next_match_btn)

        self._log_match_counter = QLabel("0/0")
        top_controls_layout.addWidget(self._log_match_counter)
        top_controls_layout.addStretch(1)

        layout.addLayout(top_controls_layout)

        second_controls_layout = QHBoxLayout()
        second_controls_layout.setDirection(QHBoxLayout.RightToLeft)
        second_controls_layout.setAlignment(Qt.AlignRight)

        self._log_time_filter = QComboBox()
        self._log_time_filter.addItems(["הכל", "שעה אחרונה", "6 שעות", "24 שעות", "7 ימים"])
        self._log_time_filter.currentTextChanged.connect(lambda _: self._refresh_log())
        second_controls_layout.addWidget(make_field_pair("טווח זמן:", self._log_time_filter))

        self._log_filter = QComboBox()
        self._log_filter.addItems(["הכל", "ירי טילים", "כלי טיס עוין", "התראה מקדימה", "אירוע הסתיים", "no alert"])
        self._log_filter.currentTextChanged.connect(self._on_log_filter_changed)
        second_controls_layout.addWidget(make_field_pair("סנן לפי סוג:", self._log_filter))

        self._log_search = QLineEdit()
        self._log_search.setPlaceholderText("חיפוש לפי מלל...")
        self._log_search.setAlignment(Qt.AlignRight)
        self._log_search.textChanged.connect(self._on_log_search_changed)
        second_controls_layout.addWidget(make_field_pair("חיפוש:", self._log_search, stretch=1), 1)

        layout.addLayout(second_controls_layout)

        self._log_table = QTableWidget(0, 4)
        self._log_table.setLayoutDirection(Qt.RightToLeft)
        self._log_table.setHorizontalHeaderLabels(["תאריך", "שעה", "סוג התראה", "אזורים"])
        self._log_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._log_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._log_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._log_table.setAlternatingRowColors(True)
        self._log_table.verticalHeader().setVisible(False)
        self._log_table.horizontalHeader().setStretchLastSection(True)
        self._log_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self._log_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._log_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._log_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self._log_table.setStyleSheet(
            "QTableWidget { background: #1f1f1f; alternate-background-color: #2b2b2b; gridline-color: #3a3a3a; color: white; }"
            "QHeaderView::section { background: #2d2d2d; color: white; padding: 6px; border: 1px solid #3a3a3a; }"
            "QTableWidget::item:selected { background: #0f766e; color: white; }"
        )
        layout.addWidget(self._log_table)

        self._highlight_ranges: list[int] = []
        self._highlight_index: int = -1

        # Buttons row
        btn_layout = QVBoxLayout()
        buttons = QVBoxLayout()
        
        btn_refresh = QPushButton("רענון")
        btn_refresh.clicked.connect(lambda: self._refresh_log())
        buttons.addWidget(btn_refresh)

        btn_export = QPushButton("EXPORT TO CSV")
        btn_export.clicked.connect(lambda: self._export_log_csv())
        buttons.addWidget(btn_export)

        btn_clear = QPushButton("נקה לוג")
        btn_clear.clicked.connect(lambda: self._clear_log())
        buttons.addWidget(btn_clear)

        # Arrange buttons horizontally
        buttons_row = QVBoxLayout()
        h_layout = QVBoxLayout()
        h_layout.addWidget(btn_refresh)
        buttons_row.addLayout(h_layout)
        
        h_layout2 = QVBoxLayout()
        h_layout2.addWidget(btn_export)
        buttons_row.addLayout(h_layout2)
        
        h_layout3 = QVBoxLayout()
        h_layout3.addWidget(btn_clear)
        buttons_row.addLayout(h_layout3)

        btn_layout_h = QVBoxLayout()
        btn_layout_h.addWidget(btn_refresh)
        btn_layout_h.addWidget(btn_export)
        btn_layout_h.addWidget(btn_clear)
        layout.addLayout(btn_layout_h)

        self._refresh_log()
        container.setLayout(layout)
        return container

    def _on_log_search_changed(self, text: str) -> None:
        """Filter log entries based on search text."""
        self._refresh_log(search_text=text)

    def _on_log_filter_changed(self, text: str) -> None:
        """Filter log entries based on alert type."""
        self._refresh_log()

    def _on_tab_changed(self, index: int) -> None:
        # Refresh log view when switching to the log tab.
        if self._tabs.tabText(index) == "יומן":
            self._refresh_log()
        self._update_log_auto_refresh_timer()

    def _log_refresh_interval_seconds_from_ui(self) -> int:
        value = self._log_auto_refresh_value.value() if hasattr(self, "_log_auto_refresh_value") else 30
        unit = self._log_auto_refresh_unit.currentText() if hasattr(self, "_log_auto_refresh_unit") else "שניות"
        if unit == "דקות":
            return max(1, value * 60)
        return max(1, value)

    def _sync_log_refresh_controls(self) -> None:
        enabled = self._log_auto_refresh_checkbox.isChecked() if hasattr(self, "_log_auto_refresh_checkbox") else False
        if hasattr(self, "_log_auto_refresh_value"):
            self._log_auto_refresh_value.setEnabled(enabled)
        if hasattr(self, "_log_auto_refresh_unit"):
            self._log_auto_refresh_unit.setEnabled(enabled)

    def _update_log_auto_refresh_timer(self) -> None:
        if not hasattr(self, "_log_auto_refresh_checkbox"):
            return

        self._sync_log_refresh_controls()

        is_log_tab = self._tabs.currentWidget() is getattr(self, "_log_tab", None)
        if not self._log_auto_refresh_checkbox.isChecked() or not is_log_tab:
            self._log_auto_refresh_timer.stop()
            return

        interval_ms = self._log_refresh_interval_seconds_from_ui() * 1000
        self._log_auto_refresh_timer.start(interval_ms)

    def _on_log_auto_refresh_tick(self) -> None:
        if self._tabs.currentWidget() is getattr(self, "_log_tab", None):
            self._refresh_log()

    def _time_filter_delta(self) -> timedelta | None:
        value = self._log_time_filter.currentText() if hasattr(self, "_log_time_filter") else "הכל"
        if value == "שעה אחרונה":
            return timedelta(hours=1)
        if value == "6 שעות":
            return timedelta(hours=6)
        if value == "24 שעות":
            return timedelta(hours=24)
        if value == "7 ימים":
            return timedelta(days=7)
        return None

    def _entry_in_time_window(self, entry: dict, window: timedelta | None) -> bool:
        if window is None:
            return True

        ts = entry.get("timestamp")
        if not ts:
            return False

        try:
            dt = datetime.fromisoformat(ts)
        except Exception:
            return False
        return dt >= datetime.now() - window

    def _entry_matches_search(self, entry: dict, formatted: str, search_text: str) -> bool:
        if not search_text:
            return True

        tokens = [t for t in search_text.lower().split() if t]
        if not tokens:
            return True

        blob = " ".join(
            [
                formatted.lower(),
                " ".join((entry.get("alert_cities") or [])).lower(),
                " ".join((entry.get("matched_cities") or [])).lower(),
                " ".join((entry.get("poi_matched_cities") or [])).lower(),
                (entry.get("decision_reason") or "").lower(),
                (entry.get("filter_mode") or "").lower(),
                (entry.get("error") or "").lower(),
                (entry.get("poi_city") or "").lower(),
            ]
        )

        for token in tokens:
            if ":" in token:
                key, value = token.split(":", 1)
                value = value.strip()
                if not value:
                    continue

                if key == "city":
                    haystack = [c.lower() for c in (entry.get("alert_cities") or [])]
                    if not any(value in c for c in haystack):
                        return False
                elif key == "mode":
                    if value not in (entry.get("filter_mode") or "").lower():
                        return False
                elif key == "reason":
                    if value not in (entry.get("decision_reason") or "").lower():
                        return False
                elif key == "status":
                    status = "displayed" if entry.get("displayed") else "filtered"
                    if entry.get("fetch_success") is False:
                        status = "error"
                    if not entry.get("alert_present"):
                        status = "noalert"
                    if value != status:
                        return False
                elif key == "type":
                    if value not in (entry.get("alert_type") or "").lower() and value not in formatted.lower():
                        return False
                else:
                    if token not in blob:
                        return False
            else:
                if token not in blob:
                    return False

        return True

    def _highlight_search_matches(self, search_text: str) -> None:
        """Track visible rows for next/previous navigation in the log table."""
        if not search_text.strip():
            self._highlight_ranges = []
            self._highlight_index = -1
            self._log_table.clearSelection()
            self._update_highlight_nav_ui()
            return

        row_count = self._log_table.rowCount() if hasattr(self, "_log_table") else 0
        self._highlight_ranges = list(range(row_count))
        self._highlight_index = 0 if row_count else -1
        self._update_highlight_nav_ui()
        if row_count:
            self._log_table.selectRow(self._highlight_index)

    def _update_highlight_nav_ui(self) -> None:
        total = len(getattr(self, "_highlight_ranges", []))
        has_matches = total > 0

        if hasattr(self, "_log_prev_match_btn"):
            self._log_prev_match_btn.setEnabled(has_matches)
        if hasattr(self, "_log_next_match_btn"):
            self._log_next_match_btn.setEnabled(has_matches)

        if hasattr(self, "_log_match_counter"):
            if not has_matches:
                self._log_match_counter.setText("0/0")
            else:
                self._log_match_counter.setText(f"{self._highlight_index + 1}/{total}")

    def _jump_to_highlight(self, step: int) -> None:
        if not self._highlight_ranges:
            return

        total = len(self._highlight_ranges)
        self._highlight_index = (self._highlight_index + step) % total
        row = self._highlight_ranges[self._highlight_index]
        self._log_table.selectRow(row)
        self._log_table.scrollToItem(self._log_table.item(row, 0), QAbstractItemView.PositionAtCenter)
        self._update_highlight_nav_ui()

    def _refresh_log(self, search_text: str = "") -> None:
        logger = get_logger()
        if not search_text:
            search_text = self._log_search.text() if hasattr(self, "_log_search") else ""
        search_text = search_text.lower().strip()

        alert_type_names = {
            "T": "ירי טילים",
            "A": "כלי טיס עוין",
            "EW": "התראה מקדימה",
            "ALL": "אירוע הסתיים",
            "UNKNOWN": "לא ידוע (כניסה ישנה)",
            None: "no alert"
        }

        entries = logger.entries()
        window = self._time_filter_delta()
        entries = [e for e in entries if self._entry_in_time_window(e, window)]

        # In normal mode, hide noisy connectivity/no-alert polling records.
        debug_enabled = self._debug_logging_checkbox.isChecked() if hasattr(self, "_debug_logging_checkbox") else self._config.debug_logging
        if not debug_enabled:
            quiet_reasons = {"no_payload", "no_alert_in_payload", "invalid_json", "duplicate_alert_id"}
            entries = [
                e
                for e in entries
                if not (
                    e.get("fetch_success") is True
                    and not e.get("alert_present")
                    and (e.get("decision_reason") in quiet_reasons or not e.get("decision_reason"))
                )
            ]

        # Ensure backward compatibility with old log entries that don't have alert_type field
        for entry in entries:
            if "alert_type" not in entry:
                if entry.get("alert_present"):
                    # Old entry with alert but no type information - mark as unknown
                    entry["alert_type"] = "UNKNOWN"
                else:
                    # Old entry without alert
                    entry["alert_type"] = None
            if "decision_reason" not in entry:
                entry["decision_reason"] = "legacy"
            if "displayed" not in entry:
                entry["displayed"] = bool(entry.get("alert_present") and entry.get("matched_cities"))

        # Apply type filter
        filter_type = self._log_filter.currentText()
        if filter_type != "הכל":
            if filter_type == "no alert":
                entries = [e for e in entries if not e.get("alert_present")]
            else:
                filter_mapping = {
                    "ירי טילים": "T",
                    "כלי טיס עוין": "A",
                    "התראה מקדימה": "EW",
                    "אירוע הסתיים": "ALL"
                }
                mapped = filter_mapping.get(filter_type)
                entries = [e for e in entries if e.get("alert_type") == mapped]

        if entries:
            latest = entries[-1]
            ts = latest.get("timestamp", "")
            formatted_ts = format_timestamp(ts)
            self._log_status.setText(f"סטטוס: בדיקה אחרונה: {formatted_ts} ({len(entries)} כניסות בלוג)")
        else:
            self._log_status.setText("סטטוס: אין בדיקות עדיין (מחכה לבדיקה כל 5 שניות)")

        rows: list[tuple[str, str, str, str, str]] = []
        # Show newest entries first
        entries = list(reversed(entries))

        # Limit to the user-selected number of lines
        num_lines = self._log_lines_spin.value() if hasattr(self, "_log_lines_spin") else len(entries)
        entries = entries[:num_lines]

        for entry in entries:
            ts = entry.get("timestamp", "")
            formatted_ts = format_timestamp(ts)
            try:
                dt = datetime.fromisoformat(ts) if ts else None
            except Exception:
                dt = None
            date_text = dt.strftime("%Y-%m-%d") if dt else formatted_ts.split(" ")[0] if formatted_ts else ""
            time_text = dt.strftime("%H:%M:%S") if dt else (formatted_ts.split(" ")[1] if " " in formatted_ts else "")
            
            # Build the formatted line
            if entry.get("fetch_success") is False:
                alert_type_text = "שגיאה"
                areas_text = entry.get("error", "") or "-"
                formatted = f"{formatted_ts}  ❌ fetch failed: {areas_text}"
            elif not entry.get("alert_present"):
                reason = entry.get("decision_reason") or "no_alert"
                alert_type_text = "ללא התראה"
                areas_text = f"[{reason}]"
                formatted = f"{formatted_ts}  (no alert) [{reason}]"
            else:
                alert_type = entry.get("alert_type")
                alert_type_text = alert_type_names.get(alert_type, "לא ידוע")

                matched = entry.get("matched_cities") or []
                all_cities = entry.get("alert_cities") or []
                matched_str = ", ".join(matched) if matched else "(ללא התאמה)"
                areas_text = ", ".join(matched if matched else all_cities) or "-"

                if all_cities and set(all_cities) != set(matched):
                    all_str = ", ".join(all_cities)
                    formatted = f"{formatted_ts}  ✅ {alert_type_text} - {matched_str} (כל הערים: {all_str})"
                else:
                    formatted = f"{formatted_ts}  ✅ {alert_type_text} - {matched_str}"

                if not entry.get("displayed"):
                    reason = entry.get("decision_reason") or "filtered_out"
                    alert_type_text = f"{alert_type_text} (סונן)"
                    areas_text = matched_str
                    formatted = f"{formatted_ts}  ⏭ סונן [{reason}] - {matched_str}"

            # Apply search filter
            if not self._entry_matches_search(entry, formatted, search_text):
                continue

            rows.append((date_text, time_text, alert_type_text, areas_text, formatted))

        self._log_table.setRowCount(len(rows))
        for row_index, (date_text, time_text, alert_type_text, areas_text, formatted) in enumerate(rows):
            items = [
                QTableWidgetItem(date_text),
                QTableWidgetItem(time_text),
                QTableWidgetItem(alert_type_text),
                QTableWidgetItem(areas_text),
            ]
            for col, item in enumerate(items):
                item.setToolTip(formatted)
                self._log_table.setItem(row_index, col, item)

        self._highlight_search_matches(search_text)

    def _export_log_csv(self) -> None:
        """Export the current log to a CSV file."""
        import csv
        from pathlib import Path

        logger = get_logger()
        if not logger.entries():
            QMessageBox.information(self, "ייצוא לוג", "הלוג ריק - אין מה לייצא.")
            return

        path = QFileDialog.getSaveFileName(
            self, "שמור לוג ל־CSV", os.path.expanduser("~"), "CSV Files (*.csv)"
        )
        if not path or not path[0]:
            return

        try:
            with open(path[0], "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Timestamp",
                    "Status",
                    "Alert Present",
                    "Matched Cities",
                    "POI Matched Cities",
                    "Decision Reason",
                    "Filter Mode",
                    "POI",
                    "Regions",
                    "Cities",
                    "Distance Details",
                ])

                for entry in logger.entries():
                    ts = entry.get("timestamp", "")
                    formatted_ts = format_timestamp(ts)
                    success = "✅" if entry.get("fetch_success") else "❌"
                    alert_present = "כן" if entry.get("alert_present") else "לא"
                    matched = ", ".join(entry.get("matched_cities", []))
                    poi_matched = ", ".join(entry.get("poi_matched_cities", []))
                    reason = entry.get("decision_reason", "")
                    mode = entry.get("filter_mode", "")
                    poi = entry.get("poi_city", "")
                    regions = ", ".join(entry.get("selected_regions", []))
                    cities = ", ".join(entry.get("selected_cities", []))
                    distance_details = json.dumps(entry.get("distance_details", []), ensure_ascii=False)

                    writer.writerow([
                        formatted_ts,
                        success,
                        alert_present,
                        matched,
                        poi_matched,
                        reason,
                        mode,
                        poi,
                        regions,
                        cities,
                        distance_details,
                    ])

            QMessageBox.information(self, "ייצוא לוג", f"ייצוא הצליח:\n{path[0]}")
        except Exception as e:
            QMessageBox.critical(self, "שגיאת ייצוא", f"שגיאה בייצוא:\n{str(e)}")

    def _clear_log(self) -> None:
        """Clear the log file."""
        try:
            log_path = Path(os.getenv("APPDATA")) / "RedAlert" / "alerts_log.jsonl"
            if log_path.exists():
                log_path.unlink()

            # Clear the in-memory logger
            logger = get_logger()
            logger._entries.clear()

            self._log_status.setText("סטטוס: הלוג נוקה")
            self._refresh_log()
            QMessageBox.information(self, "ניקוי לוג", "הלוג נוקה בהצלחה.")
        except Exception as e:
            QMessageBox.critical(self, "שגיאת ניקוי", f"שגיאה בניקוי לוג:\n{str(e)}")

    def _show_last_no_alert_reason(self) -> None:
        """Show an explanation for the most recent alert that was filtered out."""
        entries = list(reversed(get_logger().entries()))
        target = None
        for entry in entries:
            if entry.get("fetch_success") is False:
                continue
            if entry.get("alert_present") and not entry.get("displayed", bool(entry.get("matched_cities"))):
                target = entry
                break

        if not target:
            QMessageBox.information(self, "אין מקרה רלוונטי", "לא נמצאה התראה שסוננה לאחרונה.")
            return

        reason = target.get("decision_reason", "לא ידוע")
        mode = target.get("filter_mode", "")
        alert_cities = ", ".join(target.get("alert_cities", [])) or "(ללא ערים)"
        matched = ", ".join(target.get("matched_cities", [])) or "(ללא התאמה)"
        poi_matched = ", ".join(target.get("poi_matched_cities", [])) or "(ללא התאמת POI)"

        details_lines = []
        for item in target.get("distance_details", [])[:8]:
            city = item.get("city", "")
            dist = item.get("distance_km")
            src = item.get("coords_source", "")
            if dist is None:
                details_lines.append(f"- {city}: ללא קואורדינטות ({src})")
            else:
                details_lines.append(f"- {city}: {dist} ק\"מ ({src})")

        details_text = "\n".join(details_lines) if details_lines else "- אין פרטי מרחק"
        message = (
            f"סיבת החלטה: {reason}\n"
            f"מצב סינון: {mode}\n"
            f"ערים בהתראה: {alert_cities}\n"
            f"ערים שעברו סינון: {matched}\n"
            f"ערים בטווח POI: {poi_matched}\n\n"
            f"פרטי מרחק:\n{details_text}"
        )
        QMessageBox.information(self, "למה לא קיבלתי התראה", message)

    def _build_misc_tab(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)

        self._autostart_checkbox = QCheckBox("אתחול אוטומטי עם פתיחת מערכת")
        layout.addWidget(self._autostart_checkbox)

        # Google Maps toggle
        self._use_google_maps_checkbox = QCheckBox("השתמש ב-Google Maps (דורש API key)")
        self._use_google_maps_checkbox.stateChanged.connect(self._on_google_maps_toggled)
        layout.addWidget(self._use_google_maps_checkbox)

        self._google_maps_api_key = QLineEdit()
        self._google_maps_api_key.setPlaceholderText("Google Maps API key")
        self._google_maps_api_key.setEchoMode(QLineEdit.PasswordEchoOnEdit)
        self._google_maps_api_key.textChanged.connect(lambda _: self._update_map_preview())
        layout.addWidget(QLabel("Google Maps API key:"))
        layout.addWidget(self._google_maps_api_key)

        layout.addWidget(QLabel("(אם מבוטל: מפה סטטית של ישראל בלי עלויות API)"))

        self._test_alert_button = QPushButton("הרץ סימולציית התראה")
        self._test_alert_button.clicked.connect(self._on_test_alert_clicked)
        layout.addWidget(self._test_alert_button)

        self._debug_logging_checkbox = QCheckBox("מצב דיבוג לוג (שמור גם no alert / no_payload)")
        self._debug_logging_checkbox.stateChanged.connect(lambda _: self._refresh_log())
        layout.addWidget(self._debug_logging_checkbox)

        self._log_auto_refresh_checkbox = QCheckBox("רענון אוטומטי ליומן")
        self._log_auto_refresh_checkbox.stateChanged.connect(lambda _: self._update_log_auto_refresh_timer())
        layout.addWidget(self._log_auto_refresh_checkbox)

        auto_refresh_row = QWidget()
        auto_refresh_layout = QHBoxLayout(auto_refresh_row)
        auto_refresh_layout.setContentsMargins(0, 0, 0, 0)
        auto_refresh_layout.addWidget(QLabel("כל"))

        self._log_auto_refresh_value = QSpinBox()
        self._log_auto_refresh_value.setRange(1, 3600)
        self._log_auto_refresh_value.setValue(30)
        self._log_auto_refresh_value.valueChanged.connect(lambda _: self._update_log_auto_refresh_timer())
        auto_refresh_layout.addWidget(self._log_auto_refresh_value)

        self._log_auto_refresh_unit = QComboBox()
        self._log_auto_refresh_unit.addItems(["שניות", "דקות"])
        self._log_auto_refresh_unit.currentTextChanged.connect(lambda _: self._update_log_auto_refresh_timer())
        auto_refresh_layout.addWidget(self._log_auto_refresh_unit)
        auto_refresh_layout.addStretch(1)
        layout.addWidget(auto_refresh_row)

        layout.addStretch(1)
        container.setLayout(layout)
        return container

    def _browse_sound(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "בחר קובץ צליל",
            os.path.expanduser("~"),
            "Audio Files (*.wav *.mp3);;Wave Files (*.wav);;MP3 Files (*.mp3);;All Files (*)",
        )
        if path:
            self._custom_sound_path.setText(path)
            self._sound_mode.setCurrentText(AlertSound.CUSTOM)

    def _on_google_maps_toggled(self) -> None:
        """Enable/disable API key field based on checkbox state."""
        is_checked = self._use_google_maps_checkbox.isChecked()
        self._google_maps_api_key.setEnabled(is_checked)
        self._update_map_preview()

    def _load_config_state(self) -> None:
        self._sound_mode.setCurrentText(self._config.sound_mode)
        self._custom_sound_path.setText(self._config.custom_sound_path)
        self._alert_mode.setCurrentText(self._config.alert_mode)

        # Restore region selection (multi-select)
        selected_regions = self._config.selected_regions or ["כל האזורים"]
        for i in range(self._region_selector.count()):
            item = self._region_selector.item(i)
            item.setSelected(item.text() in selected_regions)

        # Clear search and rebuild city list.
        self._city_search.setText("")
        self._on_region_changed()

        # Restore city selection.
        selected_cities = self._config.selected_cities or []
        for i in range(self._city_selector.count()):
            item = self._city_selector.item(i)
            item.setSelected(item.text() in selected_cities)

        self._poi_city.setCurrentText(self._config.poi_city)
        self._poi_distance.setValue(int(self._config.poi_distance_km or 0))
        self._autostart_checkbox.setChecked(self._config.autostart)
        self._use_google_maps_checkbox.setChecked(self._config.use_google_maps)
        self._google_maps_api_key.setText(self._config.google_maps_api_key)
        self._google_maps_api_key.setEnabled(self._config.use_google_maps)
        self._debug_logging_checkbox.setChecked(self._config.debug_logging)

        interval = int(self._config.log_auto_refresh_interval_seconds or 30)
        if interval % 60 == 0 and interval >= 60:
            self._log_auto_refresh_unit.setCurrentText("דקות")
            self._log_auto_refresh_value.setValue(max(1, interval // 60))
        else:
            self._log_auto_refresh_unit.setCurrentText("שניות")
            self._log_auto_refresh_value.setValue(max(1, interval))
        self._log_auto_refresh_checkbox.setChecked(self._config.log_auto_refresh_enabled)
        self._update_log_auto_refresh_timer()

        # Refresh map preview with saved POI
        self._update_map_preview()

        if self._config.popup_duration_seconds is None:
            self._popup_manual.setChecked(True)
            self._popup_duration.setEnabled(False)
        else:
            self._popup_manual.setChecked(False)
            self._popup_duration.setValue(self._config.popup_duration_seconds)
            self._popup_duration.setEnabled(True)

        self._on_alert_mode_changed()

    def _on_alert_mode_changed(self) -> None:
        mode = self._alert_mode.currentText()
        if mode == AlertMode.ALL:
            self._region_selector.setEnabled(False)
            self._city_search.setEnabled(False)
            self._city_selector.setEnabled(False)
            self._select_all_cities_btn.setEnabled(False)
            self._poi_city.setEnabled(False)
            self._poi_distance.setEnabled(False)
        elif mode == AlertMode.CUSTOM:
            self._region_selector.setEnabled(True)
            self._city_search.setEnabled(True)
            self._city_selector.setEnabled(True)
            self._select_all_cities_btn.setEnabled(True)
            self._poi_city.setEnabled(False)
            self._poi_distance.setEnabled(False)
        elif mode == AlertMode.POI:
            self._region_selector.setEnabled(False)
            self._city_search.setEnabled(False)
            self._city_selector.setEnabled(False)
            self._select_all_cities_btn.setEnabled(False)
            self._poi_city.setEnabled(True)
            self._poi_distance.setEnabled(True)

        # Always refresh the map preview when alert mode changes (e.g., switching to/from POI).
        self._update_map_preview()

    def _on_save_clicked(self) -> None:
        try:
            self._config.sound_mode = self._sound_mode.currentText()
            self._config.custom_sound_path = self._custom_sound_path.text() or ""
            self._config.alert_mode = self._alert_mode.currentText()

            self._config.selected_regions = self._selected_regions() or ["כל האזורים"]
            self._config.selected_cities = self._selected_cities()
            self._config.selected_region = self._config.selected_regions[0]
            self._config.selected_city = self._config.selected_cities[0] if self._config.selected_cities else ""

            self._config.poi_city = self._poi_city.currentText()
            self._config.poi_distance_km = float(self._poi_distance.value())
            self._config.google_maps_api_key = self._google_maps_api_key.text().strip()
            self._config.use_google_maps = self._use_google_maps_checkbox.isChecked()
            self._config.selected_regions = self._selected_regions() or ["כל האזורים"]
            self._config.selected_cities = self._selected_cities()
            self._config.autostart = self._autostart_checkbox.isChecked()
            self._config.debug_logging = self._debug_logging_checkbox.isChecked()
            self._config.log_auto_refresh_enabled = self._log_auto_refresh_checkbox.isChecked()
            self._config.log_auto_refresh_interval_seconds = self._log_refresh_interval_seconds_from_ui()
            self._config.popup_duration_seconds = None if self._popup_manual.isChecked() else self._popup_duration.value()
            self._config.save()
            self._update_log_auto_refresh_timer()

            if self._on_save:
                self._on_save()

            QMessageBox.information(self, "שמירה", "ההגדרות נשמרו בהצלחה.")
        except Exception as exc:
            QMessageBox.critical(self, "שגיאת שמירה", f"שמירת ההגדרות נכשלה:\n{exc}")

    def _on_test_alert_clicked(self) -> None:
        # Apply current UI state first so simulation reflects unsaved settings.
        self._save_current_state_to_config()
        if self._on_test_alert:
            self._on_test_alert()

    def set_alert_cities_for_map(self, cities: List[str]) -> None:
        """Update the map to show which cities currently have alerts."""
        self._alert_cities_for_map = cities
        self._update_map_preview()

    def _update_map_preview(self) -> None:
        """Refresh the map preview based on the selected POI and current alerts."""
        poi_city = self._poi_city.currentText()
        if not poi_city:
            self._map_widget.show_message("בחר עיר כדי להציג מפה")
            return

        # Use Google Maps only if enabled in settings
        use_google_maps = self._use_google_maps_checkbox.isChecked()
        
        api_key = self._google_maps_api_key.text().strip() or self._config.google_maps_api_key.strip()
        poi_coords = resolve_location_coordinates(poi_city, api_key=api_key)
        if not poi_coords:
            self._map_widget.show_message("אין נתוני מיקום לעיר זו")
            return

        poi_radius = float(self._poi_distance.value() or 0)

        # Determine which cities to highlight on the map.
        # Prefer actual alert cities when available, otherwise show all known cities within the POI radius.
        map_points: list[dict[str, object]] = []
        if self._alert_cities_for_map:
            for city, coords in known_locations_with_coordinates(self._alert_cities_for_map, api_key=api_key):
                map_points.append({"name": city, "lat": coords[0], "lng": coords[1], "kind": "alert"})
        else:
            # No active alerts: highlight all known cities that fit within the POI radius.
            for city, coords in city_coordinates.items():
                if city == poi_city:
                    continue
                dist = compute_distance_km(poi_coords[0], poi_coords[1], coords[0], coords[1])
                if dist <= poi_radius:
                    map_points.append({"name": city, "lat": coords[0], "lng": coords[1], "kind": "nearby"})

        if use_google_maps:
            # Google Maps mode
            if not api_key:
                self._map_widget.show_message("הדבק Google Maps API key כדי להציג מפה דינאמית")
                return
            self._map_widget.show_map(
                api_key=api_key,
                center=poi_coords,
                poi_name=poi_city,
                poi_radius_km=poi_radius,
                points=map_points,
            )
        else:
            # Static Israel map mode (no API key needed)
            self._map_widget.show_static_israel_map(
                center=poi_coords,
                poi_name=poi_city,
                poi_radius_km=poi_radius,
                points=map_points,
            )

    def _build_about_tab(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)

        # Title
        title = QLabel("Red Alert - מזען התראות פיקוד העורף")
        title_font = title.font()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # Version info
        version_info = QLabel(f"גרסה: {__version__}\nתאריך: {datetime.now().strftime('%d.%m.%Y')}")
        layout.addWidget(version_info)

        layout.addSpacing(20)

        # System info
        system_info_label = QLabel("מידע על המערכת:")
        system_info_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(system_info_label)

        system_info = QLabel(
            f"מערכת הפעלה: {os.name}\n"
            f"Python גרסה: {sys.version.split()[0]}\n"
            f"PySide6 גרסה: 6.10.2"
        )
        layout.addWidget(system_info)

        layout.addSpacing(20)

        # Description
        description = QLabel(
            "יישום זה מספק התראות בזמן אמת עבור ירי טילים וכלי טיס עוינים "
            "בהתאם לנתוני פיקוד העורף."
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        layout.addSpacing(20)

        # Links section
        links_label = QLabel("קישורים שימושיים:")
        links_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(links_label)

        # Link to Pikud Oref
        pikud_btn = QPushButton("🔗 אתר פיקוד העורף")
        pikud_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://www.oref.org.il"))
        )
        layout.addWidget(pikud_btn)

        # Link to defense guidelines
        defense_btn = QPushButton("🔗 הנחיות התגוננות")
        defense_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://www.oref.org.il/12528-he/Pagries.html"))
        )
        layout.addWidget(defense_btn)

        # GitHub link (if applicable)
        github_btn = QPushButton("🔗 פרויקט GitHub")
        github_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://github.com"))
        )
        layout.addWidget(github_btn)

        layout.addStretch(1)
        container.setLayout(layout)
        return container
