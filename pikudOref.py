import requests
import json
import time
import tkinter as tk
from tkinter import messagebox

# URL של פיקוד העורף – רגיש לאותיות!
URL = "https://www.oref.org.il/warningMessages/alert/alerts.json"

# כותרות HTTP כדי לדמות דפדפן
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.oref.org.il/",
    "Accept": "application/json"
}

last_alert_id = None  # כדי למנוע כפילויות

# פונקציה להצגת פופאפ מודרני
def show_popup(title, message):
    root = tk.Tk()
    root.withdraw()  # מסתיר את חלון ה-Tkinter הראשי
    messagebox.showwarning(title, message)
    root.destroy()

# פונקציה לזיהוי סוג האיום
# OREF API מחזירה שדה `type` עבור כל עיר (T=טילים, A=כלי טיס).
# נשתמש בזה קודם, ונשתמש בטקסט בכותרת כגיבוי.
def parse_threat_type(payload):
    first_item = None
    for item in payload.get("data", []):
        if isinstance(item, dict):
            first_item = item
            break

    if first_item:
        alert_type = (first_item.get("type") or "").upper()
        if alert_type == "T":
            return "ירי רקטות"
        if alert_type == "A":
            return "כלי טיס עוין"

    text = (payload.get("title") or payload.get("headline") or "").lower()
    if "טיל" in text or "רקטה" in text:
        return "ירי רקטות"
    if "כלי טיס" in text or "מטוס" in text:
        return "כלי טיס עוין"

    return "איום לא ידוע"


def extract_alert_id(payload):
    """Return a stable identifier for the current alert payload."""

    if not payload:
        return ""

    top_id = payload.get("id")
    if top_id:
        return str(top_id)

    items = payload.get("data") or []
    if items and isinstance(items[0], dict):
        item_id = items[0].get("id")
        if item_id:
            return str(item_id)

    try:
        return str(hash(json.dumps(payload, sort_keys=True)))
    except Exception:
        return ""


def build_message(payload):
    cities = []
    for item in payload.get("data", []):
        if isinstance(item, dict):
            city = item.get("cityName")
            if city:
                cities.append(city)

    cities = sorted(set(cities))
    cities_str = ", ".join(cities) if cities else "(לא ידוע)"

    title = payload.get("title") or payload.get("headline") or "התראה חדשה"
    threat = parse_threat_type(payload)

    return f"{threat}\n{title}\nאזורים: {cities_str}"


# לולאה רציפה לבדיקה כל 5 שניות
while True:
    try:
        r = requests.get(URL, headers=HEADERS, timeout=5)
        if r.status_code != 200:
            print("HTTP Error:", r.status_code)
            time.sleep(5)
            continue

        content = r.content.decode("utf-8-sig").strip()
        if not content:
            print("No data returned")
            time.sleep(5)
            continue

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            print("Response is not valid JSON:", repr(content))
            time.sleep(5)
            continue

        # בדיקה אם יש התראות פעילות
        if data and "data" in data and len(data["data"]) > 0:
            alert_id = extract_alert_id(data)
            if not alert_id:
                print("Could not determine alert id")
            elif alert_id != last_alert_id:
                last_alert_id = alert_id
                msg = build_message(data)

                print("\n🚨 NEW ALERT 🚨")
                print(msg)
                print("--------------------")

                # הצגת פופאפ
                show_popup("🚨 התראה מפיקוד העורף 🚨", msg)
            else:
                print("No new alerts")
        else:
            print("No alerts")

    except Exception as e:
        print("Error:", e)

    time.sleep(5)