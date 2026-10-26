"""Real CouchDB integration / Integración real con CouchDB.

Runs ONLY when TEST_COUCHDB_URL is set. Creates and deletes a uniquely
named disposable database on the test server. Never use production credentials.
"""
import base64
import json
import os
import unittest
import uuid
from unittest.mock import patch
from server import app
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

from livesync_plain import decode_plain_note


@unittest.skipUnless(os.environ.get("TEST_COUCHDB_URL"), "Isolated CouchDB not configured")
class RealCouchDBIntegrationTests(unittest.TestCase):
    def test_disposable_database_roundtrip(self):
        root = os.environ["TEST_COUCHDB_URL"].rstrip("/")
        if root not in ("http://127.0.0.1:5984", "http://localhost:5984"):
            self.fail("Safety: disposable test database only permitted on loopback CouchDB:5984")
        username = os.environ.get("TEST_COUCHDB_USER", "")
        password = os.environ.get("TEST_COUCHDB_PASSWORD", "")
        if not username or not password:
            self.fail("Safety: test-only admin credentials required")
        auth = "Basic " + base64.b64encode(f"{username}:{password}".encode()).decode()
        db = "obsidian_ci_" + uuid.uuid4().hex
        base = root + "/" + db
        def call(url, method="GET", payload=None):
            body = json.dumps(payload).encode() if payload is not None else None
            req = Request(url, data=body, method=method,
                          headers={"Authorization": auth, "Content-Type": "application/json"})
            with urlopen(req, timeout=8) as resp:
                return json.load(resp)

        created = False
        try:
            result = call(base, "PUT")
            self.assertTrue(result.get("ok"))
            created = True
            config = {
                "livesync_cli_enabled": True,
                "couchdb_url": root,
                "couchdb_database": db,
                "couchdb_username": username,
                "couchdb_password": password,
                "livesync_encryption_enabled": True,
                "livesync_e2ee_passphrase": "isolated-ci-only",
            }
            with patch("server.options", return_value=config):
                response = app.test_client().get("/api/livesync-cli/connection-check")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json["status"], "database_reachable")
            self.assertFalse(response.json["encryption_verified"])
            self.assertFalse(response.json["remote_writes_enabled"])
            config["couchdb_password"] = "incorrect-test-password"
            with patch("server.options", return_value=config):
                rejected = app.test_client().get("/api/livesync-cli/connection-check")
            self.assertEqual(rejected.status_code, 502)
            self.assertEqual(rejected.json["status"], "authentication_failed")
            parent = {"_id": "f:synthetic", "type": "plain", "path": "Tests/Hello.md",
                      "children": ["h:first", "h:second"], "size": 11}
            chunks = [
                {"_id": "h:first", "type": "leaf", "data": "Hello "},
                {"_id": "h:second", "type": "leaf", "data": "world"},
            ]
            for doc in [parent] + chunks:
                self.assertTrue(call(base + "/" + quote(doc["_id"], safe=""), "PUT", doc).get("ok"))
            rows = call(base + "/_all_docs?include_docs=true")["rows"]
            docs = {row["id"]: row["doc"] for row in rows}
            self.assertEqual(decode_plain_note(docs["f:synthetic"], docs),
                             {"path": "Tests/Hello.md", "content": "Hello world"})
        finally:
            if created:
                self.assertTrue(call(base, "DELETE").get("ok"))


if __name__ == "__main__":
    unittest.main()
