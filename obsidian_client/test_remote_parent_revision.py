"""Safety tests: encrypted parent revision endpoint stays read-only."""
import unittest
from unittest.mock import patch
from server import app

class TestRemoteParentRevision(unittest.TestCase):
    def setUp(self):
        self.client=app.test_client()
    def test_invalid_path(self):
        response=self.client.get("/api/remote/parent-revision?path=../unsafe.md")
        self.assertEqual(response.status_code,400)
    def test_missing_configuration(self):
        with patch("server.options",return_value={}):
            response=self.client.get("/api/remote/parent-revision?path=Notes/Test.md")
        self.assertEqual(response.status_code,409)
        self.assertEqual(response.json["error"],"encryption_not_configured")
    def test_rejects_untrusted_endpoint(self):
        cfg={"livesync_encryption_enabled":True,
             "livesync_e2ee_passphrase":"synthetic-fixture",
             "couchdb_url":"http://untrusted.example:5984",
             "couchdb_database":"disposable"}
        with patch("server.options",return_value=cfg):
            response=self.client.get("/api/remote/parent-revision?path=Notes/Test.md")
        self.assertEqual(response.status_code,403)
        self.assertEqual(response.json["error"],"unsupported_connection")

if __name__=="__main__":
    unittest.main()
