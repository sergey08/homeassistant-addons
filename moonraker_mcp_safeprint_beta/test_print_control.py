"""Offline regression tests: no Moonraker connection and no physical printer actions."""
import io
import json
import unittest
from unittest.mock import patch

from moonraker_print_control import execute_print_action, PrintControlError


class Response:
    def __init__(self, payload):
        self.data = io.BytesIO(json.dumps(payload).encode())

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.data.close()

    def read(self, count):
        return self.data.read(count)


class PrintControlTests(unittest.TestCase):
    def run_action(self, action, state, confirmation, filename=None, expected_filename=None):
        requests = []

        def fake_open(req, timeout=10):
            requests.append((req.get_method(), req.full_url))
            return Response({"result": "ok"})

        with patch("moonraker_print_control._state", return_value={
            "state": state, "filename": "test.gcode"
        }):
            result = execute_print_action(
                "http://127.0.0.1:7125", "", action, confirmation,
                filename=filename, expected_filename=expected_filename,
                opener=fake_open)
        return result, requests

    def test_pause_printing(self):
        result, requests = self.run_action("pause", "printing", "CONFIRM_PAUSE")
        self.assertTrue(result["accepted"])
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0][0], "POST")
        self.assertTrue(requests[0][1].endswith("/printer/print/pause"))

    def test_resume_paused(self):
        result, requests = self.run_action("resume", "paused", "CONFIRM_RESUME")
        self.assertTrue(result["accepted"])
        self.assertTrue(requests[0][1].endswith("/printer/print/resume"))

    def test_cancel_matching_filename(self):
        result, requests = self.run_action(
            "cancel", "printing", "CONFIRM_CANCEL", expected_filename="test.gcode")
        self.assertTrue(result["accepted"])
        self.assertTrue(requests[0][1].endswith("/printer/print/cancel"))

    def test_reject_cancel_wrong_filename(self):
        with self.assertRaises(PrintControlError):
            self.run_action(
                "cancel", "printing", "CONFIRM_CANCEL", expected_filename="other.gcode")

    def test_reject_pause_when_idle(self):
        with self.assertRaises(PrintControlError):
            self.run_action("pause", "complete", "CONFIRM_PAUSE")

    def test_reject_resume_when_printing(self):
        with self.assertRaises(PrintControlError):
            self.run_action("resume", "printing", "CONFIRM_RESUME")

    def test_reject_without_confirmation(self):
        with self.assertRaises(PrintControlError):
            self.run_action("pause", "printing", "WRONG")

    def test_reject_start_without_file(self):
        with self.assertRaises(PrintControlError):
            self.run_action("start", "standby", "CONFIRM_START")


    def test_pause_rejects_unconfirmed_moonraker_response(self):
        def fake_open(req, timeout=10):
            return Response({"result": {"unexpected": True}})
        with patch("moonraker_print_control._state", return_value={
            "state": "printing", "filename": "test.gcode"
        }):
            with self.assertRaisesRegex(PrintControlError, "did not confirm"):
                execute_print_action(
                    "http://127.0.0.1:7125", "", "pause", "CONFIRM_PAUSE",
                    opener=fake_open)

    def test_pause_network_failure_does_not_claim_success(self):
        from urllib.error import URLError
        def fake_open(req, timeout=10):
            raise URLError("offline")
        with patch("moonraker_print_control._state", return_value={
            "state": "printing", "filename": "test.gcode"
        }):
            with self.assertRaises(URLError):
                execute_print_action(
                    "http://127.0.0.1:7125", "", "pause", "CONFIRM_PAUSE",
                    opener=fake_open)

if __name__ == "__main__":
    unittest.main()
