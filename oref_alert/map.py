"""Map helper utilities for displaying POI and alert locations."""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

import requests
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap, QPainter, QColor

from oref_alert.data import city_coordinates


def _degrees_to_radians(deg: float) -> float:
    return deg * math.pi / 180.0


def _km_per_pixel(lat: float, zoom: int) -> float:
    """Approximate how many kilometers one pixel represents at a given latitude/zoom."""
    # Earth circumference at equator (km)
    equator_km = 40075.017
    # Pixels for full world at given zoom
    pixels = 256 * (2**zoom)
    # kilometers per pixel at equator
    km_per_pixel_equator = equator_km / pixels
    # adjust for latitude
    return km_per_pixel_equator * math.cos(_degrees_to_radians(lat))


def _km_to_pixels(lat: float, zoom: int, km: float) -> float:
    return km / _km_per_pixel(lat, zoom)


def _app_cache_dir() -> Path:
    base = os.getenv("APPDATA") or os.path.expanduser("~")
    path = Path(base) / "RedAlert"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _geocode_cache_file() -> Path:
    return _app_cache_dir() / "geocode_cache.json"


def _load_geocode_cache() -> dict[str, list[float]]:
    path = _geocode_cache_file()
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_geocode_cache(cache: dict[str, list[float]]) -> None:
    try:
        with _geocode_cache_file().open("w", encoding="utf-8") as handle:
            json.dump(cache, handle, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _location_candidates(name: str) -> list[str]:
    cleaned = (name or "").strip()
    if not cleaned:
        return []

    candidates = [cleaned]
    for separator in (" - ", ","):
        if separator in cleaned:
            base = cleaned.split(separator)[0].strip()
            if base and base not in candidates:
                candidates.append(base)

    if cleaned.startswith("אזור תעשייה "):
        base = cleaned.replace("אזור תעשייה ", "", 1).strip()
        if base and base not in candidates:
            candidates.append(base)

    return candidates


def resolve_location_coordinates(name: str, api_key: str = "") -> Optional[Tuple[float, float]]:
    """Resolve a city/location to coordinates using static data, cache, and Google geocoding."""

    candidates = _location_candidates(name)
    if not candidates:
        return None

    for candidate in candidates:
        if candidate in city_coordinates:
            return city_coordinates[candidate]

    cache = _load_geocode_cache()
    for candidate in candidates:
        cached = cache.get(candidate)
        if isinstance(cached, list) and len(cached) == 2:
            return float(cached[0]), float(cached[1])

    if not api_key:
        return None

    for candidate in candidates:
        coords = _geocode_with_google(candidate, api_key)
        if coords is not None:
            cache[candidate] = [coords[0], coords[1]]
            _save_geocode_cache(cache)
            return coords

    return None


def _geocode_with_google(name: str, api_key: str) -> Optional[Tuple[float, float]]:
    params = {
        "address": name,
        "components": "country:IL",
        "language": "he",
        "key": api_key,
    }

    try:
        resp = requests.get("https://maps.googleapis.com/maps/api/geocode/json", params=params, timeout=10)
        resp.raise_for_status()
        payload = resp.json()
    except Exception:
        return None

    results = payload.get("results") or []
    if not results:
        return None

    location = ((results[0].get("geometry") or {}).get("location") or {})
    lat = location.get("lat")
    lng = location.get("lng")
    if lat is None or lng is None:
        return None
    return float(lat), float(lng)


def known_locations_with_coordinates(names: Iterable[str], api_key: str = "") -> list[tuple[str, tuple[float, float]]]:
    """Resolve a list of names into only the locations that have coordinates available."""

    resolved: list[tuple[str, tuple[float, float]]] = []
    for name in names:
        coords = resolve_location_coordinates(name, api_key=api_key)
        if coords is not None:
            resolved.append((name, coords))
    return resolved


def _latlon_to_tile(lat: float, lon: float, zoom: int) -> Tuple[float, float]:
    """Convert lat/lon to OSM tile coordinates (can be fractional)."""

    lat_rad = math.radians(lat)
    n = 2 ** zoom
    x = (lon + 180.0) / 360.0 * n
    y = (1.0 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2.0 * n
    return x, y


def _fetch_tile(zoom: int, x: int, y: int, session: Optional[requests.Session] = None) -> Optional[QImage]:
    """Fetch a single map tile from OpenStreetMap tile server."""

    url = f"https://a.tile.openstreetmap.org/{zoom}/{x}/{y}.png"
    headers = {
        # Use a clear User-Agent to satisfy tile usage policies.
        "User-Agent": "RedAlertDesktop/1.0 (https://github.com)",
        "Referer": "https://www.openstreetmap.org/",
    }

    try:
        sess = session or requests
        resp = sess.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        img = QImage.fromData(resp.content)
        if img.isNull():
            return None
        return img
    except Exception:
        return None


def _get_google_static_map(
    center: Tuple[float, float],
    zoom: int,
    size: Tuple[int, int],
    poi: Optional[Tuple[float, float]] = None,
    alert_points: Optional[List[Tuple[float, float]]] = None,
    api_key: Optional[str] = None,
) -> Optional[QPixmap]:
    """Fetch a static map from Google Maps Static API (requires API key)."""

    if not api_key:
        return None

    width, height = size
    base_url = "https://maps.googleapis.com/maps/api/staticmap"
    params = {
        "center": f"{center[0]},{center[1]}",
        "zoom": str(zoom),
        "size": f"{width}x{height}",
        "scale": "2",
        "key": api_key,
    }

    markers = []
    if poi:
        markers.append(f"color:red|label:P|{poi[0]},{poi[1]}")
    if alert_points:
        for lat, lon in alert_points:
            markers.append(f"color:blue|label:A|{lat},{lon}")

    if markers:
        params["markers"] = markers

    try:
        resp = requests.get(base_url, params=params, timeout=10)
        resp.raise_for_status()
        img = QImage.fromData(resp.content)
        if img.isNull():
            return None
        return QPixmap.fromImage(img)
    except Exception:
        return None


def get_static_map_pixmap(
    center: Tuple[float, float],
    zoom: int,
    size: Tuple[int, int],
    poi: Optional[Tuple[float, float]] = None,
    poi_radius_km: Optional[float] = None,
    alert_points: Optional[List[Tuple[float, float]]] = None,
) -> QPixmap:
    """Render a map centered at `center` with optional markers.

    By default this uses OpenStreetMap tile server (a.tile.openstreetmap.org).
    If tile fetching fails, falls back to a simple placeholder grid map.

    You can optionally force Google Maps by setting the environment variable
    `REDALERT_MAP_PROVIDER=google` and providing `REDALERT_GOOGLE_MAPS_API_KEY`.
    """

    width, height = size

    # Prefer Google Maps when explicitly configured (requires API key).
    provider = os.getenv("REDALERT_MAP_PROVIDER", "osm").strip().lower()
    if provider == "google":
        api_key = os.getenv("REDALERT_GOOGLE_MAPS_API_KEY")
        google_pix = _get_google_static_map(
            center=center,
            zoom=zoom,
            size=size,
            poi=poi,
            alert_points=alert_points,
            api_key=api_key,
        )
        if google_pix is not None:
            pixmap = google_pix
        else:
            pixmap = _create_offline_map(size=size, poi=poi, poi_radius_km=poi_radius_km, alert_points=alert_points)
        # Still draw radius overlay as needed.
        if poi and poi_radius_km and poi_radius_km > 0:
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            pen_color = QColor(255, 0, 0, 200)
            brush_color = QColor(255, 0, 0, 60)
            painter.setPen(pen_color)
            painter.setBrush(brush_color)

            pixel_radius = _km_to_pixels(poi[0], zoom, poi_radius_km)
            center_x_pix = width / 2
            center_y_pix = height / 2
            painter.drawEllipse(
                int(center_x_pix - pixel_radius),
                int(center_y_pix - pixel_radius),
                int(pixel_radius * 2),
                int(pixel_radius * 2),
            )
            painter.end()

        return pixmap

    # Otherwise fall back to OpenStreetMap tile-based rendering.
    try:
        # Determine center in tile coordinates
        center_x, center_y = _latlon_to_tile(center[0], center[1], zoom)

        # How many tiles are needed to cover the view (add a margin)
        tiles_x = math.ceil(width / 256) + 2
        tiles_y = math.ceil(height / 256) + 2

        # Determine the top-left tile indexes
        tile_x0 = int(math.floor(center_x - tiles_x / 2))
        tile_y0 = int(math.floor(center_y - tiles_y / 2))

        # Create a buffer big enough for the full tile grid
        buffer_img = QImage(tiles_x * 256, tiles_y * 256, QImage.Format_RGB32)
        buffer_img.fill(QColor(240, 240, 240))

        session = requests.Session()
        for dy in range(tiles_y):
            for dx in range(tiles_x):
                tx = tile_x0 + dx
                ty = tile_y0 + dy
                if tx < 0 or ty < 0 or tx >= 2**zoom or ty >= 2**zoom:
                    continue
                tile_img = _fetch_tile(zoom, tx, ty, session=session)
                if tile_img is None:
                    continue
                painter = QPainter(buffer_img)
                painter.drawImage(dx * 256, dy * 256, tile_img)
                painter.end()

        # Crop to the requested viewport centered on the desired lat/lon.
        offset_x = int((center_x - tile_x0) * 256 - width / 2)
        offset_y = int((center_y - tile_y0) * 256 - height / 2)
        rect = buffer_img.copy(offset_x, offset_y, width, height)
        pixmap = QPixmap.fromImage(rect)

    except Exception:
        pixmap = _create_offline_map(size=size, poi=poi, poi_radius_km=poi_radius_km, alert_points=alert_points)

    # Draw POI radius overlay if requested
    if poi and poi_radius_km and poi_radius_km > 0:
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        pen_color = QColor(255, 0, 0, 200)
        brush_color = QColor(255, 0, 0, 60)
        painter.setPen(pen_color)
        painter.setBrush(brush_color)

        pixel_radius = _km_to_pixels(poi[0], zoom, poi_radius_km)
        center_x_pix = width / 2
        center_y_pix = height / 2
        painter.drawEllipse(
            int(center_x_pix - pixel_radius),
            int(center_y_pix - pixel_radius),
            int(pixel_radius * 2),
            int(pixel_radius * 2),
        )
        painter.end()

    return pixmap


def _create_offline_map(
    size: Tuple[int, int],
    poi: Optional[Tuple[float, float]] = None,
    poi_radius_km: Optional[float] = None,
    alert_points: Optional[List[Tuple[float, float]]] = None,
) -> QPixmap:
    """Create a simple placeholder map when the static map service is unreachable."""

    width, height = size
    pixmap = QPixmap(width, height)
    pixmap.fill(QColor(30, 30, 30))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    # Draw a simple grid
    grid_color = QColor(80, 80, 80)
    painter.setPen(grid_color)
    step_x = max(20, width // 12)
    step_y = max(20, height // 12)
    for x in range(0, width, step_x):
        painter.drawLine(x, 0, x, height)
    for y in range(0, height, step_y):
        painter.drawLine(0, y, width, y)

    # Center text
    painter.setPen(QColor(200, 200, 200))
    painter.drawText(pixmap.rect(), Qt.AlignCenter, "מפה לא זמינה\n(אין רשת)")

    # Draw POI and alert points as a rough relative map based on their relative deltas.
    if poi and alert_points:
        # Determine bounding box
        all_points = [poi] + alert_points
        lats = [p[0] for p in all_points]
        lons = [p[1] for p in all_points]
        min_lat, max_lat = min(lats), max(lats)
        min_lon, max_lon = min(lons), max(lons)

        # Add tiny padding so points don't overlap edges
        lat_pad = (max_lat - min_lat) * 0.1 or 0.01
        lon_pad = (max_lon - min_lon) * 0.1 or 0.01
        min_lat -= lat_pad
        max_lat += lat_pad
        min_lon -= lon_pad
        max_lon += lon_pad

        def project(lat: float, lon: float) -> Tuple[int, int]:
            x = int((lon - min_lon) / (max_lon - min_lon) * (width - 20) + 10)
            y = int((max_lat - lat) / (max_lat - min_lat) * (height - 20) + 10)
            return x, y

        # Draw POI
        poi_x, poi_y = project(*poi)
        painter.setBrush(QColor(255, 0, 0))
        painter.setPen(QColor(255, 255, 255))
        painter.drawEllipse(poi_x - 6, poi_y - 6, 12, 12)

        # Draw alerts
        painter.setBrush(QColor(0, 150, 255))
        painter.setPen(QColor(230, 230, 255))
        for pt in alert_points:
            ax, ay = project(*pt)
            painter.drawEllipse(ax - 5, ay - 5, 10, 10)

    painter.end()
    return pixmap
