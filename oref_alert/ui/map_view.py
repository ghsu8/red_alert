"""Interactive map widget backed by Google Maps JavaScript API."""

from __future__ import annotations

import json
from typing import Iterable, Optional

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QLabel, QStackedLayout, QWidget

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
except Exception:  # pragma: no cover - depends on local Qt installation
    QWebEngineView = None


class InteractiveMapWidget(QWidget):
    """Embeds an interactive Google map when WebEngine is available."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self._layout = QStackedLayout(self)
        self._message = QLabel("בחר עיר כדי להציג מפה", self)
        self._message.setWordWrap(True)
        self._message.setStyleSheet(
            "background: #222; border: 1px solid #444; color: #f5f5f5; padding: 12px;"
        )
        self._message.setMinimumSize(360, 360)
        self._layout.addWidget(self._message)

        self._view = QWebEngineView(self) if QWebEngineView is not None else None
        if self._view is not None:
            self._view.setMinimumSize(360, 360)
            self._layout.addWidget(self._view)

        self.show_message("בחר עיר כדי להציג מפה")

    def show_message(self, message: str) -> None:
        self._message.setText(message)
        self._layout.setCurrentWidget(self._message)

    def show_map(
        self,
        *,
        api_key: str,
        center: tuple[float, float],
        poi_name: str,
        poi_radius_km: float,
        points: Iterable[dict[str, object]],
    ) -> None:
        if self._view is None:
            self.show_message("Qt WebEngine לא זמין ולכן אי אפשר להציג מפה דינאמית")
            return

        if not api_key:
            self.show_message("חסר Google Maps API key")
            return

        payload = {
            "center": {"lat": center[0], "lng": center[1]},
            "poiName": poi_name,
            "radiusMeters": int(poi_radius_km * 1000),
            "points": list(points),
        }
        html = _build_map_html(api_key=api_key, payload=payload)
        self._view.setHtml(html, QUrl("https://maps.googleapis.com/"))
        self._layout.setCurrentWidget(self._view)

    def show_static_israel_map(
        self,
        *,
        center: tuple[float, float],
        poi_name: str,
        poi_radius_km: float,
        points: Iterable[dict[str, object]],
    ) -> None:
        """Display a static map of Israel with zoom capability, without requiring Google Maps API key."""
        if self._view is None:
            self.show_message("Qt WebEngine לא זמין ולכן אי אפשר להציג מפה")
            return

        payload = {
            "center": {"lat": center[0], "lng": center[1]},
            "poiName": poi_name,
            "radiusMeters": int(poi_radius_km * 1000),
            "points": list(points),
        }
        html = _build_static_israel_map_html(payload=payload)
        self._view.setHtml(html, QUrl("about:blank"))
        self._layout.setCurrentWidget(self._view)


def _build_map_html(*, api_key: str, payload: dict[str, object]) -> str:
    payload_json = json.dumps(payload, ensure_ascii=False)
    api_key_json = json.dumps(api_key)
    return f"""
<!DOCTYPE html>
<html lang="he">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    html, body, #map {{
      height: 100%;
      width: 100%;
      margin: 0;
      padding: 0;
      background: #222;
    }}
  </style>
