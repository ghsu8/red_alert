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
        mapId: 'DEMO_MAP_ID',
        mapTypeControl: true,
        streetViewControl: false,
        fullscreenControl: false,
        gestureHandling: 'greedy'
      }});

      const poiEl = document.createElement('div');
      poiEl.style.width = '18px';
      poiEl.style.height = '18px';
      poiEl.style.background = '#ff0000';
      poiEl.style.border = '2px solid #ffffff';
      poiEl.style.borderRadius = '50%';
      poiEl.style.boxShadow = '0 0 5px rgba(0,0,0,0.5)';

      const poiMarker = new google.maps.marker.AdvancedMarkerElement({{
        map,
        position: center,
        title: MAP_PAYLOAD.poiName,
        content: poiEl,
        gmpClickable: true
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
        const markerEl = document.createElement('div');
        markerEl.style.width = '14px';
        markerEl.style.height = '14px';
        markerEl.style.borderRadius = '50%';
        markerEl.style.background = point.kind === 'alert' ? '#0066ff' : '#ffcc00';
        markerEl.style.border = '2px solid #ffffff';
        markerEl.style.boxShadow = '0 0 3px rgba(0,0,0,0.4)';

        const marker = new google.maps.marker.AdvancedMarkerElement({{
          map,
          position,
          title: point.name,
          content: markerEl,
          gmpClickable: true
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
  <script src="https://maps.googleapis.com/maps/api/js?key={api_key}&loading=async&callback=initMap&v=weekly&libraries=marker"></script>
</body>
</html>
"""


def _build_static_israel_map_html(*, payload: dict[str, object]) -> str:
    """Real interactive map via Leaflet.js + CARTO tiles – no API key required."""
    payload_json = json.dumps(payload, ensure_ascii=False)

    return f"""
<!DOCTYPE html>
<html lang="he">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
        integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin=""/>
  <style>
    html, body, #map {{
      height: 100%; width: 100%; margin: 0; padding: 0;
    }}
  </style>
</head>
<body>
  <div id="map"></div>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
          integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV/XN/WLEo=" crossorigin=""></script>
  <script>
    const MAP_PAYLOAD = {payload_json};
    const center = MAP_PAYLOAD.center;

    const map = L.map('map', {{ zoomControl: true }}).setView([center.lat, center.lng], 9);

    L.tileLayer('https://{{s}}.basemaps.cartocdn.com/rastertiles/voyager/{{z}}/{{x}}/{{y}}{{r}}.png', {{
      attribution: '\u00a9 <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> \u00a9 <a href="https://carto.com/attributions">CARTO</a>',
      subdomains: 'abcd',
      maxZoom: 19
    }}).addTo(map);

    // POI red circle marker
    const poiIcon = L.divIcon({{
      html: '<div style="width:18px;height:18px;background:#ff0000;border-radius:50%;border:2.5px solid #fff;box-shadow:0 0 5px rgba(0,0,0,0.5)"></div>',
      className: '',
      iconSize: [18, 18],
      iconAnchor: [9, 9]
    }});
    L.marker([center.lat, center.lng], {{icon: poiIcon}})
      .bindPopup('<div dir="rtl"><b>' + MAP_PAYLOAD.poiName + '</b><br>\u05e0\u05e7\u05d5\u05d3\u05ea \u05d9\u05d9\u05d7\u05d5\u05e1</div>')
      .addTo(map);

    // Radius circle
    L.circle([center.lat, center.lng], {{
      radius: MAP_PAYLOAD.radiusMeters,
      color: '#ff3b30',
      fillColor: '#ff3b30',
      fillOpacity: 0.12,
      weight: 2
    }}).addTo(map);

    // Points
    for (const point of MAP_PAYLOAD.points) {{
      const color = point.kind === 'alert' ? '#0066ff' : '#ffcc00';
      const border = point.kind === 'alert' ? '#ffffff' : '#333333';
      const icon = L.divIcon({{
        html: '<div style="width:14px;height:14px;background:' + color + ';border-radius:50%;border:2px solid ' + border + ';box-shadow:0 0 3px rgba(0,0,0,0.4)"></div>',
        className: '',
        iconSize: [14, 14],
        iconAnchor: [7, 7]
      }});
      const label = point.kind === 'alert' ? '\u05e2\u05d9\u05e8 \u05d1\u05d4\u05ea\u05e8\u05d0\u05d4' : '\u05d1\u05ea\u05d5\u05da \u05d8\u05d5\u05d5\u05d7 POI';
      L.marker([point.lat, point.lng], {{icon}})
        .bindPopup('<div dir="rtl"><b>' + point.name + '</b><br>' + label + '</div>')
        .addTo(map);
    }}
  </script>
</body>
</html>
"""