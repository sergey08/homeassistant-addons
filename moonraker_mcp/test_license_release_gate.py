"""Offline tests of exact-SBOM stable attribution gate."""
import copy
import unittest
from license_release_gate import assess, canonical_sbom_sha256


class LicenseReleaseGateTests(unittest.TestCase):
    def setUp(self):
        self.sbom = {"bomFormat": "CycloneDX", "specVersion": "1.6",
                     "components": [{"bom-ref": "pkg:golang/example@v1.0.0",
                                     "name": "example", "version": "v1.0.0"},
                                    {"bom-ref": "pkg:apk/alpine/base@3.22",
                                     "name": "base", "version": "3.22"}]}
        self.manifest = {"sbom_sha256": canonical_sbom_sha256(self.sbom),
                         "reviews": [
                             {"bom_ref": c["bom-ref"], "status": "REVIEWED",
                              "license_evidence": "verified upstream LICENSE at fixed revision",
                              "notice_obligations": "manually evaluated; retain required notices",
                              "reviewer": "test-reviewer"}
                             for c in self.sbom["components"]]}

    def test_complete_documentation_not_legal_approval(self):
        ok, issues = assess(self.sbom, self.manifest)
        self.assertTrue(ok)
        self.assertEqual(issues, [])

    def test_unreviewed_or_unknown_component_blocks(self):
        for field, value in (("status", "PENDING"), ("reviewer", ""),
                             ("notice_obligations", ""), ("license_evidence", "")):
            m = copy.deepcopy(self.manifest)
            m["reviews"][0][field] = value
            with self.subTest(field=field):
                self.assertFalse(assess(self.sbom, m)[0])
        m = copy.deepcopy(self.manifest)
        m["reviews"].pop()
        self.assertFalse(assess(self.sbom, m)[0])

    def test_stale_sbom_and_duplicate_reviews_rejected(self):
        sbom = copy.deepcopy(self.sbom)
        sbom["components"][0]["version"] = "v2.0.0"
        self.assertFalse(assess(sbom, self.manifest)[0])
        m = copy.deepcopy(self.manifest)
        m["reviews"].append(copy.deepcopy(m["reviews"][0]))
        with self.assertRaises(ValueError):
            assess(self.sbom, m)

    def test_unknown_component_not_silently_ignored(self):
        m = copy.deepcopy(self.manifest)
        m["reviews"].append({"bom_ref": "unknown", "status": "REVIEWED",
                             "license_evidence": "x", "notice_obligations": "x",
                             "reviewer": "x"})
        self.assertFalse(assess(self.sbom, m)[0])

    def test_invalid_component_references_fail_closed(self):
        sbom = copy.deepcopy(self.sbom)
        sbom["components"][1]["bom-ref"] = sbom["components"][0]["bom-ref"]
        with self.assertRaises(ValueError):
            assess(sbom, self.manifest)


if __name__ == "__main__":
    unittest.main()
