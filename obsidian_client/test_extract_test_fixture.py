"""Offline fixture extraction tests / Pruebas de extracción aislada."""
import unittest

from extract_test_fixture import make_fixture


def synthetic_export():
    return {"rows": [
        {"doc": {"_id": "f:demo", "type": "plain", "path": "Demo/Hello.md",
                 "children": ["h:first", "h:second"], "size": 11,
                 "private_field": "SHOULD_NOT_EXPORT"}},
        {"doc": {"_id": "h:first", "type": "leaf", "data": "Hello ",
                 "private_field": "SHOULD_NOT_EXPORT"}},
        {"doc": {"_id": "h:second", "type": "leaf", "data": "world"}},
        {"doc": {"_id": "f:other", "type": "plain", "path": "Other.md",
                 "data": "PRIVATE_OTHER_NOTE"}},
    ]}


class ExtractorTests(unittest.TestCase):
    def test_extracts_only_selected_note_and_chunks(self):
        fixture = make_fixture(synthetic_export(), "Demo/Hello.md", "Hello world")
        self.assertEqual(fixture["expected"]["content"], "Hello world")
        self.assertEqual(set(fixture["chunks"]), {"h:first", "h:second"})
        self.assertNotIn("SHOULD_NOT_EXPORT", str(fixture))
        self.assertNotIn("PRIVATE_OTHER_NOTE", str(fixture))

    def test_rejects_mismatched_content(self):
        with self.assertRaises(ValueError):
            make_fixture(synthetic_export(), "Demo/Hello.md", "different")

    def test_rejects_missing_referenced_chunk(self):
        export = synthetic_export()
        export["rows"] = [r for r in export["rows"] if r["doc"]["_id"] != "h:second"]
        with self.assertRaises(ValueError):
            make_fixture(export, "Demo/Hello.md", "Hello world")

    def test_rejects_duplicate_documents(self):
        export = synthetic_export()
        export["rows"].append(export["rows"][0])
        with self.assertRaises(ValueError):
            make_fixture(export, "Demo/Hello.md", "Hello world")


if __name__ == "__main__":
    unittest.main()
