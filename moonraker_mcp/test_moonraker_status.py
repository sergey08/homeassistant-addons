"""Tests for printer availability without touching a real printer."""
import io
import json
import unittest
import urllib.error
from unittest.mock import patch
from moonraker_status import connection_status


class MockResponse:
    def __init__(self, obj):
        self.status = 200
        self.payload = json.dumps(obj).encode()
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def read(self, size=-1):
        return self.payload[:size]


class StatusTests(unittest.TestCase):
    def test_printer_ready(self):
        with patch("moonraker_status._OPENER.open", return_value=MockResponse(
            {"result": {"klippy_state": "ready", "moonraker_version": "2.0.0"}})) as mock:
            result = connection_status("http://printer.local:7125", "hidden-test-key")
        self.assertEqual(result["state"], "online")
        self.assertEqual(result["klippy_state"], "ready")
        self.assertEqual(mock.call_args.args[0].headers["X-api-key"], "hidden-test-key")
        self.assertNotIn("hidden-test-key", str(result))

    def test_printer_offline(self):
        with patch("moonraker_status._OPENER.open", side_effect=urllib.error.URLError("secret address")):
            result = connection_status("http://printer.local:7125", "secret-key")
        self.assertEqual(result["state"], "offline_or_unreachable")
        self.assertIn("apagada", result["message"])
        self.assertNotIn("secret", str(result))

    def test_klippy_not_ready(self):
        with patch("moonraker_status._OPENER.open", return_value=MockResponse(
            {"result": {"klippy_state": "startup"}})):
            self.assertEqual(connection_status("http://printer.local")["state"], "not_ready")

    def test_auth_failure(self):
        with patch("moonraker_status._OPENER.open", side_effect=urllib.error.HTTPError(
            "http://printer.local", 403, "forbidden", {}, None)):
            result = connection_status("http://printer.local", "secret-key")
        self.assertEqual(result["state"], "authentication_error")
        self.assertNotIn("secret-key", str(result))

    def test_invalid_reply(self):
        with patch("moonraker_status._OPENER.open", return_value=MockResponse({"result": []})):
            self.assertEqual(connection_status("http://printer.local")["state"], "unavailable")

    def test_no_redirect(self):
        from moonraker_status import _NoRedirect
        self.assertIsNone(_NoRedirect().redirect_request(None, None, 302, "", {}, "https://another.example"))

if __name__ == "__main__":
    unittest.main()
