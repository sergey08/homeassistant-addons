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

if __name__ == "__main__":
    unittest.main()
