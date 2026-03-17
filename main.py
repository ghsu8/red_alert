"""Entry point for the Red Alert desktop notifier.

This application runs on Windows and displays Home Front Command alerts as edge popups.
The design is modular so new notification types, rules, and UI panels can be added later.

Run:
    python main.py

If packaged with PyInstaller, the entry point should be set to this script.
"""

from oref_alert.app import RedAlertApp


def main() -> None:
    app = RedAlertApp()
    app.run()


if __name__ == "__main__":
    main()
