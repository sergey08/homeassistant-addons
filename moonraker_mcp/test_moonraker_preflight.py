"""Offline-only tests. No printer, spool mutation, or network requests."""
import unittest
from moonraker_preflight import PreflightError, validate_plan, evaluate_preflight

def stock(remaining, archived=False):
    return {"count": 1, "spools": [{"id": 4, "remaining_weight_g": remaining,
                                   "archived": archived, "filament": {"material": "PLA"}}]}

class FilamentPreflightTests(unittest.TestCase):
    def test_sufficient_with_reserve(self):
        result = evaluate_preflight({"T0": 100}, {"T0": 4}, stock(120))
        self.assertTrue(result["can_confirm_sufficient"])
        self.assertEqual(result["results"][0]["required_with_reserve_g"], 110)
        self.assertEqual(result["results"][0]["assessment"], "sufficient")
        self.assertEqual(result["mapping_source"], "user_supplied_not_verified_by_printer")

    def test_insufficient_including_reserve(self):
        result = evaluate_preflight({"T0": 100}, {"T0": 4}, stock(105))
        self.assertFalse(result["can_confirm_sufficient"])
        self.assertEqual(result["results"][0]["assessment"], "insufficient")

    def test_unmapped_tool_is_unknown_not_sufficient(self):
        result = evaluate_preflight({"T0": 100}, {}, stock(1000))
        self.assertFalse(result["can_confirm_sufficient"])
        self.assertEqual(result["results"][0]["assessment"], "unknown_mapping")

    def test_missing_spool_is_unknown(self):
        result = evaluate_preflight({"T0": 50}, {"T0": 9}, stock(1000))
        self.assertFalse(result["can_confirm_sufficient"])
        self.assertEqual(result["results"][0]["assessment"], "spool_not_found")

    def test_archived_or_missing_weight_not_sufficient(self):
        result = evaluate_preflight({"T0": 20}, {"T0": 4}, stock(1000, True))
        self.assertEqual(result["results"][0]["assessment"], "archived_spool")
        result = evaluate_preflight({"T0": 20}, {"T0": 4}, stock(None))
        self.assertEqual(result["results"][0]["assessment"], "unknown_remaining")

    def test_plan_validation_rejects_unsafe_values(self):
        invalid = [
            ({"T4": 10}, {}),
            ({"T0": 0}, {}),
            ({"T0": -4}, {}),
            ({"T0": True}, {}),
            ({"T0": float("nan")}, {}),
            ({"T0": 30}, {"T0": True}),
            ({"T0": 30}, {"T1": 4}),
            ({"T0": 30, "T1": 40}, {"T0": 4, "T1": 4}),
            ({"T0": 30}, {"T0": -1}),
        ]
        for req, assignments in invalid:
            with self.subTest(req=req, assignments=assignments), self.assertRaises(PreflightError):
                validate_plan(req, assignments)

    def test_multiple_tools_only_complete_when_all_are_sufficient(self):
        inventory = {"count": 2, "spools": [
            {"id": 4, "remaining_weight_g": 100, "archived": False},
            {"id": 5, "remaining_weight_g": 25, "archived": False}]}
        result = evaluate_preflight({"T0": 50, "T1": 25},
                                    {"T0": 4, "T1": 5}, inventory)
        self.assertFalse(result["can_confirm_sufficient"])
        self.assertEqual([x["assessment"] for x in result["results"]],
                         ["sufficient", "insufficient"])
        self.assertNotIn("pass", str(result))

if __name__ == "__main__":
    unittest.main()
