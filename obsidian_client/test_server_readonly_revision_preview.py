"""Read-only editor preview must verify content and revision in one request."""
import unittest
from unittest.mock import patch
from flask import jsonify
import server

HEADERS={"X-Obsidian-Client-Action":"write-preview","Content-Type":"application/json"}
BODY={"path":"Notes/example.md","expected_content":"# Original\\n",
      "content":"# Modified\\n"}

class RemotePreviewRevisionTests(unittest.TestCase):
    def setUp(self):
        self.client=server.app.test_client()

    def test_verified_preview_remains_read_only(self):
        with patch.object(server,"read_encrypted_note",
                          return_value=("# Original\\n",None)),patch.object(
                server,"remote_parent_revision") as inspect:
            inspect.side_effect=lambda path: jsonify(
                revision_available=True,encrypted_parent=True,
                write_supported=False)
            r=self.client.post("/api/remote/write-preview",
                               json=BODY,headers=HEADERS)
            self.assertEqual(r.status_code,200)
            self.assertTrue(r.json["revision_verified"])
            self.assertTrue(r.json["content_changed"])
            self.assertFalse(r.json["save_supported"])
            self.assertFalse(r.json["remote_write_enabled"])
            self.assertEqual(r.headers["Cache-Control"],"no-store")
            inspect.assert_called_once_with(BODY["path"])

    def test_changed_remote_content_rejects_before_revision_lookup(self):
        with patch.object(server,"read_encrypted_note",
                          return_value=("# Changed elsewhere\\n",None)),patch.object(
                server,"remote_parent_revision") as inspect:
            r=self.client.post("/api/remote/write-preview",
                               json=BODY,headers=HEADERS)
            self.assertEqual(r.status_code,409)
            self.assertEqual(r.json["error"],"remote_content_conflict")
            inspect.assert_not_called()

    def test_revision_failure_blocks_preview(self):
        with patch.object(server,"read_encrypted_note",
                          return_value=("# Original\\n",None)),patch.object(
                server,"remote_parent_revision") as inspect:
            inspect.side_effect=lambda path: (
                jsonify(error="missing_or_ambiguous_parent",write_supported=False),409)
            r=self.client.post("/api/remote/write-preview",
                               json=BODY,headers=HEADERS)
            self.assertEqual(r.status_code,409)
            self.assertFalse(r.json["save_supported"])
            self.assertEqual(r.json["error"],"remote_revision_not_verified")

    def test_revision_missing_blocks_preview(self):
        with patch.object(server,"read_encrypted_note",
                          return_value=("# Original\\n",None)),patch.object(
                server,"remote_parent_revision") as inspect:
            inspect.side_effect=lambda path: jsonify(
                revision_available=False,encrypted_parent=True,
                write_supported=False)
            r=self.client.post("/api/remote/write-preview",
                               json=BODY,headers=HEADERS)
            self.assertEqual(r.status_code,409)

    def test_cross_origin_header_rejected(self):
        r=self.client.post("/api/remote/write-preview",json=BODY,
             headers={**HEADERS,"Origin":"https://untrusted.example"})
        self.assertEqual(r.status_code,403)

if __name__=="__main__":
    unittest.main()
