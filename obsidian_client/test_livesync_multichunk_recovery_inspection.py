"""Post-interruption diagnostics are read-only, fail-closed and bounded."""
import unittest
from copy import deepcopy
from test_livesync_isolated_multichunk_commit import example_plan, PASSWORD, SALT
from livesync_multichunk_recovery_inspection import inspect_interrupted_multichunk
from livesync_write_preflight import UnsafeWrite

OLD_REV = "1-" + "a" * 32
NEW_REV = "2-" + "b" * 32


class RecoveryInspectionTests(unittest.TestCase):
    def setUp(self):
        self.plan = example_plan()
        self.docs = {leaf["_id"]: {**deepcopy(leaf), "_rev": "1-" + "c" * 32}
                     for leaf in self.plan["leaves"]}
        self.parent = {**deepcopy(self.plan["parent"]), "_rev": NEW_REV}
        self.events = []

    def inspect(self, **kwargs):
        def read(key):
            self.events.append(key)
            return deepcopy(self.parent) if key == self.parent["_id"] else deepcopy(self.docs.get(key))
        return inspect_interrupted_multichunk(
            self.plan, read, PASSWORD, SALT, isolated_test=True, **kwargs)

    def test_parent_and_three_leaves_verified_without_writes(self):
        result = self.inspect()
        self.assertEqual(result["state"], "committed")
        self.assertEqual(result["confirmed_leaves"], 3)
        self.assertEqual(self.events, ["synthetic-parent"] +
                         [x["_id"] for x in self.plan["leaves"]] +
                         ["synthetic-parent"])
        self.assertFalse(result["automatic_retry"])
        self.assertFalse(result["safe_to_delete"])

    def test_old_revision_and_partial_leaf_creation(self):
        self.parent["_rev"] = OLD_REV
        self.parent["path"] = "original-ciphertext-placeholder"
        del self.docs[self.plan["leaves"][2]["_id"]]
        # The old metadata cannot be decrypted => uncertain, never committed.
        result = self.inspect()
        self.assertEqual(result["state"], "unknown")
        self.assertEqual(result["missing_leaves"], 1)
        self.assertFalse(result["automatic_cleanup"])

    def test_verified_old_parent_is_not_committed(self):
        from livesync_encrypted_metadata_fixture import encode_parent_metadata_fixture
        previous = encode_parent_metadata_fixture(
            self.plan["path"], ["h:+previous"], PASSWORD, SALT,
            ctime=100, mtime=100, size=5)
        self.parent["_rev"] = OLD_REV
        self.parent["path"] = previous["path"]
        result = self.inspect()
        self.assertEqual(result["state"], "not_committed")
        self.assertEqual(result["reason"], "old_parent_revision_remains")
        self.assertFalse(result["safe_to_delete"])

    def test_other_valid_revision_and_metadata_is_conflict(self):
        from livesync_encrypted_metadata_fixture import encode_parent_metadata_fixture
        another = encode_parent_metadata_fixture(
            self.plan["path"], ["h:+other"], PASSWORD, SALT,
            ctime=100, mtime=300, size=5)
        self.parent["_rev"] = "3-" + "d" * 32
        self.parent["path"] = another["path"]
        result = self.inspect()
        self.assertEqual(result["state"], "conflict")
        self.assertFalse(result["automatic_retry"])

    def test_missing_leaf_even_with_new_parent_is_unknown(self):
        del self.docs[self.plan["leaves"][1]["_id"]]
        result = self.inspect()
        self.assertEqual(result["state"], "unknown")
        self.assertEqual(result["reason"], "parent_points_to_unverified_leaves")

    def test_tampered_leaf_even_with_new_parent_is_unknown(self):
        self.docs[self.plan["leaves"][0]["_id"]]["data"] = "%=tampered"
        result = self.inspect()
        self.assertEqual(result["state"], "unknown")
        self.assertEqual(result["mismatched_leaves"], 1)

    def test_parent_revision_changed_by_another_writer(self):
        self.parent["_rev"] = "3-" + "d" * 32
        self.parent["path"] = self.plan["parent"]["path"] + "other"
        result = self.inspect()
        self.assertEqual(result["state"], "unknown")
        self.assertFalse(result["automatic_retry"])

    def test_unstable_parent_between_reads(self):
        count = 0
        def read(key):
            nonlocal count
            if key == "synthetic-parent":
                count += 1
                return {**self.parent, "_rev": NEW_REV if count == 1 else "3-" + "d" * 32}
            return self.docs[key]
        result = inspect_interrupted_multichunk(
            self.plan, read, PASSWORD, SALT, isolated_test=True)
        self.assertEqual(result["state"], "unknown")

    def test_failed_read_yields_no_inferred_success(self):
        def read(_):
            raise TimeoutError("private-data-in-exception")
        result = inspect_interrupted_multichunk(
            self.plan, read, PASSWORD, SALT, isolated_test=True)
        self.assertEqual(result["state"], "unknown")
        self.assertNotIn("private-data", str(result))

    def test_explicit_disposable_gate(self):
        called = []
        for opts in ({}, {"isolated_test": True, "remote_writes_enabled": True}):
            with self.assertRaisesRegex(UnsafeWrite, "isolated_inspection_only"):
                inspect_interrupted_multichunk(
                    self.plan, lambda x: called.append(x),
                    PASSWORD, SALT, **opts)
        self.assertEqual(called, [])


if __name__ == "__main__":
    unittest.main()
