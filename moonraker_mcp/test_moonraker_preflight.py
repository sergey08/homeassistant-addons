import unittest
from moonraker_preflight import PreflightError, validate_u1_metadata

class PreflightTests(unittest.TestCase):
    def test_valid_metadata_is_not_automatically_approved(self):
        result = validate_u1_metadata("part.gcode", {"size": 200, "estimated_time": 120})
        self.assertFalse(result["safe_to_start"])
        self.assertEqual(result["compatible_with_u1"], "unverified")

    def test_traversal_rejected(self):
        with self.assertRaises(PreflightError):
            validate_u1_metadata("../part.gcode", {"size": 200})

    def test_non_gcode_rejected(self):
        with self.assertRaises(PreflightError):
            validate_u1_metadata("config.cfg", {"size": 200})

    def test_invalid_size_rejected(self):
        for value in (0, -1, True, float("nan"), "100"):
            with self.subTest(value=value), self.assertRaises(PreflightError):
                validate_u1_metadata("part.gcode", {"size": value})

    def test_bad_nozzle_rejected(self):
        with self.assertRaises(PreflightError):
            validate_u1_metadata("part.gcode", {"size": 200, "nozzle_diameter_list": [0.4] * 5})

if __name__ == "__main__":
    unittest.main()
