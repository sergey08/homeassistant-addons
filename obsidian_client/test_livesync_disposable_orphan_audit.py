"""Offline-only tests for non-destructive orphan candidate reporting."""
import unittest

from livesync_disposable_orphan_audit import audit_disposable_chunk_references
from livesync_write_preflight import UnsafeWrite


def parent(children, parent_id="f:note"):
    return {"_id":parent_id,"type":"plain","children":children}


def leaf(chunk_id):
    return {"_id":chunk_id,"type":"leaf"}


def audit(parents, leaves, **kwargs):
    return audit_disposable_chunk_references(
        parents,leaves,isolated_test=True,snapshot_complete=True,**kwargs)


class DisposableOrphanAuditTests(unittest.TestCase):
    def test_reports_losing_cas_leaf_as_candidate_without_deleting(self):
        result=audit([parent(["h:+winner"])],
                     [leaf("h:+winner"),leaf("h:+loser")])
        self.assertEqual(result["unreferenced_leaf_candidates"],("h:+loser",))
        self.assertEqual(result["missing_referenced_leaf_ids"],())
        self.assertIs(result["deletion_permitted"],False)

    def test_shared_chunks_are_not_classified_as_orphans(self):
        result=audit([parent(["h:+shared"],"f:first"),
                      parent(["h:+shared"],"f:second")],[leaf("h:+shared")])
        self.assertEqual(result["unreferenced_leaf_candidates"],())

    def test_duplicate_chunk_reference_within_parent_fails_closed(self):
        parents=[parent(["h:+same","h:+same"])]
        leaves=[leaf("h:+same")]
        with self.assertRaisesRegex(UnsafeWrite,"duplicate_parent_chunk_reference"):
            audit(parents,leaves)
        self.assertEqual(parents[0]["children"],["h:+same","h:+same"])

    def test_same_chunk_across_different_parents_remains_valid(self):
        parents=[parent(["h:+shared"],"f:one"),
                 parent(["h:+shared"],"f:two")]
        result=audit(parents,[leaf("h:+shared")])
        self.assertEqual(result["unreferenced_leaf_candidates"],())
        self.assertEqual(result["missing_referenced_leaf_ids"],())

    def test_missing_chunks_reported_without_any_mutation(self):
        parents=[parent(["h:+present","h:+missing"])]
        leaves=[leaf("h:+present")]
        result=audit(parents,leaves)
        self.assertEqual(result["missing_referenced_leaf_ids"],("h:+missing",))
        self.assertEqual(parents[0]["children"],["h:+present","h:+missing"])
        self.assertEqual(len(leaves),1)

    def test_incomplete_or_nonisolated_snapshots_rejected(self):
        for isolated,complete in ((False,True),(True,False),(False,False),
                                  (1,True),(True,1)):
            with self.subTest(isolated=isolated,complete=complete), self.assertRaisesRegex(
                    UnsafeWrite,"complete_disposable_snapshot_required"):
                audit_disposable_chunk_references(
                    [parent(["h:+present"])],[leaf("h:+present")],
                    isolated_test=isolated,snapshot_complete=complete)

    def test_invalid_optional_revisions_fail_closed(self):
        for kind in ("parent", "leaf"):
            for rev in (None, "", "1-invalid", "0-"+"a"*32,
                        "1-"+"g"*32, 123, ["invalid"]):
                parents=[parent(["h:+kept"])]
                leaves=[leaf("h:+kept")]
                (parents[0] if kind=="parent" else leaves[0])["_rev"]=rev
                with self.subTest(kind=kind,rev=rev), self.assertRaisesRegex(
                        UnsafeWrite,"invalid_snapshot_revision"):
                    audit(parents,leaves)

    def test_valid_optional_revisions_do_not_change_report(self):
        parents=[dict(parent(["h:+winner"]),_rev="2-"+"a"*32)]
        leaves=[dict(leaf("h:+winner"),_rev="1-"+"b"*32),
                dict(leaf("h:+loser"),_rev="1-"+"c"*32)]
        result=audit(parents,leaves)
        self.assertEqual(result["unreferenced_leaf_candidates"],("h:+loser",))
        self.assertIs(result["deletion_permitted"],False)

    def test_overwritten_leaf_revision_rejected_in_disposable_audit(self):
        for revision in ("2-"+"a"*32, "3-"+"b"*32, "10-"+"c"*32):
            parents=[dict(parent(["h:+kept"]),_rev="7-"+"d"*32)]
            leaves=[dict(leaf("h:+kept"),_rev=revision)]
            with self.subTest(revision=revision), self.assertRaisesRegex(
                    UnsafeWrite,"overwritten_leaf_snapshot"):
                audit(parents,leaves)

    def test_fresh_leaf_revision_remains_valid(self):
        result=audit([dict(parent(["h:+kept"]),_rev="8-"+"a"*32)],
                     [dict(leaf("h:+kept"),_rev="1-"+"b"*32)])
        self.assertEqual(result["unreferenced_leaf_candidates"],())
        self.assertEqual(result["missing_referenced_leaf_ids"],())
        self.assertIs(result["deletion_permitted"],False)

    def test_attachment_metadata_is_not_a_safe_audit_snapshot(self):
        for kind in ("parent", "leaf"):
            for value in ({}, {"file.bin":{"stub":True}}):
                parents=[parent(["h:+kept"])]
                leaves=[leaf("h:+kept")]
                (parents[0] if kind=="parent" else leaves[0])["_attachments"]=value
                with self.subTest(kind=kind,value=value), self.assertRaisesRegex(
                        UnsafeWrite,"attachments_not_supported"):
                    audit(parents,leaves)

    def test_duplicate_or_corrupt_documents_fail_closed(self):
        cases=[
            ([parent(["h:+same"]),parent(["h:+same"])],[leaf("h:+same")]),
            ([parent(["h:+good"])],[leaf("h:+good"),leaf("h:+good")]),
            ([parent(["bad-reference"])],[leaf("h:+good")]),
            ([dict(parent(["h:+good"]),_conflicts=["2-"+"a"*32])],[leaf("h:+good")]),
            ([parent(["h:+good"])],[dict(leaf("h:+good"),_deleted=True)]),
            ([{"_id":"f:note","type":"unexpected","children":["h:+good"]}],
             [leaf("h:+good")]),
        ]
        for parents,leaves in cases:
            with self.subTest(parents=parents,leaves=leaves), self.assertRaises(UnsafeWrite):
                audit(parents,leaves)


if __name__=="__main__":
    unittest.main()
