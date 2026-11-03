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
            inspect.assert_not_called()

    def test_changed_remote_content_rejects_before_revision_lookup(self):
        with patch.object(server,"read_encrypted_note",
                          return_value=("# Changed elsewhere\\n",None)),patch.object(
                server,"remote_parent_revision") as inspect:
            r=self.client.post("/api/remote/write-preview",
                               json=BODY,headers=HEADERS)
            self.assertEqual(r.status_code,409)
            self.assertEqual(r.json["error"],"remote_content_conflict")
            inspect.assert_not_called()

    def test_inconsistent_remote_snapshot_blocks_preview(self):
        with patch.object(server,"read_encrypted_note",
                          return_value=(None,"remote_revision_changed")) as reader:
            r=self.client.post("/api/remote/write-preview",
                               json=BODY,headers=HEADERS)
            self.assertEqual(r.status_code,409)
            self.assertFalse(r.json["save_supported"])
            self.assertEqual(r.json["error"],"remote_snapshot_not_verified")
            reader.assert_called_once_with(BODY["path"],verify_revision=True)

    def test_ambiguous_parent_blocks_preview(self):
        with patch.object(server,"read_encrypted_note",
                          return_value=(None,"ambiguous_parent")):
            r=self.client.post("/api/remote/write-preview",
                               json=BODY,headers=HEADERS)
            self.assertEqual(r.status_code,409)

    def test_revision_verification_failure_modes_fail_closed(self):
        # The reader owns parent/chunk consistency; preview must never authorize
        # saving if that verification reports an unsafe remote snapshot.
        for reason in ("remote_revision_changed", "ambiguous_parent",
                       "invalid_parent_snapshot", "read_failed",
                       "not_found", "size_mismatch"):
            with self.subTest(reason=reason):
                with patch.object(server, "read_encrypted_note",
                                  return_value=(None, reason)) as reader:
                    r = self.client.post("/api/remote/write-preview",
                                         json=BODY, headers=HEADERS)
                self.assertEqual(r.status_code, 409)
                self.assertEqual(r.json["error"], "remote_snapshot_not_verified")
                self.assertFalse(r.json["save_supported"])
                self.assertFalse(r.json["remote_write_enabled"])
                reader.assert_called_once_with(BODY["path"], verify_revision=True)

    def test_malformed_second_parent_fetch_is_rejected(self):
        import io
        import json
        from unittest.mock import Mock
        parent = {"_id": "f:opaque", "_rev": "1-original",
                  "type": "plain", "path": "/\\:%=ciphertext"}
        responses = [
            {"pbkdf2salt": "salt"},
            {"rows": [{"doc": parent}]},
            {"type": "leaf", "data": "%=ciphertext"},
            ["not", "a", "document"],
        ]
        opener = Mock()
        opener.open.side_effect = [
            io.BytesIO(json.dumps(value).encode()) for value in responses
        ]
        cfg = {"livesync_encryption_enabled": True,
               "livesync_e2ee_passphrase": "test-secret",
               "couchdb_url": "http://db21ed7f-obsidian-syncserver-ssl:5984",
               "couchdb_database": "test"}
        decrypted = [json.dumps({"path": BODY["path"], "size": 4}), "body"]
        with (patch.object(server, "options", return_value=cfg),
              patch.object(server, "build_opener", return_value=opener),
              patch("livesync_crypto.decrypt_hkdf_string", side_effect=decrypted),
              patch("livesync_metadata.validate_encrypted_parent", return_value=["h:chunk"]),
              patch("livesync_encrypted_parent_snapshot.validate_encrypted_parent_snapshot")):
            content, error = server.read_encrypted_note(BODY["path"], verify_revision=True)
        self.assertIsNone(content)
        self.assertEqual(error, "remote_revision_changed")
        self.assertEqual(opener.open.call_count, 4)

    def test_cross_origin_header_rejected(self):
        r=self.client.post("/api/remote/write-preview",json=BODY,
             headers={**HEADERS,"Origin":"https://untrusted.example"})
        self.assertEqual(r.status_code,403)

if __name__=="__main__":
    unittest.main()
