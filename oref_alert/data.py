"""Static data used for location-related logic.

This module can load an official list of settlements from the Israeli Open Data portal
and map them to regions (נפות) so the app can offer a full set of cities and auto-
assign regions when filtering alerts.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

# Cache policy: refresh the cached municipalities data every week.
_CACHE_TTL_DAYS = 7
_CACHE_FILE = "gov_settlements.json"

# Data.gov.il resource for settlements (ישובים).
_GOV_SETTLEMENTS_RESOURCE_ID = "b8112650-a2f8-41f2-9c05-a9b9483fb4c0"
_GOV_DATASTORE_URL = "https://data.gov.il/api/3/action/datastore_search"

# A minimal set of known coordinates for a few major cities.
# This is used for POI distance filtering and aircraft direction heuristics.
city_coordinates: dict[str, tuple[float, float]] = {
    "תל אביב": (32.0853, 34.7818),
    "ירושלים": (31.7683, 35.2137),
    "חיפה": (32.7940, 34.9896),
    "נתניה": (32.3215, 34.8532),
    "באר שבע": (31.2518, 34.7915),
    "אילת": (29.5581, 34.9482),
    "קריית שמונה": (33.2083, 35.5687),
    "ראש העין": (32.0648, 34.9614),
    "ראשון לציון": (31.9691, 34.7991),
    "נהריה": (33.0068, 35.0978),
    "עכו": (32.9240, 35.0844),
    "כרמיאל": (32.9180, 35.2979),
    "חדרה": (32.4446, 34.9118),
    "קריית ביאליק": (32.8246, 35.0812),
    "קריית אתא": (32.8164, 35.0896),
}

# Default fallback region mapping. It will be updated if we can load the full dataset.
city_regions: dict[str, str] = {
    "תל אביב": "מרכז",
    "ירושלים": "מרכז",
    "חיפה": "צפון",
    "נתניה": "מרכז",
    "באר שבע": "דרום",
    "אילת": "דרום",
    "קריית שמונה": "צפון",
    "ראש העין": "מרכז",
    "ראשון לציון": "מרכז",
}

# General regions for UI filtering.
# The API provides 'נפה' values that are more granular (e.g., "חיפה", "בי""ש"),
# so we map these to broad regions like "צפון" / "מרכז" / "דרום".
REGION_GROUPS: list[str] = ["צפון", "מרכז", "דרום", "ירושלים", "אחר"]

# Full list of known cities (may include many more from the government dataset).
# This is dynamically updated when `refresh_city_data()` runs.
all_cities: list[str] = sorted(city_regions.keys())


def _get_cache_dir() -> Path:
    """Return the directory used for caching downloaded data."""

    base = os.getenv("APPDATA") or os.path.expanduser("~")
    p = Path(base) / "RedAlert"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _cache_path() -> Path:
    return _get_cache_dir() / _CACHE_FILE


def _is_cache_stale(path: Path) -> bool:
    try:
        modified = datetime.fromtimestamp(path.stat().st_mtime)
        return datetime.now() - modified > timedelta(days=_CACHE_TTL_DAYS)
    except Exception:
        return True


def _load_cached_settlements() -> Optional[List[Dict[str, Any]]]:
    path = _cache_path()
    if not path.exists() or _is_cache_stale(path):
        return None

    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _save_cached_settlements(data: List[Dict[str, Any]]) -> None:
    try:
        with _cache_path().open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _fetch_settlements_from_gov() -> List[Dict[str, Any]]:
    """Fetch settlement metadata from data.gov.il."""

    settlements: List[Dict[str, Any]] = []
    params = {"resource_id": _GOV_SETTLEMENTS_RESOURCE_ID, "limit": 1000, "offset": 0}

    while True:
        resp = requests.get(_GOV_DATASTORE_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        result = data.get("result") or {}
        records = result.get("records") or []
        settlements.extend(records)

        total = result.get("total") or len(settlements)
        if len(settlements) >= total:
            break

        params["offset"] = params["offset"] + len(records)

    return settlements


def _normalize_region_group(region: str) -> str:
    """Map a raw נפה value into one of the general region groups."""

    region = (region or "").strip()
    if not region:
        return "אחר"

    # First, handle the obvious cases where the raw value already matches.
    if region in REGION_GROUPS:
        return region

    # Common names that should be treated as the broader regions.
    north = {"חיפה", "עכו", "נצרת", "צפת", "עפולה", "כנרת", "נהריה", "קריות", "גליל"}
    center = {"תל אביב", "פתח תקווה", "רחובות", "רמלה", "לוד", "חולון", "חדרה", "השרון", "בני ברק", "ראשון לציון"}
    south = {"באר שבע", "אשקלון", "אשדוד", "דימונה", "קריית גת"}

    if region in north:
        return "צפון"
    if region in center:
        return "מרכז"
    if region in south:
        return "דרום"
    if "ירוש" in region or region == "ירושלים":
        return "ירושלים"

    # Attempt heuristic based on keywords.
    if "צפון" in region:
        return "צפון"
    if "מרכז" in region or "שרון" in region or "תל" in region:
        return "מרכז"
    if "דרום" in region or "באר" in region or "אש" in region:
        return "דרום"

    return "אחר"


def refresh_city_data(force: bool = False) -> None:
    """Refresh the internal city/region mappings using the government dataset.

    This will be used to populate the cities dropdown, and to automatically map
    cities to regions (נפות).
    """

    # Load from cache if available and not forced.
    cached = None if force else _load_cached_settlements()
    settlements = cached
    if settlements is None:
        try:
            settlements = _fetch_settlements_from_gov()
            _save_cached_settlements(settlements)
        except Exception:
            settlements = cached

    if not settlements:
        return

    # Fields in the dataset.
    name_field = "שם_ישוב"
    region_field = "נפה"

    city_regions.clear()
    for item in settlements:
        name = item.get(name_field) or ""
        region = item.get(region_field) or ""
        name = str(name).strip()
        region = str(region).strip()
        if not name:
            continue
        city_regions[name] = _normalize_region_group(region)

    # Update region list.
    global regions
    regions = ["כל האזורים"] + sorted({r for r in city_regions.values() if r})

    # Update full city list.
    global all_cities
    all_cities = sorted(city_regions.keys())


# Refresh the data at import time so the UI can show all cities.
try:
    refresh_city_data(force=False)
except Exception:
    # Best-effort; we don't want the app to crash if the dataset can't be downloaded.
    pass
