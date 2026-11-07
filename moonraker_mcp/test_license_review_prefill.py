"""Tests that evidence hints never become license approvals."""
import unittest
from license_review_prefill import reconcile


class ReviewHintsTests(unittest.TestCase):
    def setUp(self):
        self.pending = {
            "purpose": "WORKSHEET_ONLY_NOT_APPROVED",
            "sbom_sha256": "test-sha",
            "reviews": [
                {"bom_ref": "pkg:golang/example.org/mod@v1.2.3", "status": "PENDING"},
                {"bom_ref": "pkg:apk/alpine/alpine-baselayout@3.7.0-r0?arch=x86_64", "status": "PENDING"},
                {"bom_ref": "urn:cdx:some-unidentified-file", "status": "PENDING"}
            ]
        }

    def test_exact_evidence_with_all_items_pending(self):
        go = [{"bom_ref": "pkg:golang/example.org/mod@v1.2.3",
               "source_status": "SOURCE_LICENSE_FILES_FOUND", "license_file": "LICENSE",
               "license_sha256": "abcd"}]
        apk = [{"package": "alpine-baselayout", "version": "3.7.0-r0",
                "license_expression": "GPL-2.0-only",
                "review_category": "COPYLEFT_OR_RECIPROCAL_REVIEW"}]
        evidence = reconcile(self.pending, go, apk)
        self.assertFalse(evidence["reviewer_approved"])
        self.assertEqual(evidence["purpose"], "EVIDENCE_HINTS_ONLY_NOT_LICENSE_APPROVAL")
        self.assertEqual(len(evidence["components"]), 3)
        self.assertTrue(all(c["status"] == "PENDING" and c["human_review_required"]
                            for c in evidence["components"]))
        self.assertEqual(len(evidence["components"][0]["go_source_files"]), 1)
        self.assertEqual(evidence["components"][1]["alpine_metadata"][0]["declared_expression"], "GPL-2.0-only")
        self.assertEqual(evidence["components"][2]["go_source_files"], [])

    def test_preapproved_or_duplicate_inputs_fail_closed(self):
        self.pending["reviews"][0]["status"] = "REVIEWED"
        with self.assertRaises(ValueError):
            reconcile(self.pending, [], [])
        self.pending["reviews"][0]["status"] = "PENDING"
        self.pending["reviews"].append(dict(self.pending["reviews"][0]))
        with self.assertRaises(ValueError):
            reconcile(self.pending, [], [])

    def test_unknown_purpose_rejected(self):
        self.pending["purpose"] = "APPROVED"
        with self.assertRaises(ValueError):
            reconcile(self.pending, [], [])


if __name__ == "__main__":
    unittest.main()
