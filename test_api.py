"""Smoke tests for the OREF alert API endpoints."""

import unittest

import requests


class ApiEndpointTests(unittest.TestCase):
    def test_primary_alert_api_is_reachable(self):
        url = "https://www.oref.org.il/warningMessages/alert/alerts.json"
        headers = {
            "User-Agent": "RedAlertDesktop/1.0",
            "Referer": "https://www.oref.org.il/",
        }

        try:
            resp = requests.get(url, headers=headers, timeout=10)
        except requests.RequestException as exc:
            self.skipTest(f"Network unavailable or endpoint unreachable: {exc}")
            return

        # The endpoint may return an empty payload when there are no active alerts.
        self.assertIn(resp.status_code, {200, 204})


if __name__ == "__main__":
    unittest.main()

