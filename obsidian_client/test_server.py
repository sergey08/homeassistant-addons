"""Offline security and behavior tests; no live CouchDB needed."""
import json
import unittest
from unittest.mock import patch
import server

class ClientTests(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()

    def test_unconfigured_connection(self):
        with patch.object(server, "options", return_value={}):
            response = self.client.get("/api/connection")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["status"], "not_configured")

    def test_rejects_credentials_over_http(self):
        options = {"couchdb_url": "http://localhost:5984", "couchdb_database": "test",
                   "couchdb_username": "user", "couchdb_password": "secret"}
        with patch.object(server, "options", return_value=options):
            response = self.client.get("/api/connection")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["status"], "https_required")

    def test_rejects_embedded_credentials(self):
        options = {"couchdb_url": "https://user:secret@example.org",
                   "couchdb_database": "test"}
        with patch.object(server, "options", return_value=options):
            response = self.client.get("/api/connection")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["status"], "invalid_url")

    def test_rejects_nonroot_url(self):
        options = {"couchdb_url": "https://example.org/proxy",
                   "couchdb_database": "test"}
        with patch.object(server, "options", return_value=options):
            response = self.client.get("/api/connection")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["status"], "invalid_url_path")

    def test_rejects_bad_database_name(self):
        options = {"couchdb_url": "https://example.org",
                   "couchdb_database": "../private"}
        with patch.object(server, "options", return_value=options):
            response = self.client.get("/api/connection")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["status"], "invalid_database")


    def test_connection_reads_only_database_metadata(self):
        from unittest.mock import MagicMock
        opts = {"couchdb_url": "https://example.org", "couchdb_database": "sandbox"}
        response_obj = MagicMock()
        response_obj.__enter__.return_value = response_obj
        response_obj.read.return_value = b'{"doc_count":3}'
        with patch.object(server, "options", return_value=opts), \
             patch.object(server, "build_opener") as factory:
            factory.return_value.open.return_value = response_obj
            result = self.client.get("/api/connection")
            req = factory.return_value.open.call_args.args[0]
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json["document_count"], 3)
        self.assertEqual(req.get_method(), "GET")
        self.assertEqual(req.full_url, "https://example.org/sandbox")

    def test_connection_failure_hides_internal_error(self):
        opts = {"couchdb_url": "https://example.org", "couchdb_database": "sandbox"}
        with patch.object(server, "options", return_value=opts), \
             patch.object(server, "build_opener") as factory:
            factory.return_value.open.side_effect = RuntimeError("private secret")
            result = self.client.get("/api/connection")
        self.assertEqual(result.status_code, 502)
        self.assertNotIn("private secret", result.get_data(as_text=True))


    def test_local_note_preview_is_read_only(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "sample.md").write_text("# Test note", encoding="utf-8")
            with patch.object(server, "vault_dir", return_value=root):
                response = self.client.get("/?path=sample.md")
            self.assertEqual(response.status_code, 200)
            self.assertIn("Test note", response.get_data(as_text=True))
            self.assertEqual((root / "sample.md").read_text(), "# Test note")

    def test_local_note_rejects_parent_traversal(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(server, "vault_dir", return_value=root):
                response = self.client.get("/?path=../secret.md")
            self.assertEqual(response.status_code, 404)

    def test_local_note_rejects_non_markdown(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "private.txt").write_text("secret", encoding="utf-8")
            with patch.object(server, "vault_dir", return_value=root):
                response = self.client.get("/?path=private.txt")
            self.assertEqual(response.status_code, 404)


    def test_malformed_port_returns_clean_error(self):
        opts = {"couchdb_url": "https://example.org:not-a-port", "couchdb_database": "sandbox"}
        with patch.object(server, "options", return_value=opts):
            response = self.client.get("/api/connection")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["status"], "invalid_url")


    def test_notes_index_filters_and_excludes_hidden_files(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "Travel").mkdir()
            (root / "Travel" / "Trip.md").write_text("sample", encoding="utf-8")
            (root / ".hidden.md").write_text("hidden", encoding="utf-8")
            (root / "Other.md").write_text("other", encoding="utf-8")
            with patch.object(server, "vault_dir", return_value=root):
                result = self.client.get("/api/notes?q=trip")
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.json["notes"], ["Travel/Trip.md"])
            self.assertEqual(result.json["count"], 1)

    def test_notes_index_rejects_overlong_query(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            with patch.object(server, "vault_dir", return_value=Path(tmp)):
                result = self.client.get("/api/notes?q=" + "x" * 201)
            self.assertEqual(result.status_code, 400)


    def test_remote_inspect_unconfigured(self):
        with patch.object(server, "options", return_value={}):
            response = self.client.get("/api/remote/inspect")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["status"], "not_configured")

    def test_remote_inspect_rejects_http_credentials(self):
        opts = {"couchdb_url": "http://localhost:5984", "couchdb_database": "sandbox", "couchdb_username": "user"}
        with patch.object(server, "options", return_value=opts):
            response = self.client.get("/api/remote/inspect")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["status"], "https_required")

if __name__ == "__main__":
    unittest.main()
