"""Run the Red Alert notifier as a module."""

from oref_alert.app import RedAlertApp


def main() -> None:
    app = RedAlertApp()
    app.run()


if __name__ == "__main__":
    main()
