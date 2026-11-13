"""Disposable encrypted multi-leaf commit: never updates parent before readback."""
import base64
import unittest
from copy import deepcopy

from livesync_crypto import encrypt_hkdf_string
from livesync_encrypted_metadata_fixture import encode_parent_metadata_fixture
from livesync_isolated_multichunk_commit import (
    commit_isolated_multichunk_plan, IncompleteMultichunkCommit)
from livesync_write_preflight import UnsafeWrite

PASSWORD = "isolated-test-passphrase"
SALT = base64.b64encode(b"isolated-multichunk-test-salt").decode()
REV = "1-" + "a" * 32


def example_plan():
    parts = ("Hola ", "mundo 🌍", "\n")
    ids = ["h:+synthetic" + str(i) for i in range(len(parts))]
    meta = encode_parent_metadata_fixture(
        "Tests/Three.md", ids, PASSWORD, SALT,
        ctime=100, mtime=200, size=len("".join(parts).encode("utf-8")))
    leaves = [
        {"_id": ident, "type": "leaf", "e_": True,
         "data": encrypt_hkdf_string(part, PASSWORD, SALT)}
        for ident, part in zip(ids, parts)
    ]
    return {"write_supported": False, "path": "Tests/Three.md",
            "expected_parent_revision": REV,
            "leaves": leaves,
            "parent": {"_id": "synthetic-parent", "_rev": REV,
                       "type": "plain", "path": meta["path"],
                       "children": [], "ctime": 0, "mtime": 0, "size": 0}}


class FakeCouchDB:
    def __init__(self, *, fail_leaf=None, readback_corrupt=False, parent_conflict=False):
        self.docs = {"synthetic-parent": {"_id": "synthetic-parent", "_rev": REV,
                                        "type": "plain", "path": "old-encrypted-content",
                                        "children": [], "ctime": 0, "mtime": 0, "size": 0}}
        self.fail_leaf = fail_leaf
        self.readback_corrupt = readback_corrupt
        self.parent_conflict = parent_conflict
        self.puts = []
        self.reads = []

    def put(self, doc):
        ident = doc["_id"]
        self.puts.append(ident)
        if doc["type"] == "leaf":
            if self.fail_leaf == ident:
                raise TimeoutError("synthetic-only")
            if ident in self.docs:
                return 409, {"error": "conflict"}
            self.docs[ident] = {**deepcopy(doc), "_rev": "1-" + "b" * 32}
            return 201, {"ok": True, "id": ident, "rev": "1-" + "b" * 32}
        if self.parent_conflict or doc["_rev"] != self.docs[ident]["_rev"]:
            return 409, {"error": "conflict"}
        self.docs[ident] = {**deepcopy(doc), "_rev": "2-" + "c" * 32}
        return 201, {"ok": True, "id": ident, "rev": "2-" + "c" * 32}

    def read(self, ident):
        self.reads.append(ident)
        result = deepcopy(self.docs.get(ident))
        if self.readback_corrupt and result is not None:
            result["data"] = "tampered"
        return result


class MultichunkCommitTests(unittest.TestCase):
    def run_plan(self, plan, fake):
        return commit_isolated_multichunk_plan(
            plan, fake.put, fake.read, PASSWORD, SALT, isolated_test=True)

    def test_three_chunks_confirmed_before_parent(self):
        plan = example_plan()
        fake = FakeCouchDB()
        result = self.run_plan(plan, fake)
        self.assertEqual(result["status"], "committed_in_disposable_test_only")
        self.assertEqual(result["confirmed_chunks"], 3)
        self.assertEqual(fake.puts, [doc["_id"] for doc in plan["leaves"]] +
                         [plan["parent"]["_id"]])
        self.assertEqual(fake.reads, [doc["_id"] for doc in plan["leaves"]])
        self.assertEqual(result["parent_revision"], "2-" + "c" * 32)

    def test_second_leaf_timeout_never_updates_parent(self):
        plan = example_plan()
        fake = FakeCouchDB(fail_leaf=plan["leaves"][1]["_id"])
        with self.assertRaises(IncompleteMultichunkCommit) as err:
            self.run_plan(plan, fake)
        self.assertEqual(err.exception.phase, "leaf_uncertain")
        self.assertEqual(err.exception.confirmed_chunks, 1)
        self.assertNotIn("synthetic-parent", fake.puts)
        self.assertEqual(fake.docs["synthetic-parent"]["_rev"], REV)

    def test_readback_mismatch_never_updates_parent(self):
        plan = example_plan()
        fake = FakeCouchDB(readback_corrupt=True)
        with self.assertRaises(IncompleteMultichunkCommit) as err:
            self.run_plan(plan, fake)
        self.assertEqual(err.exception.phase, "leaf_uncertain")
        self.assertEqual(err.exception.confirmed_chunks, 0)
        self.assertEqual(len(fake.puts), 1)

    def test_parent_conflict_does_not_retry_or_modify_previous(self):
        plan = example_plan()
        fake = FakeCouchDB(parent_conflict=True)
        with self.assertRaises(IncompleteMultichunkCommit) as err:
            self.run_plan(plan, fake)
        self.assertEqual(err.exception.phase, "parent_uncertain")
        self.assertEqual(err.exception.confirmed_chunks, 3)
        self.assertEqual(fake.puts.count("synthetic-parent"), 1)
        self.assertEqual(fake.docs["synthetic-parent"]["_rev"], REV)

    def test_wrong_content_and_size_blocked_without_put(self):
        plan = example_plan()
        plan["leaves"][1]["data"] = "%=invalid"
        fake = FakeCouchDB()
        with self.assertRaisesRegex(UnsafeWrite, "unverified_leaf_ciphertext"):
            self.run_plan(plan, fake)
        self.assertEqual(fake.puts, [])

    def test_missing_parent_revision_blocks_without_put(self):
        plan = example_plan()
        del plan["parent"]["_rev"]
        fake = FakeCouchDB()
        with self.assertRaises(UnsafeWrite):
            self.run_plan(plan, fake)
        self.assertEqual(fake.puts, [])

    def test_production_gate_blocks_before_transport(self):
        plan = example_plan()
        fake = FakeCouchDB()
        for kwargs in ({}, {"isolated_test": True, "remote_writes_enabled": True}):
            with self.assertRaisesRegex(UnsafeWrite, "isolated_commit_only"):
                commit_isolated_multichunk_plan(
                    plan, fake.put, fake.read, PASSWORD, SALT, **kwargs)
        self.assertEqual(fake.puts, [])


if __name__ == "__main__":
    unittest.main()