</head>
<body>
  <div id="map"></div>
  <script>
    const MAP_PAYLOAD = {payload_json};
    const API_KEY = {api_key_json};

    function initMap() {{
      const center = MAP_PAYLOAD.center;
      const map = new google.maps.Map(document.getElementById('map'), {{
        center,
        zoom: 9,
        mapTypeControl: true,
        streetViewControl: false,
        fullscreenControl: false,
        gestureHandling: 'greedy'
      }});

      const poiMarkerElement = document.createElement('div');
      poiMarkerElement.style.width = '32px';
      poiMarkerElement.style.height = '32px';
      poiMarkerElement.style.background = 'url("https://maps.google.com/mapfiles/ms/icons/red-dot.png")';
      poiMarkerElement.style.backgroundSize = '100%';
      poiMarkerElement.style.cursor = 'pointer';

      const poiMarker = new google.maps.marker.AdvancedMarkerElement({{
        map,
        position: center,
        title: MAP_PAYLOAD.poiName,
        content: poiMarkerElement
      }});

      const poiInfo = new google.maps.InfoWindow({{
        content: `<div dir="rtl"><strong>${{MAP_PAYLOAD.poiName}}</strong><br>נקודת ייחוס</div>`
      }});
      poiMarker.addListener('click', () => poiInfo.open({{ anchor: poiMarker, map }}));

      new google.maps.Circle({{
        strokeColor: '#ff3b30',
        strokeOpacity: 0.9,
        strokeWeight: 2,
        fillColor: '#ff3b30',
        fillOpacity: 0.18,
        map,
        center,
        radius: MAP_PAYLOAD.radiusMeters
      }});

      const bounds = new google.maps.LatLngBounds();
      bounds.extend(center);

      for (const point of MAP_PAYLOAD.points) {{
        const position = {{ lat: point.lat, lng: point.lng }};
        
        const markerElement = document.createElement('div');
        markerElement.style.width = '32px';
        markerElement.style.height = '32px';
        markerElement.style.background += point.kind === 'alert'
          ? 'url("https://maps.google.com/mapfiles/ms/icons/blue-dot.png")'
          : 'url("https://maps.google.com/mapfiles/ms/icons/yellow-dot.png")';
        markerElement.style.backgroundSize = '100%';
        markerElement.style.cursor = 'pointer';
        
        const marker = new google.maps.marker.AdvancedMarkerElement({{
          map,
          position,
          title: point.name,
          content: markerElement
        }});
        
        const info = new google.maps.InfoWindow({{
          content: `<div dir="rtl"><strong>${{point.name}}</strong><br>${{point.kind === 'alert' ? 'עיר בהתראה' : 'בתוך טווח POI'}}</div>`
        }});
        marker.addListener('click', () => info.open({{ anchor: marker, map }}));
        bounds.extend(position);
      }}

      if (MAP_PAYLOAD.points.length > 0) {{
        map.fitBounds(bounds, 40);
      }}
    }}

    window.initMap = initMap;
  </script>
  <script src="https://maps.googleapis.com/maps/api/js?key={api_key}&loading=async&callback=initMap"></script>
</body>
</html>
"""


def _build_static_israel_map_html(*, payload: dict[str, object]) -> str:
    """Build a static map of Israel with zoom/pan and markers, without needing API key."""
    payload_json = json.dumps(payload, ensure_ascii=False)
    
    return f"""
<!DOCTYPE html>
<html lang="he">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    html, body {{
      height: 100%;
      width: 100%;
      margin: 0;
      padding: 0;
      background: #222;
      font-family: Arial, sans-serif;
    }}
    #map-container {{
      width: 100%;
      height: 100%;
      position: relative;
      overflow: hidden;
    }}
    svg {{
      display: block;
      width: 100%;
      height: 100%;
    }}
    .map-bounds {{
      fill: #e8f4f8;
      stroke: #333;
      stroke-width: 1;
    }}
    .marker {{
      cursor: pointer;
    }}
    .marker-poi {{
      fill: #ff0000;
    }}
    .marker-alert {{
      fill: #0066ff;
    }}
    .marker-nearby {{
      fill: #ffcc00;
    }}
    .marker-circle {{
      fill: none;
      stroke: #ff3b30;
      stroke-width: 2;
      stroke-opacity: 0.9;
      fill-opacity: 0.18;
    }}
    .info-popup {{
      position: absolute;
      background: white;
      border: 1px solid #999;
      border-radius: 4px;
      padding: 8px 12px;
      font-size: 12px;
      z-index: 1000;
      box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
      pointer-events: none;
      max-width: 200px;
    }}
    .info-popup h4 {{
      margin: 0 0 4px 0;
      font-size: 13px;
    }}
    .info-popup p {{
      margin: 0;
      font-size: 11px;
      color: #666;
    }}
    .zoom-controls {{
      position: absolute;
      top: 10px;
      right: 10px;
      z-index: 100;
      background: white;
      border: 1px solid #999;
      border-radius: 4px;
      overflow: hidden;
    }}
    .zoom-btn {{
      width: 28px;
      height: 28px;
      border: none;
      cursor: pointer;
      font-size: 16px;
      background: white;
      color: #333;
      padding: 0;
      margin: 0;
      border-bottom: 1px solid #999;
    }}
    .zoom-btn:last-child {{
      border-bottom: none;
    }}
    .zoom-btn:hover {{
      background: #f0f0f0;
    }}
  </style>
