"""Test-only commit protocol checks, with an in-memory transport."""
import unittest
from copy import deepcopy
from livesync_isolated_commit import commit_isolated_plan
from livesync_write_preflight import UnsafeWrite
from livesync_revision_contract import RevisionConflict


def plan():
    return {"write_order":("leaf","parent"),
            "leaf":{"_id":"h:+abc","type":"leaf","e_":True,"data":"%="},
            "parent":{"_id":"notes/example.md","type":"plain",
                      "children":["h:+abc"],"_rev":"1-"+"a"*32}}


class TestIsolatedCommit(unittest.TestCase):
    def test_external_plan_mutation_cannot_change_validated_commit(self):
        candidate=plan()
        candidate["parent"]["nested"]={"tags":["original"]}
        expected=deepcopy(candidate)
        sent=[]
        def mutating_put(doc):
            sent.append(deepcopy(doc))
            if doc["type"]=="leaf":
                candidate["parent"]["_id"]="other.md"
                candidate["parent"]["_rev"]="9-"+"d"*32
                candidate["parent"]["children"].append("h:+injected")
                candidate["parent"]["nested"]["tags"].append("injected")
                return 201,{"ok":True,"id":doc["_id"],"rev":"1-"+"c"*32}
            return 201,{"ok":True,"id":doc["_id"],"rev":"2-"+"b"*32}
        result=commit_isolated_plan(candidate,mutating_put,isolated_test=True)
        self.assertEqual(sent,[expected["leaf"],expected["parent"]])
        self.assertEqual(result["parent_id"],expected["parent"]["_id"])

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

    def test_isolated_transport_rejects_write_enabled_plans(self):
        for flag in (True, 1, "true", None):
            candidate=plan()
            candidate["write_supported"]=flag
            calls=[]
            with self.subTest(flag=flag), self.assertRaisesRegex(
                    UnsafeWrite, "production_write_plan_forbidden"):
                commit_isolated_plan(candidate,lambda doc:calls.append(doc),
                                     isolated_test=True)
            self.assertEqual(calls,[])

    def test_explicitly_read_only_plan_still_commits_in_disposable_test(self):
        candidate=plan()
        candidate["write_supported"]=False
        calls=[]
        def fake_put(doc):
            calls.append(doc["_id"])
            rev="1-"+"c"*32 if doc["type"]=="leaf" else "2-"+"b"*32
            return 201,{"ok":True,"id":doc["_id"],"rev":rev}
        result=commit_isolated_plan(candidate,fake_put,isolated_test=True)
        self.assertEqual(result["status"],"committed_in_disposable_test_only")
        self.assertEqual(calls,["h:+abc","notes/example.md"])

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

    def test_leaf_failure_never_attempts_parent_or_retries(self):
        for status, payload, expected_error in (
                (409, {"error":"conflict"}, "remote_revision_conflict"),
                (503, {"error":"unavailable"}, "remote_write_not_confirmed"),
                (201, {"ok":True,"id":"h:+abc","rev":"2-"+"c"*32},
                 "unexpected_revision_generation")):
            candidate=plan()
            original=deepcopy(candidate)
            calls=[]
            def fake_put(doc):
                calls.append(doc["_id"])
                return status,payload
            with self.subTest(status=status,payload=payload), self.assertRaisesRegex(
                    RevisionConflict,expected_error):
                commit_isolated_plan(candidate,fake_put,isolated_test=True)
            self.assertEqual(calls,["h:+abc"])
            self.assertEqual(candidate,original)

    def test_parent_failure_never_retries_or_mutates_input(self):
        for status,payload,expected_error in (
                (409, {"error":"conflict"}, "remote_revision_conflict"),
                (503, {"error":"unavailable"}, "remote_write_not_confirmed")):
            candidate=plan()
            original=deepcopy(candidate)
            calls=[]
            def fake_put(doc):
                calls.append(doc["_id"])
                if doc["type"]=="leaf":
                    return 201,{"ok":True,"id":doc["_id"],"rev":"1-"+"c"*32}
                return status,payload
            with self.subTest(status=status), self.assertRaisesRegex(
                    RevisionConflict,expected_error):
                commit_isolated_plan(candidate,fake_put,isolated_test=True)
            self.assertEqual(calls,["h:+abc","notes/example.md"])
            self.assertEqual(candidate,original)

    def test_transport_exceptions_stop_without_retry_or_parent_fallback(self):
        for fail_kind in ("leaf","parent"):
            candidate=plan()
            original=deepcopy(candidate)
            calls=[]
            def fake_put(doc):
                calls.append(doc["_id"])
                if doc["type"]==fail_kind:
                    raise ConnectionError("synthetic_network_disconnect")
                return 201,{"ok":True,"id":doc["_id"],"rev":"1-"+"c"*32}
            with self.subTest(fail_kind=fail_kind), self.assertRaisesRegex(
                    ConnectionError,"synthetic_network_disconnect"):
                commit_isolated_plan(candidate,fake_put,isolated_test=True)
            expected_calls=(["h:+abc"] if fail_kind=="leaf" else
                            ["h:+abc","notes/example.md"])
            self.assertEqual(calls,expected_calls)
            self.assertEqual(candidate,original)

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

    def test_expected_parent_revision_must_match_before_leaf_put(self):
        for expected in ("2-"+"b"*32, "invalid", None):
            candidate=plan()
            candidate["expected_parent_revision"]=expected
            calls=[]
            with self.subTest(expected=expected), self.assertRaises(RevisionConflict):
                commit_isolated_plan(candidate,lambda doc:calls.append(doc),
                                     isolated_test=True)
            self.assertEqual(calls,[])

    def test_expected_parent_revision_requires_existing_parent_revision(self):
        candidate=plan()
        del candidate["parent"]["_rev"]
        candidate["expected_parent_revision"]="1-"+"a"*32
        calls=[]
        with self.assertRaises(RevisionConflict):
            commit_isolated_plan(candidate,lambda doc:calls.append(doc),
                                 isolated_test=True)
        self.assertEqual(calls,[])

    def test_matching_expected_parent_revision_keeps_leaf_first_protocol(self):
        candidate=plan()
        candidate["expected_parent_revision"]=candidate["parent"]["_rev"]
        calls=[]
        def put(doc):
            calls.append(doc["_id"])
            rev="1-"+"c"*32 if doc["type"]=="leaf" else "2-"+"b"*32
            return 201,{"ok":True,"id":doc["_id"],"rev":rev}
        result=commit_isolated_plan(candidate,put,isolated_test=True)
        self.assertEqual(result["status"],"committed_in_disposable_test_only")
        self.assertEqual(calls,["h:+abc","notes/example.md"])

    def test_attachments_rejected_before_any_disposable_put(self):
        for kind in ("leaf", "parent"):
            for value in ({}, {"a.txt":{"data":"YQ==","content_type":"text/plain"}}):
                candidate=plan()
                candidate[kind]["_attachments"]=value
                calls=[]
                with self.subTest(kind=kind,value=value), self.assertRaisesRegex(
                        UnsafeWrite, "attachments_not_supported"):
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

    def test_transport_cannot_mutate_nested_plan_metadata(self):
        candidate=plan()
        candidate["parent"]["nested"]={"tags":["untouched"]}
        original_children=list(candidate["parent"]["children"])
        calls=[]
        def mutating_put(doc):
            calls.append(doc["_id"])
            if doc["type"]=="plain":
                doc["children"].append("h:+injected")
                doc["nested"]["tags"].append("injected")
                return 201,{"ok":True,"id":doc["_id"],"rev":"2-"+"b"*32}
            return 201,{"ok":True,"id":doc["_id"],"rev":"1-"+"c"*32}
        result=commit_isolated_plan(candidate,mutating_put,isolated_test=True)
        self.assertEqual(result["status"],"committed_in_disposable_test_only")
        self.assertEqual(calls,["h:+abc","notes/example.md"])
        self.assertEqual(candidate["parent"]["children"],original_children)
        self.assertEqual(candidate["parent"]["nested"],{"tags":["untouched"]})

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
