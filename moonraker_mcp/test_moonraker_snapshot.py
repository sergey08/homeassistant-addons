"""Contract tests: bounded read-only U1 print and four-tool filament snapshots."""
import unittest
from moonraker_snapshot import (
    SnapshotError, normalize_print_status, normalize_filament_slots,
    read_status,
)


class SnapshotTests(unittest.TestCase):
    def test_print_snapshot_distinguishes_progress_sources(self):
        result = normalize_print_status({
            "print_stats": {"state": "printing", "filename": "model.gcode",
                            "print_duration": 95, "total_duration": 100,
                            "filament_used": 15.5,
                            "info": {"current_layer": 3, "total_layer": 10}},
            "virtual_sdcard": {"progress": .2, "is_active": True,
                               "file_path": "/private/path/model.gcode"},
            "display_status": {"progress": .3},
            "toolhead": {"extruder": "extruder2"},
        })
        self.assertEqual(result["active_tool"], "T2")
        self.assertEqual(result["display_progress_pct"], 30)
        self.assertEqual(result["file_progress_pct"], 20)
        self.assertIsNone(result["eta_seconds"])
        self.assertNotIn("file_path", result)

    def test_filters_private_nfc_fields(self):
        result = normalize_filament_slots({"filament_detect": {
            "state": [0, 0, 0, 0],
            "info": [{"MAIN_TYPE": "PLA+", "MANUFACTURER": "Sunlu",
                      "ARGB_COLOR": 0xFFFFFFFF, "CARD_UID": [1, 2, 3],
                      "RSA_KEY_VERSION": 2}] * 4,
        }})
        self.assertEqual(len(result["slots"]), 4)
        self.assertEqual(result["slots"][0]["slot"], "T0")
        self.assertEqual(result["slots"][0]["color_hex"], "FFFFFF")
        self.assertIsNone(result["slots"][0]["spoolman_id"])
        self.assertNotIn("CARD_UID", str(result))
        self.assertNotIn("RSA_KEY", str(result))

    def test_filament_sensor_readings_are_optional_and_true_false_are_distinct(self):
        status = {
            "filament_detect": {"info": [{"MAIN_TYPE": "PLA"}] * 4},
            "filament_motion_sensor e0_filament": {
                "enabled": True, "filament_detected": False, "secret": "hidden"},
            "filament_motion_sensor e1_filament": {
                "enabled": True, "filament_detected": True},
        }
        result = normalize_filament_slots(status)
        self.assertIs(result["slots"][0]["filament_detected"], False)
        self.assertIs(result["slots"][1]["filament_detected"], True)
        self.assertIsNone(result["slots"][2]["filament_detected"])
        self.assertIsNone(result["slots"][3]["filament_sensor_enabled"])
        self.assertNotIn("hidden", str(result))

    def test_paused_active_tool_without_filament_is_only_suspected_runout(self):
        status = {
            "print_stats": {"state": "paused"},
            "virtual_sdcard": {},
            "display_status": {},
            "toolhead": {"extruder": "extruder"},
            "filament_motion_sensor e0_filament": {
                "enabled": True, "filament_detected": False},
        }
        result = normalize_print_status(status)
        self.assertTrue(result["filament_alert"]["possible_runout"])
        self.assertFalse(result["filament_alert"]["cause_confirmed"])
        self.assertEqual(result["filament_alert"]["assessment"],
                         "possible_filament_runout")
        status["print_stats"]["state"] = "printing"
        result = normalize_print_status(status)
        self.assertFalse(result["filament_alert"]["possible_runout"])
        self.assertEqual(result["filament_alert"]["assessment"],
                         "no_filament_detected")

    def test_disabled_or_unavailable_sensor_does_not_claim_runout(self):
        status = {
            "print_stats": {"state": "paused"},
            "virtual_sdcard": {},
            "display_status": {},
            "toolhead": {"extruder": "extruder"},
            "filament_motion_sensor e0_filament": {
                "enabled": False, "filament_detected": False},
        }
        self.assertFalse(normalize_print_status(status)["filament_alert"]["possible_runout"])
        status.pop("filament_motion_sensor e0_filament")
        self.assertIsNone(normalize_print_status(status)["filament_alert"]["active_tool_filament_detected"])

    def test_unknown_material_is_not_fabricated(self):
        result = normalize_filament_slots({"filament_detect": {
            "info": [{"MAIN_TYPE": "UNKNOWN"}] * 4,
        }})
        self.assertEqual(result["slots"][0]["material"], "UNKNOWN")

    def test_absent_four_slot_object_is_explicit(self):
        self.assertFalse(normalize_filament_slots({})["available"])

    def test_malformed_slots_fail_closed(self):
        with self.assertRaises(SnapshotError):
            normalize_filament_slots({"filament_detect": {"info": [{}]}})

    def test_malformed_print_objects_fail_closed(self):
        with self.assertRaises(SnapshotError):
            normalize_print_status({"print_stats": {"state": "printing"}})

    def test_invalid_duration_and_progress_do_not_leak(self):
        result = normalize_print_status({
            "print_stats": {"state": "printing", "print_duration": -1,
                            "total_duration": float("inf")},
            "virtual_sdcard": {"progress": 4, "is_active": True},
            "display_status": {"progress": -1},
            "toolhead": {"extruder": "outside"},
        })
        self.assertIsNone(result["print_duration_s"])
        self.assertIsNone(result["total_duration_s"])
        self.assertIsNone(result["file_progress_pct"])
        self.assertIsNone(result["display_progress_pct"])
        self.assertIsNone(result["active_tool"])

    def test_status_request_has_fixed_read_only_objects(self):
        import io
        import json
        class Resp:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, n): return json.dumps({"result": {"status": {"print_stats": {}}}}).encode()
        def opener(req, timeout):
            self.assertEqual(req.get_method(), "GET")
            self.assertEqual(timeout, 10)
            self.assertIn("/printer/objects/query?", req.full_url)
            self.assertIn("filament_detect", req.full_url)
            self.assertIn("filament_motion_sensor%20e0_filament", req.full_url)
            self.assertIn("filament_motion_sensor%20e3_filament", req.full_url)
            self.assertNotIn("script=", req.full_url)
            return Resp()
        result = read_status("http://printer.local:7125", opener=opener)
        self.assertIn("print_stats", result)


if __name__ == "__main__":
    unittest.main()