</head>
<body>
  <div id="map-container">
    <svg id="map-svg" preserveAspectRatio="xMidYMid meet" viewBox="29 29 42 52">
      <!-- Israel approximate boundaries as SVG polygon -->
      <polygon class="map-bounds" points="34.27,31.92 34.50,32.45 35.30,33.92 35.68,34.98 35.42,36.23 35.05,36.52 34.96,37.21 34.56,37.53 34.47,38.48 34.77,39.04 34.34,40.15 34.12,41.04 34.27,42.16 34.57,42.91 34.92,42.77 35.26,43.07 35.58,42.81 35.78,43.64 36.00,44.31 36.22,45.04 36.19,45.91 35.91,46.68 35.62,46.84 35.41,47.29 35.27,48.35 35.31,48.78 35.05,49.39 34.89,50.45 34.81,51.62 34.67,51.95 34.43,51.82 34.21,52.31 33.95,52.73 33.68,52.85 33.48,52.62 33.37,51.86 33.26,51.24 33.07,50.31 32.93,49.50 32.92,48.50 32.69,47.90 32.62,46.98 32.78,46.30 32.91,45.71 32.88,44.60 32.65,43.95 32.40,44.10 32.13,43.62 32.17,42.81 32.06,42.05 31.76,41.86 31.53,41.19 31.65,40.45 31.50,39.71 31.70,39.00 32.26,38.89 32.58,38.30 32.72,37.50 32.61,36.94 32.73,35.92 32.50,35.23 32.63,34.46 32.98,33.99 33.24,33.35 33.60,32.89 33.85,32.10 34.27,31.92"/>
    </svg>
    <div class="zoom-controls">
      <button class="zoom-btn" id="zoom-in">+</button>
      <button class="zoom-btn" id="zoom-out">−</button>
    </div>
  </div>

  <script>
    const MAP_PAYLOAD = {payload_json};
    const svg = document.getElementById('map-svg');
    const container = document.getElementById('map-container');
    let currentZoom = 1;
    let panX = 0;
    let panY = 0;
    let isDragging = false;
    let dragStartX = 0;
    let dragStartY = 0;

    // Israel bounds: latitude 29.5-33.3, longitude 34.2-35.9
    const ISRAEL_BOUNDS = {{
      minLat: 29.5, maxLat: 33.3,
      minLon: 34.2, maxLon: 35.9
    }};

    function latLonToSVG(lat, lon) {{
      const x = 29 + (lon - ISRAEL_BOUNDS.minLon) / (ISRAEL_BOUNDS.maxLon - ISRAEL_BOUNDS.minLon) * 42;
      const y = 29 + (ISRAEL_BOUNDS.maxLat - lat) / (ISRAEL_BOUNDS.maxLat - ISRAEL_BOUNDS.minLat) * 52;
      return {{x, y}};
    }}

    function distances_km_to_svg(lat_center, lon_center, radius_m) {{
      // Rough conversion: 1 degree ≈ 111 km
      const radius_deg = (radius_m / 1000) / 111;
      const svg_center = latLonToSVG(lat_center, lon_center);
      const svg_edge = latLonToSVG(lat_center + radius_deg, lon_center);
      const radius_svg = Math.abs(svg_edge.y - svg_center.y);
      return {{center: svg_center, radius: radius_svg}};
    }}

    function updateSVGTransform() {{
      svg.setAttribute('style', `transform: translate({{panX}}px, {{panY}}px) scale({{currentZoom}}); transform-origin: 0 0; transition: none;`);
    }}

    function addMarkers() {{
      const centerLat = MAP_PAYLOAD.center.lat;
      const centerLon = MAP_PAYLOAD.center.lng;
      const radiusM = MAP_PAYLOAD.radiusMeters;

      // Draw radius circle
      const circleData = distances_km_to_svg(centerLat, centerLon, radiusM);
      const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      circle.setAttribute('cx', circleData.center.x);
      circle.setAttribute('cy', circleData.center.y);
      circle.setAttribute('r', circleData.radius);
      circle.setAttribute('class', 'marker-circle');
      svg.appendChild(circle);

      // Draw POI marker
      const poiPos = latLonToSVG(centerLat, centerLon);
      const poiMarker = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      poiMarker.setAttribute('cx', poiPos.x);
      poiMarker.setAttribute('cy', poiPos.y);
      poiMarker.setAttribute('r', '0.3');
      poiMarker.setAttribute('class', 'marker marker-poi');
      poiMarker.style.cursor = 'pointer';
      svg.appendChild(poiMarker);

      poiMarker.addEventListener('click', (e) => {{
        e.stopPropagation();
        showPopup(`<h4>${{MAP_PAYLOAD.poiName}}</h4><p>נקודת ייחוס</p>`, e.pageX, e.pageY);
      }});

      // Draw point markers
      for (const point of MAP_PAYLOAD.points) {{
        const pos = latLonToSVG(point.lat, point.lng);
        const marker = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        marker.setAttribute('cx', pos.x);
        marker.setAttribute('cy', pos.y);
        marker.setAttribute('r', '0.25');
        marker.setAttribute('class', `marker marker-${{point.kind}}`);
        marker.style.cursor = 'pointer';
        svg.appendChild(marker);

        marker.addEventListener('click', (e) => {{
          e.stopPropagation();
          const kind_label = point.kind === 'alert' ? 'עיר בהתראה' : 'בתוך טווח POI';
          showPopup(`<h4>${{point.name}}</h4><p>${{kind_label}}</p>`, e.pageX, e.pageY);
        }});
      }}
    }}

    function showPopup(html, x, y) {{
      const existing = document.querySelector('.info-popup');
      if (existing) existing.remove();
      
      const popup = document.createElement('div');
      popup.className = 'info-popup';
      popup.innerHTML = html;
      popup.style.left = (x + 10) + 'px';
      popup.style.top = (y + 10) + 'px';
      container.appendChild(popup);

      setTimeout(() => popup.remove(), 3000);
    }}

    // Zoom controls
    document.getElementById('zoom-in').addEventListener('click', () => {{
      currentZoom = Math.min(currentZoom * 1.3, 5);
      updateSVGTransform();
    }});

    document.getElementById('zoom-out').addEventListener('click', () => {{
      currentZoom = Math.max(currentZoom / 1.3, 1);
      updateSVGTransform();
    }});

    // Pan
    svg.addEventListener('mousedown', (e) => {{
      isDragging = true;
      dragStartX = e.clientX - panX;
      dragStartY = e.clientY - panY;
    }});

    document.addEventListener('mousemove', (e) => {{
      if (isDragging) {{
        panX = e.clientX - dragStartX;
        panY = e.clientY - dragStartY;
        updateSVGTransform();
      }}
    }});

    document.addEventListener('mouseup', () => {{
      isDragging = false;
    }});

    // Wheel zoom
    svg.addEventListener('wheel', (e) => {{
      e.preventDefault();
      currentZoom *= e.deltaY > 0 ? 0.85 : 1.15;
      currentZoom = Math.max(1, Math.min(5, currentZoom));
      updateSVGTransform();
    }});

    // Initialize
    addMarkers();
    updateSVGTransform();
  </script>
</body>
</html>
"""