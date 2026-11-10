"""Offline tests for Alpine installed-package license triage."""
import tempfile
from pathlib import Path
import unittest
from alpine_license_review import read_records, classify, report


class AlpineLicenseReviewTests(unittest.TestCase):
    def test_installed_apkv2_fields_and_triage(self):
        sample="P:busybox\nV:1.37.0-r0\nL:GPL-2.0-only\nP:ca-certificates\nV:2025-r0\nL:MPL-2.0\nP:libfoo\nV:1.2.3-r1\nL:MIT\n"
        rows=read_records(sample)
        self.assertEqual(len(rows),3)
        self.assertEqual(classify(rows[0]["license_expression"]),"COPYLEFT_OR_RECIPROCAL_REVIEW")
        self.assertEqual(classify(rows[1]["license_expression"]),"COPYLEFT_OR_RECIPROCAL_REVIEW")
        self.assertEqual(classify(rows[2]["license_expression"]),"STANDARD_PERMISSIVE_CANDIDATE")
        with tempfile.TemporaryDirectory() as d:
            summary=report(rows,Path(d))
            self.assertEqual(summary["installed_packages"],3)
            self.assertFalse(summary["release_clearance"])
            self.assertTrue((Path(d)/"alpine-license-review.csv").is_file())
            self.assertTrue((Path(d)/"alpine-license-review-summary.json").is_file())

    def test_compound_and_unknown_are_not_automatically_cleared(self):
        self.assertEqual(classify("MIT AND GPL-3.0-or-later"),"COPYLEFT_OR_RECIPROCAL_REVIEW")
        self.assertEqual(classify("custom-proprietary"),"OTHER_OR_COMPOUND_REVIEW")
        self.assertEqual(classify(""),"UNKNOWN")
        self.assertEqual(classify("MIT OR Apache-2.0"),"STANDARD_PERMISSIVE_CANDIDATE")

    def test_fail_closed_for_truncated_and_duplicate_records(self):
        for sample in ("", "P:partial\nV:1\n",
                       "P:a\nV:1\nL:MIT\nP:a\nV:1\nL:MIT\n",
                       "P:a\nL:MIT\nP:b\nV:1\nL:MIT\n",
                       "garbage\n"):
            with self.subTest(sample=sample):
                with self.assertRaises(ValueError):
                    read_records(sample)


if __name__=="__main__":
    unittest.main()
