"""Offline tests for non-approved CycloneDX review worksheet."""
import csv
import json
import tempfile
from pathlib import Path
import unittest

from license_review_worksheet import make_worksheet, write_worksheet
from license_release_gate import assess, canonical_sbom_sha256


class WorksheetTests(unittest.TestCase):
    def setUp(self):
        self.sbom = {"bomFormat": "CycloneDX", "specVersion": "1.6",
                     "components": [
                         {"bom-ref": "go", "name": "example", "version": "v1.2.0",
                          "purl": "pkg:golang/example@v1.2.0"},
                         {"bom-ref": "apk", "name": "busybox", "version": "1.37.0",
                          "licenses": [{"license": {"id": "GPL-2.0-only"}}]},
                     ]}

    def test_every_entry_is_pending_even_when_scanner_detected_license(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            pending = write_worksheet(self.sbom, base)
            self.assertEqual(len(pending["reviews"]), 2)
            self.assertEqual(pending["sbom_sha256"], canonical_sbom_sha256(self.sbom))
            self.assertTrue(all(entry["status"] == "PENDING" for entry in pending["reviews"]))
            self.assertFalse(assess(self.sbom, pending)[0])
            csvrows = list(csv.DictReader(
                (base / "license-human-review-worksheet.csv").open(encoding="utf-8")))
            self.assertEqual(len(csvrows), 2)
            self.assertTrue(all(not row["reviewer"] for row in csvrows))
            self.assertTrue(any("GPL-2.0-only" in row["detected_license_metadata"]
                                for row in csvrows))
            self.assertEqual(json.loads(
                (base / "license-review-pending.json").read_text())["purpose"],
                "WORKSHEET_ONLY_NOT_APPROVED")

    def test_reject_duplicate_and_missing_refs(self):
        sbom = json.loads(json.dumps(self.sbom))
        sbom["components"][1]["bom-ref"] = "go"
        with self.assertRaises(ValueError):
            make_worksheet(sbom)
        sbom["components"][1].pop("bom-ref")
        with self.assertRaises(ValueError):
            make_worksheet(sbom)

    def test_reject_invalid_scanner_license_metadata(self):
        self.sbom["components"][0]["licenses"] = "MIT"
        with self.assertRaises(ValueError):
            make_worksheet(self.sbom)


if __name__ == "__main__":
    unittest.main()
