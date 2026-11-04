"""Test-only commit protocol checks, with an in-memory transport."""
import unittest
from livesync_isolated_commit import commit_isolated_plan
from livesync_write_preflight import UnsafeWrite
from livesync_revision_contract import RevisionConflict


def plan():
    return {"write_order":("leaf","parent"),
            "leaf":{"_id":"h:+abc","type":"leaf","e_":True,"data":"%="},
            "parent":{"_id":"notes/example.md","type":"plain",
                      "children":["h:+abc"],"_rev":"1-"+"a"*32}}


class TestIsolatedCommit(unittest.TestCase):
    def test_leaf_first_and_parent_last(self):
        calls=[]
        def fake_put(doc):
            calls.append(doc["_id"])
            return 201,{"ok":True,"id":doc["_id"],
                        "rev":("2-"+"b"*32) if doc["type"]=="plain" else "1-"+"c"*32}
        result=commit_isolated_plan(plan(),fake_put,isolated_test=True)
        self.assertEqual(calls,["h:+abc","notes/example.md"])
        self.assertEqual(result["status"],"committed_in_disposable_test_only")

    def test_production_disabled_even_with_fake_transport(self):
        for kwargs in ({}, {"isolated_test":False},
                       {"isolated_test":True,"remote_writes_enabled":True}):
            calls=[]
            with self.assertRaises(UnsafeWrite):
                commit_isolated_plan(plan(),lambda x:calls.append(x),**kwargs)
            self.assertFalse(calls)

    def test_stale_parent_revision_stops_without_retry(self):
        calls=[]
        def fake_put(doc):
            calls.append(doc["_id"])
            if doc["type"]=="plain":
                return 409,{"error":"conflict"}
            return 201,{"ok":True,"id":doc["_id"],"rev":"1-"+"c"*32}
        with self.assertRaisesRegex(RevisionConflict,"remote_revision_conflict"):
            commit_isolated_plan(plan(),fake_put,isolated_test=True)
        self.assertEqual(calls,["h:+abc","notes/example.md"])

    def test_leaf_ack_identity_mismatch_stops_before_parent(self):
        calls=[]
        def fake_put(doc):
            calls.append(doc["_id"])
            return 201,{"ok":True,"id":"other","rev":"1-"+"b"*32}
        with self.assertRaisesRegex(RevisionConflict,"remote_document_identity_mismatch"):
            commit_isolated_plan(plan(),fake_put,isolated_test=True)
        self.assertEqual(calls,["h:+abc"])

    def test_parent_ack_revision_mismatch_is_rejected_without_retry(self):
        calls=[]
        def fake_put(doc):
            calls.append(doc["_id"])
            if doc["type"]=="plain":
                return 201,{"ok":True,"id":doc["_id"],"rev":"3-"+"c"*32}
            return 201,{"ok":True,"id":doc["_id"],"rev":"1-"+"c"*32}
        with self.assertRaisesRegex(RevisionConflict,"unexpected_revision_generation"):
            commit_isolated_plan(plan(),fake_put,isolated_test=True)
        self.assertEqual(calls,["h:+abc","notes/example.md"])

    def test_new_parent_create_uses_generation_one(self):
        candidate=plan()
        del candidate["parent"]["_rev"]
        calls=[]
        def fake_put(doc):
            calls.append(doc["_id"])
            return 201,{"ok":True,"id":doc["_id"],"rev":"1-"+"d"*32}
        result=commit_isolated_plan(candidate,fake_put,isolated_test=True)
        self.assertEqual(result["status"],"committed_in_disposable_test_only")
        self.assertEqual(calls,["h:+abc","notes/example.md"])

    def test_invalid_parent_revision_fails_before_any_put(self):
        for revision in (None, "", "1-invalid", "0-"+"a"*32,
                         "1-"+"g"*32, 123, ["invalid"]):
            candidate=plan()
            candidate["parent"]["_rev"]=revision
            calls=[]
            with self.subTest(revision=revision), self.assertRaises(RevisionConflict):
                commit_isolated_plan(candidate,lambda doc:calls.append(doc),
                                     isolated_test=True)
            self.assertEqual(calls,[])

    def test_deleted_or_conflicted_documents_rejected_before_any_put(self):
        for kind in ("leaf", "parent"):
            for field, value in (("_deleted", True), ("deleted", True),
                                 ("_conflicts", ["2-" + "b" * 32])):
                candidate = plan()
                candidate[kind][field] = value
                calls = []
                with self.subTest(kind=kind, field=field), self.assertRaisesRegex(
                        UnsafeWrite, "deleted_or_conflicted_document"):
                    commit_isolated_plan(candidate, lambda doc: calls.append(doc),
                                         isolated_test=True)
                self.assertEqual(calls, [])

    def test_leaf_revision_cannot_overwrite_existing_chunk(self):
        for rev in ("1-"+"a"*32, None, "invalid"):
            candidate=plan()
            candidate["leaf"]["_rev"]=rev
            calls=[]
            with self.subTest(rev=rev), self.assertRaisesRegex(
                    UnsafeWrite, "leaf_update_not_supported"):
                commit_isolated_plan(candidate,lambda doc:calls.append(doc),
                                     isolated_test=True)
            self.assertEqual(calls,[])

    def test_parent_and_leaf_identity_cannot_collide(self):
        candidate=plan()
        candidate["parent"]["_id"]=candidate["leaf"]["_id"]
        calls=[]
        with self.assertRaisesRegex(UnsafeWrite,"parent_leaf_identity_collision"):
            commit_isolated_plan(candidate,lambda doc:calls.append(doc),
                                 isolated_test=True)
        self.assertEqual(calls,[])

    def test_invalid_encrypted_leaf_payload_stops_before_any_put(self):
        for value in (None, "", "plaintext", "encrypted", 123, ["%="], {}):
            candidate=plan()
            candidate["leaf"]["data"]=value
            calls=[]
            with self.subTest(value=value), self.assertRaisesRegex(
                    UnsafeWrite, "invalid_encrypted_leaf_payload"):
                commit_isolated_plan(candidate,lambda doc:calls.append(doc),
                                     isolated_test=True)
            self.assertEqual(calls,[])

    def test_rejects_mismatched_document_or_order_before_write(self):
        for mutation in ("badorder","badleaf","badparent"):
            candidate=plan()
            if mutation=="badorder":
                candidate["write_order"]=("parent","leaf")
            elif mutation=="badleaf":
                candidate["leaf"]["e_"]=False
            else:
                candidate["parent"]["children"]=["h:+other"]
            calls=[]
            with self.assertRaises(UnsafeWrite):
                commit_isolated_plan(candidate,lambda x:calls.append(x),
                                     isolated_test=True)
            self.assertEqual(calls,[])

if __name__=="__main__":
    unittest.main()
