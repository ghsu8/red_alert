"""Polling service that fetches alerts and emits notifications."""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import requests
from PySide6.QtCore import QObject, Signal

from oref_alert.config import AppConfig
from difflib import get_close_matches

from oref_alert.data import city_coordinates, city_regions
from oref_alert.models import AlertEvent, AlertSummary, AlertType, PointOfInterest
from oref_alert.utils import compute_distance_km, bearing_between


class FetchStatus(Enum):
    OK = "ok"
    ERROR = "error"


from oref_alert.log import AlertLog


class AlertFetcher(QObject):
    """Background worker that polls the OREF alerts API."""

    new_alert = Signal(AlertSummary)
    fetch_error = Signal(str)

    def __init__(self, config: AppConfig, interval_seconds: float = 5.0, logger: Optional[AlertLog] = None):
        super().__init__()
        self._config = config
        self._interval = interval_seconds
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._api_url = "https://www.oref.org.il/warningMessages/alert/alerts.json"
        self._logger = logger

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def _run(self) -> None:
        last_seen: Optional[str] = self._config.last_seen_alert_id
        while not self._stop_event.is_set():
            try:
                status, alert, matched_cities = self._fetch_once(last_seen)

                # Log the attempt.
                if self._logger is not None:
                    self._logger.append(
                        {
                            "timestamp": datetime.now().isoformat(),
                            "fetch_success": status == FetchStatus.OK,
                            "error": None if status == FetchStatus.OK else "fetch_error",
                            "alert_present": bool(alert),
                            "alert_type": alert.type.value if alert else None,
                            "filter_mode": self._config.alert_mode,
                            "selected_regions": self._config.selected_regions,
                            "selected_cities": self._config.selected_cities,
                            "poi_city": self._config.poi_city,
                            "poi_distance_km": self._config.poi_distance_km,
                            "alert_cities": alert.cities if alert else [],
                            "matched_cities": matched_cities,
                        }
                    )

                if status == FetchStatus.OK and alert and matched_cities:
                    last_seen = alert.id
                    self._config.last_seen_alert_id = last_seen
                    self._config.save()
                    self.new_alert.emit(alert)
            except Exception as exc:
                self.fetch_error.emit(str(exc))
                if self._logger is not None:
                    self._logger.append(
                        {
                            "timestamp": datetime.now().isoformat(),
                            "fetch_success": False,
                            "error": str(exc),
                            "alert_present": False,
                            "alert_type": None,
                            "filter_mode": self._config.alert_mode,
                            "selected_regions": self._config.selected_regions,
                            "selected_cities": self._config.selected_cities,
                            "poi_city": self._config.poi_city,
                            "poi_distance_km": self._config.poi_distance_km,
                        }
                    )

            self._stop_event.wait(self._interval)

    def _fetch_once(self, last_seen_id: Optional[str]) -> Tuple[FetchStatus, Optional[AlertSummary], List[str]]:
        headers = {
            "User-Agent": "RedAlertDesktop/1.0",
            "Referer": "https://www.oref.org.il/",
        }
        # Simple retry logic
        for attempt in range(3):
            try:
                resp = requests.get(self._api_url, headers=headers, timeout=10)
                resp.raise_for_status()
                payload = resp.content.decode("utf-8-sig").strip()
                print(f"[DEBUG] Fetched payload length: {len(payload)}")
                if not payload:
                    print(f"[DEBUG] Empty payload, returning no alert")
                    return FetchStatus.OK, None, []

                try:
                    data = json.loads(payload)
                except json.JSONDecodeError:
                    print(f"[DEBUG] Invalid JSON payload, returning no alert")
                    return FetchStatus.OK, None, []

                print(f"[DEBUG] Parsed JSON, data keys: {data.keys()}")
                alert = self._parse_payload(data)
                print(f"[DEBUG] Parsed alert: {alert.title if alert else 'None'}, cities: {alert.cities if alert else []}")
                if not alert:
                    print(f"[DEBUG] Parse returned no alert")
                    return FetchStatus.OK, None, []

                if last_seen_id and alert.id == last_seen_id:
                    print(f"[DEBUG] Alert ID already seen, skipping")
                    return FetchStatus.OK, None, []

                matched = self._matched_cities(alert.cities)
                poi_matched = self._cities_within_poi_distance(alert.cities)
                print(f"[DEBUG] Matched cities: {matched} (filter mode={self._config.alert_mode})")
                print(f"[DEBUG] POI matched cities ({self._config.poi_city} @ {self._config.poi_distance_km}km): {poi_matched}")

                # If the user is using any mode but has POI enabled, also notify when an alert appears within the POI radius.
                notify_due_to_poi = bool(poi_matched)

                # If we have a POI alert but no matched cities (e.g. custom mode without those cities selected),
                # create a special summary to tell the user there are nearby alerts.
                if notify_due_to_poi and not matched:
                    alert = AlertSummary(
                        id=alert.id,
                        type=alert.type,
                        title=f"התראות סמוכות ל-{self._config.poi_city}",
                        cities=poi_matched,
                        details=f"קיימות התראות ביישובים בטווח {self._config.poi_distance_km} ק\"מ מהיישוב שלך.",
                        color="#EA580C",
                    )

                if not matched and not notify_due_to_poi:
                    return FetchStatus.OK, None, []

                return FetchStatus.OK, alert, matched or poi_matched
            except Exception as exc:
                print(f"[DEBUG] Exception on attempt {attempt}: {exc}")
                if attempt == 2:
                    raise
                time.sleep(1)
        return FetchStatus.ERROR, None, []

    def _parse_payload(self, payload: Dict[str, Any]) -> Optional[AlertSummary]:
        """Map the raw OREF payload to our AlertSummary model."""
        items = payload.get("data") or []
        print(f"[DEBUG] Data items: {items}")
        if not items:
            return None

        # The alert info is in the top level, data is list of city names
        alert_id = payload.get("id", "")
        cat = payload.get("cat", "")
        title = payload.get("title", "")

        # Determine alert type from cat or title
        if "מקדימה" in title or "early" in title.lower():
            alert_type = AlertType.EARLY_WARNING
        elif "טילים" in title or "ירי" in title:
            alert_type = AlertType.MISSILE
        elif "כלי טיס" in title or "מטוס" in title:
            alert_type = AlertType.AIRCRAFT
        else:
            alert_type = AlertType.ALL

        cities = items if isinstance(items, list) else []
        cities = [c for c in cities if isinstance(c, str)]

        kind_label = {
            AlertType.MISSILE: "ירי טילים",
            AlertType.AIRCRAFT: "כלי טיס עוין",
            AlertType.EARLY_WARNING: "התראה מקדימה",
        }.get(alert_type, "אירוע הסתיים")

        color = {
            AlertType.MISSILE: "#EF4444",
            AlertType.AIRCRAFT: "#F59E0B",
            AlertType.EARLY_WARNING: "#EAB308",
        }.get(alert_type, "#10B981")

        return AlertSummary(
            id=alert_id,
            type=alert_type,
            title=f"{kind_label} - {title}",
            cities=cities,
            details=None,  # For now
            color=color,
        )

    def _matched_cities(self, cities: List[str]) -> List[str]:
        """Return the subset of cities that pass the current filter settings."""
        if self._config.alert_mode == "all":
            return cities
        elif self._config.alert_mode == "custom":
            selected_regions = [r for r in (self._config.selected_regions or []) if r and r != "כל האזורים"]
            selected_cities = [c for c in (self._config.selected_cities or []) if c]

            if not selected_regions and not selected_cities:
                return []

            matched: List[str] = []
            for city in cities:
                if city in selected_cities:
                    matched.append(city)
                elif city_regions.get(city) in selected_regions:
                    matched.append(city)
            return matched
        elif self._config.alert_mode == "poi":
            return [c for c in cities if self._is_within_poi_distance([c])]
        return []

    def _cities_within_poi_distance(self, cities: List[str]) -> List[str]:
        """Return cities that are within the POI radius."""
        poi_city = self._config.poi_city
        if not poi_city:
            return []

        poi_coords = city_coordinates.get(poi_city)
        if not poi_coords:
            # Fallback: match by name only
            return [c for c in cities if c == poi_city]

        poi_lat, poi_lon = poi_coords
        poi_radius = float(self._config.poi_distance_km or 0)
        if poi_radius <= 0:
            return []

        within = []
        for city in cities:
            coords = city_coordinates.get(city)
            if not coords:
                # Try a close match to our known coordinate list
                matches = get_close_matches(city, city_coordinates.keys(), n=1, cutoff=0.75)
                if matches:
                    coords = city_coordinates.get(matches[0])

            if not coords:
                # If still unknown, log for debugging and skip
                print(f"[DEBUG] No coordinates for city '{city}' (cannot compute POI distance)")
                continue

            dist = compute_distance_km(poi_lat, poi_lon, coords[0], coords[1])
            if dist <= poi_radius:
                within.append(city)
        return within

    def _should_display_alert(self, cities: List[str]) -> bool:
        """Determine whether this alert should be shown based on the configuration."""
        if self._config.alert_mode == "all":
            # Optionally apply POI distance filtering
            if self._config.poi_city:
                return self._is_within_poi_distance(cities)
            return True

        # When in a filtering mode, use the configured selections.
        # If no selections are made, treat as "all".
        selected_regions = [r for r in (self._config.selected_regions or []) if r and r != "כל האזורים"]
        selected_cities = [c for c in (self._config.selected_cities or []) if c]

        if not selected_regions and not selected_cities:
            return True

        for city in cities:
            if city in selected_cities:
                return self._is_within_poi_distance(cities)
            if city_regions.get(city) in selected_regions:
                return self._is_within_poi_distance(cities)

        return False

    def _is_within_poi_distance(self, cities: List[str]) -> bool:
        """Check whether any of the alert cities is within the POI radius.

        If we don't have coordinates for the chosen POI city, fall back to simple
        name-matching so the user can still filter by a city even without geo data.
        """
        poi_city = self._config.poi_city
        poi_radius = float(self._config.poi_distance_km or 0)
        if not poi_city or poi_radius <= 0:
            return True

        poi_coords = city_coordinates.get(poi_city)
        if not poi_coords:
            # Fallback: if the alert explicitly mentions the POI city, treat it as in range.
            return poi_city in cities

        poi_lat, poi_lon = poi_coords
        for city in cities:
            coords = city_coordinates.get(city)
            if not coords:
                continue
            dist = compute_distance_km(poi_lat, poi_lon, coords[0], coords[1])
            if dist <= poi_radius:
                return True
        return False

    def _to_event(self, raw: Dict[str, Any]) -> Optional[AlertEvent]:
        """Convert raw API object to AlertEvent."""
        try:
            alert_type = raw.get("type", "")
            if alert_type not in (AlertType.MISSILE.value, AlertType.AIRCRAFT.value):
                alert_type = AlertType.ALL.value

            return AlertEvent(
                id=str(raw.get("id", "")),
                type=AlertType(alert_type),
                headline=raw.get("headline", "האזעקה החלה"),
                timestamp=raw.get("date", ""),
                cities=[raw.get("cityName", "")],
                raw=raw,
            )
        except Exception:
            return None

    def _compute_aircraft_direction(self, items: List[Dict[str, Any]]) -> Optional[str]:
        """Compute a rough direction for aircraft alerts based on the POI and the cities in the alert."""
        poi_city = self._config.poi_city
        if not poi_city:
            return None

        poi_coords = self._configured_poi_coords()
        if not poi_coords:
            return None

        # Simple heuristic: use the first two distinct cities in payload
        unique_cities = []
        for item in items:
            city = item.get("cityName")
            if city and city not in unique_cities:
                unique_cities.append(city)
            if len(unique_cities) >= 2:
                break

        if len(unique_cities) < 2:
            return None

        from_city, to_city = unique_cities[:2]
        from_coords = city_coordinates.get(from_city)
        to_coords = city_coordinates.get(to_city)
        if not from_coords or not to_coords:
            return None

        # Compute bearing of the movement between the two cities
        bearing_deg = bearing_between(from_coords[0], from_coords[1], to_coords[0], to_coords[1])

        # Compute whether movement is toward or away from the point of interest
        poi_lat, poi_lon = poi_coords.latitude, poi_coords.longitude
        dist_from = compute_distance_km(poi_lat, poi_lon, from_coords[0], from_coords[1])
        dist_to = compute_distance_km(poi_lat, poi_lon, to_coords[0], to_coords[1])
        trend = "מתקרב" if dist_to < dist_from else "מתרחק"

        return f"כיוון משוער: {bearing_deg:.0f}° ({from_city} → {to_city}), {trend} לעבר {poi_city}"

    def _configured_poi_coords(self) -> Optional[PointOfInterest]:
        poi = self._config.poi_city
        if not poi:
            return None

        coords = city_coordinates.get(poi)
        if not coords:
            return None

        return PointOfInterest(city=poi, latitude=coords[0], longitude=coords[1])
