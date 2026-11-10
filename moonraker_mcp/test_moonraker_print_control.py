"""No real printer requests: fake HTTP read/write responses for restricted controls."""
import io
import json
import unittest
from moonraker_print_control import execute_print_action, PrintControlError

class Reply:
    def __init__(self, data):
        self.handle = io.BytesIO(json.dumps(data).encode())
    def __enter__(self): return self.handle
    def __exit__(self, *args): self.handle.close()

class PrintControlTests(unittest.TestCase):
    def run_fake(self, action, state, confirmation=None, filename=None,
                 expected_filename=None, current_file="test.gcode", klippy="ready"):
        calls = []
        def opener(req, timeout):
            calls.append((req.get_method(), req.full_url))
            self.assertEqual(timeout, 10)
            if req.get_method() == "GET" and "/server/files/metadata?" in req.full_url:
                return Reply({"result": {"size": 12345}})
            if req.get_method() == "GET":
                return Reply({"result": {"status": {
                    "webhooks": {"state": klippy},
                    "print_stats": {"state": state, "filename": current_file},
                }}})
            return Reply({"result": "ok"})
        try:
            value = execute_print_action(
                "http://printer.local:7125", "test", action,
                confirmation if confirmation is not None else "CONFIRM_" + action.upper(),
                filename, expected_filename, opener)
            return calls, value
        except PrintControlError:
            return calls, None

    def test_pause_only_printing(self):
        calls, result = self.run_fake("pause", "printing")
        self.assertEqual([x[0] for x in calls], ["GET", "POST"])
        self.assertTrue(result["accepted"])
        calls, result = self.run_fake("pause", "paused")
        self.assertEqual([x[0] for x in calls], ["GET"])
        self.assertIsNone(result)

    def test_resume_only_paused(self):
        calls, result = self.run_fake("resume", "paused")
        self.assertEqual([x[0] for x in calls], ["GET", "POST"])
        self.assertTrue(result["accepted"])
        calls, result = self.run_fake("resume", "standby")
        self.assertEqual([x[0] for x in calls], ["GET"])
        self.assertIsNone(result)

    def test_cancel_requires_matching_active_filename(self):
        calls, result = self.run_fake("cancel", "printing", expected_filename="test.gcode")
        self.assertEqual([x[0] for x in calls], ["GET", "POST"])
        self.assertTrue(result["accepted"])
        calls, result = self.run_fake("cancel", "printing", expected_filename="other.gcode")
        self.assertEqual([x[0] for x in calls], ["GET"])
        self.assertIsNone(result)

    def test_start_only_from_idle_with_safe_filename(self):
        calls, result = self.run_fake("start", "standby", filename="folder/model.gcode")
        self.assertEqual([item[0] for item in calls], ["GET", "GET", "POST"])
        self.assertIn("folder%2Fmodel.gcode", calls[-1][1])
        self.assertTrue(result["accepted"])
        calls, result = self.run_fake("start", "printing", filename="model.gcode")
        self.assertEqual([x[0] for x in calls], ["GET"])
        self.assertIsNone(result)
        calls, result = self.run_fake("start", "standby", filename="../private.cfg")
        self.assertEqual(calls, [])
        self.assertIsNone(result)

    def test_start_rejects_missing_file_metadata_before_post(self):
        def opener(req, timeout):
            if "/printer/objects/query?" in req.full_url:
                return Reply({"result": {"status": {
                    "webhooks": {"state": "ready"},
                    "print_stats": {"state": "standby"},
                }}})
            if "/server/files/metadata?" in req.full_url:
                return Reply({"result": {"size": 0}})
            self.fail("Print POST must never be reached")
        with self.assertRaises(PrintControlError):
            execute_print_action("http://printer.local:7125", "", "start",
                                 "CONFIRM_START", filename="model.gcode", opener=opener)

    def test_confirmation_required_before_any_network_access(self):
        calls, result = self.run_fake("pause", "printing", confirmation="NO")
        self.assertEqual(calls, [])
        self.assertIsNone(result)

    def test_fail_closed_if_klipper_unavailable(self):
        calls, result = self.run_fake("cancel", "printing", klippy="shutdown",
                                      expected_filename="test.gcode")
        self.assertEqual([x[0] for x in calls], ["GET"])
        self.assertIsNone(result)

    def test_prevent_filename_arguments_for_other_operations(self):
        calls, result = self.run_fake("pause", "printing", filename="test.gcode")
        self.assertEqual(calls, [])
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
