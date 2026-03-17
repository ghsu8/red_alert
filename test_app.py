"""Basic set of sanity checks for the Red Alert app."""

import unittest


class AppInitializationTests(unittest.TestCase):
    def test_app_initializes(self):
        from oref_alert.app import RedAlertApp

        app = RedAlertApp()
        self.assertIsNotNone(app.config)
        self.assertIn(app.config.alert_mode, ["all", "custom", "נקודת ייחוס"])
        # App should have created the fetcher and tray icon logic
        self.assertIsNotNone(app._fetcher)


if __name__ == "__main__":
    unittest.main()
