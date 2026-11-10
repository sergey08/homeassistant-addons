"""Tests for the optional safe temperature history adapter (offline fixtures)."""
import json
import unittest
import urllib.error
from unittest.mock import patch

from moonraker_status import public_temperature_store


class Response:
    status = 200

    def __init__(self, data):
        self.data = json.dumps(data).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limit):
        return self.data[:limit]


class TemperaturePrivacyTests(unittest.TestCase):
    def test_bounded_recent_history_and_private_sensor_names(self):
        source = {"result": {
            "extruder": {
                "temperatures": list(range(1200)),
                "targets": [205] * 1200,
                "powers": [0.5] * 1200,
            },
            "temperature_sensor private_room": {
                "temperatures": [24.5] * 1200,
            },
        }}
        with patch("moonraker_status._OPENER.open", return_value=Response(source)):
            result = public_temperature_store("http://printer.local:7125", "placeholder")
        self.assertEqual(set(result), {"extruder", "sensor_1"})
        self.assertEqual(result["extruder"]["temperatures"][0], 1080)
        self.assertEqual(len(result["extruder"]["temperatures"]), 120)
        self.assertEqual(len(result["sensor_1"]["temperatures"]), 120)
        self.assertNotIn("private_room", json.dumps(result))

    def test_reject_invalid_measurements(self):
        for bad in ([None], ["not numeric"], [True], list(range(2401))):
            with self.subTest(sample_type=type(bad[0]).__name__):
                source = {"result": {"extruder": {"temperatures": bad}}}
                with patch("moonraker_status._OPENER.open", return_value=Response(source)):
                    self.assertEqual(public_temperature_store("http://printer.local"), {"state": "unavailable"})

    def test_unreachable_printer(self):
        with patch("moonraker_status._OPENER.open", side_effect=urllib.error.URLError("offline")):
            self.assertEqual(public_temperature_store("http://printer.local"),
                             {"state": "offline_or_unreachable"})


if __name__ == "__main__":
    unittest.main()
