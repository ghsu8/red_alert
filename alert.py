import requests
import time
import tkinter as tk
import threading
import json
import winsound

URL = "https://www.oref.org.il/warningMessages/alert/alerts.json"
last_alert = ""

def show_popup(message, title="אזעקה!"):
    winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)

    root = tk.Tk()
    root.overrideredirect(True)
    root.attributes("-topmost", True)

    width = 360
    height = 150
    x = root.winfo_screenwidth() - width - 20
    y = 20
    root.geometry(f"{width}x{height}+{x}+{y}")

    canvas = tk.Canvas(root, width=width, height=height, highlightthickness=0, bg="#EF4444")
    canvas.pack(fill="both", expand=True)

    # כותרת והודעה
    canvas.create_text(20, 20, anchor="nw", text=title, fill="white", font=("Arial", 14, "bold"))
    canvas.create_text(20, 50, anchor="nw", text=message, fill="white", font=("Arial", 12), width=width-40)

    # כפתור סגירה
    btn_close = tk.Button(root, text="✕", command=root.destroy,
                          bg="#EF4444", fg="white", font=("Arial", 12, "bold"),
                          relief="flat", bd=0, activebackground="#DC2626", cursor="hand2")
    btn_close.place(x=width-30, y=10, width=20, height=20)

    # כפתור Learn More
    def btn_action():
        print("Learn More clicked!")
        root.destroy()

    btn_action_widget = tk.Button(root, text="Learn More", command=btn_action,
                                  bg="#3B82F6", fg="white", font=("Arial", 10, "bold"),
                                  relief="flat", bd=0, activebackground="#2563EB", cursor="hand2")
    btn_action_widget.place(x=20, y=height-50, width=100, height=25)

    # אנימציה fade-in / fade-out
    def fade_in(step=0):
        if step <= 10:
            root.attributes("-alpha", step/10)
            root.after(30, lambda: fade_in(step+1))

    def fade_out(step=10):
        if step >= 0:
            root.attributes("-alpha", step/10)
            root.after(30, lambda: fade_out(step-1))
        else:
            root.destroy()

    root.attributes("-alpha", 0)
    fade_in()
    root.after(8000, fade_out)
    root.mainloop()


def check_alerts():
    global last_alert

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.oref.org.il/"
    }

    while True:
        try:
            print("Checking alerts...")
            response = requests.get(URL, headers=headers, timeout=10)
            text = response.content.decode("utf-8-sig").strip()

            if not text:
                print("No alerts")
                time.sleep(5)
                continue

            if text.startswith("{"):
                data = json.loads(text)

                if data != last_alert:
                    last_alert = data

                    alert_items = data.get("data", [])
                    messages = []

                    for alert in alert_items:
                        city = alert.get("cityName", "")
                        alert_type = alert.get("type", "")  # לדוגמה: "T" = טילים, "A" = כלי טיס
                        if alert_type == "T":
                            alert_kind = "ירי טילים"
                        elif alert_type == "A":
                            alert_kind = "כלי טיס עוין"
                        else:
                            alert_kind = "אזעקה כללית"

                        messages.append(f"{city} ({alert_kind})")

                    full_message = "\n".join(messages)
                    print("ALERT:", full_message)

                    threading.Thread(
                        target=show_popup,
                        args=(full_message,)
                    ).start()
            else:
                print("Server returned non JSON")

        except Exception as e:
            print("Error:", e)

        time.sleep(5)


print("Red Alert monitor started...")
check_alerts()