"""Read-only editor preview: never writes remotely."""
import unittest
from unittest.mock import patch
from server import app

class TestRemoteWritePreview(unittest.TestCase):
    def setUp(self):
        self.client=app.test_client()
        self.headers={"Content-Type":"application/json",
                      "X-Obsidian-Client-Action":"write-preview"}
    def post(self, payload, headers=None):
        return self.client.post("/api/remote/write-preview",
                                json=payload,headers=headers or self.headers)
    def test_valid_preview_is_read_only(self):
        with patch("server.read_encrypted_note",return_value=("before",None)) as read, \\
             patch("server.remote_parent_revision") as inspect:
            from flask import jsonify
            inspect.side_effect=lambda path: jsonify(
                revision_available=True,encrypted_parent=True,write_supported=False)
            result=self.post({"path":"Notes/Test.md","content":"after",
                              "expected_content":"before"})
        self.assertEqual(result.status_code,200)
        self.assertEqual(result.json["status"],"preview_only")
        self.assertFalse(result.json["remote_write_enabled"])
        self.assertFalse(result.json["save_supported"])
        self.assertTrue(result.json["revision_verified"])\n        inspect.assert_called_once_with("Notes/Test.md")
        read.assert_called_once_with("Notes/Test.md")
    def test_rejects_remote_content_conflict(self):
        with patch("server.read_encrypted_note",return_value=("changed elsewhere",None)):
            result=self.post({"path":"Notes/Test.md","content":"after",
                              "expected_content":"before"})
        self.assertEqual(result.status_code,409)
        self.assertEqual(result.json["error"],"remote_content_conflict")
    def test_rejects_missing_header(self):
        result=self.post({"path":"Test.md","content":"new",
                          "expected_content":"old"},headers={"Content-Type":"application/json"})
        self.assertEqual(result.status_code,403)
    def test_rejects_invalid_path_before_read(self):
        with patch("server.read_encrypted_note") as read:
            result=self.post({"path":"../bad.md","content":"new",
                              "expected_content":"old"})
        self.assertEqual(result.status_code,400)
        read.assert_not_called()

if __name__=="__main__":
    unittest.main()
