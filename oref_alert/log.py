"""Logging for alert API calls.

This module maintains an in-memory rolling log of the last N fetch operations and
persists them to disk so they can be inspected from the UI.
"""

from __future__ import annotations

import json
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


_LOG_FILENAME = "alerts_log.jsonl"
_MAX_ENTRIES = 1000


def _get_log_path() -> Path:
    """Return the path to the log file in the app data directory."""
    # Avoid importing AppConfig to keep this module light.
    from oref_alert.config import _get_app_dir

    return _get_app_dir() / _LOG_FILENAME


class AlertLog:
    """A rolling log of alerts and fetch attempts."""

    def __init__(self) -> None:
        self._path = _get_log_path()
        self._entries: deque[Dict[str, Any]] = deque(maxlen=_MAX_ENTRIES)
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            with self._path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        self._entries.append(obj)
                    except Exception:
                        continue
        except Exception:
            # Best-effort: ignore load errors.
            pass

    def _save(self) -> None:
        try:
            with self._path.open("w", encoding="utf-8") as f:
                for entry in self._entries:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def append(self, entry: Dict[str, Any]) -> None:
        """Add a new entry and persist the log."""
        entry = {**entry}
        # Ensure timestamp
        if "timestamp" not in entry:
            entry["timestamp"] = datetime.now().isoformat()
        self._entries.append(entry)
        self._save()

    def entries(self) -> List[Dict[str, Any]]:
        return list(self._entries)


# Module-level singleton for convenience.
_logger: Optional[AlertLog] = None


def get_logger() -> AlertLog:
    global _logger
    if _logger is None:
        _logger = AlertLog()
    return _logger
