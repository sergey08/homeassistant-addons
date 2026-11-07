"""Recovery never retries or guesses after an ambiguous disposable commit."""
import unittest
from livesync_isolated_recovery import inspect_isolated_commit
from livesync_write_preflight import UnsafeWrite


def plan():
    return {"write_order": ("leaf", "parent"), "write_supported": False,
            "leaf": {"_id": "h:+synthetic", "type": "leaf", "e_": True,
                     "data": "%=synthetic"},
            "parent": {"_id": "synthetic-parent", "type": "plain",
                       "children": ["h:+synthetic"], "_rev": "1-" + "a" * 32},
            "expected_parent_revision": "1-" + "a" * 32}


def successful_response(document):
    return 201, {"ok": True, "id": document["_id"],
                 "rev": ("1-" if document["type"] == "leaf" else "2-") + "b" * 32}


class IsolatedRecoveryTests(unittest.TestCase):
    def test_success_confirms_parent(self):
        calls = []
        def put(doc):
            calls.append(doc["type"])
            return successful_response(doc)
        result = inspect_isolated_commit(plan(), put, isolated_test=True)
        self.assertEqual(calls, ["leaf", "plain"])
        self.assertEqual(result["remote_state"], "parent_confirmed")
        self.assertFalse(result["retry_automatic"])

    def test_preflight_rejection_never_writes(self):
        unsafe = plan()
        unsafe["parent"]["_rev"] = "invalid"
        calls = []
        result = inspect_isolated_commit(unsafe, lambda doc: calls.append(doc),
                                         isolated_test=True)
        self.assertFalse(calls)
        self.assertEqual(result["remote_state"], "unchanged")

    def test_failed_leaf_is_uncertain_and_not_retried(self):
        calls = []
        def put(doc):
            calls.append(doc["type"])
            raise ConnectionError("synthetic-disconnect-secret")
        result = inspect_isolated_commit(plan(), put, isolated_test=True)
        self.assertEqual(calls, ["leaf"])
        self.assertEqual(result["remote_state"], "leaf_uncertain")
        self.assertFalse(result["retry_automatic"])
        self.assertNotIn("secret", str(result))

    def test_parent_conflict_must_be_inspected_manually(self):
        calls = []
        def put(doc):
            calls.append(doc["type"])
            if doc["type"] == "leaf":
                return successful_response(doc)
            return 409, {"error": "conflict"}
        result = inspect_isolated_commit(plan(), put, isolated_test=True)
        self.assertEqual(calls, ["leaf", "plain"])
        self.assertEqual(result["remote_state"], "parent_uncertain")
        self.assertIn("review_orphan_leaf", result["recovery"])

    def test_parent_timeout_is_not_assumed_to_have_failed(self):
        calls = []
        def put(doc):
            calls.append(doc["type"])
            if doc["type"] == "plain":
                raise TimeoutError("synthetic-timeout")
            return successful_response(doc)
        result = inspect_isolated_commit(plan(), put, isolated_test=True)
        self.assertEqual(calls, ["leaf", "plain"])
        self.assertEqual(result["remote_state"], "parent_uncertain")

    def test_never_runs_outside_disposable_tests(self):
        calls = []
        for kwargs in ({}, {"isolated_test": True, "remote_writes_enabled": True}):
            with self.assertRaises(UnsafeWrite):
                inspect_isolated_commit(plan(), lambda doc: calls.append(doc), **kwargs)
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
