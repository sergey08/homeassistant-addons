"""Tests: classify absent license metadata without assigning guessed licenses."""
import unittest
from sbom_license_queue import ecosystem, missing_licenses


class LicenseQueueTests(unittest.TestCase):
    def test_go_and_alpine_components_are_queued_without_guesses(self):
        source = [
            {"bom-ref": "go-1", "name": "golang.org/x/text", "version": "v0.41.0",
             "purl": "pkg:golang/golang.org/x/text@v0.41.0", "type": "library"},
            {"bom-ref": "apk-1", "name": "libcrypto3", "version": "3.5.0",
             "purl": "pkg:apk/alpine/libcrypto3@3.5.0", "type": "library", "licenses": []},
            {"bom-ref": "lic-1", "name": "documented", "type": "library",
             "licenses": [{"license": {"id": "Apache-2.0"}}]},
        ]
        queue = missing_licenses(source)
        self.assertEqual(len(queue), 2)
        self.assertEqual({row["ecosystem"] for row in queue}, {"golang", "apk"})
        self.assertTrue(all(row["review_status"] == "PENDING" for row in queue))
        self.assertTrue(all("license" not in row for row in queue))
        self.assertNotIn("documented", {row["name"] for row in queue})

    def test_malformed_component_rejected(self):
        for components in ([{"name": "no-ref"}],
                           [{"bom-ref": "a", "name": "first"},
                            {"bom-ref": "a", "name": "second"}],
                           [{"bom-ref": "a", "name": "pkg", "licenses": "MIT"}]):
            with self.subTest(components=components):
                with self.assertRaises(ValueError):
                    missing_licenses(components)

    def test_missing_purl_is_its_own_category(self):
        self.assertEqual(ecosystem({"name": "unknown"}), "no-purl")


if __name__ == "__main__":
    unittest.main()
