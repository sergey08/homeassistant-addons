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
