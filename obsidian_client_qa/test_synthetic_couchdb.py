"""Synthetic CouchDB read-only integration test / Prueba aislada de CouchDB.

Uses a loopback HTTP server and invented note data. No real vault, credentials
or external network connections are involved.
"""
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import urlopen

from livesync_plain import decode_plain_note


PARENT = {"_id": "f:demo", "type": "plain", "path": "Demo/Hello.md",
          "children": ["h:one", "h:two"], "size": 11}
CHUNKS = {
    "h:one": {"_id": "h:one", "type": "leaf", "data": "Hello "},
    "h:two": {"_id": "h:two", "type": "leaf", "data": "world"},
}


class FakeCouchDB(BaseHTTPRequestHandler):
    requests_seen = []

    def do_GET(self):
        self.requests_seen.append(("GET", self.path))
        if self.path == "/synthetic/_all_docs?include_docs=true":
            payload = {"rows": [{"id": "f:demo", "doc": PARENT}] +
                       [{"id": key, "doc": doc} for key, doc in CHUNKS.items()]}
            self.send_response(200)
        else:
            payload = {"error": "not_found"}
            self.send_response(404)
        encoded = json.dumps(payload).encode("utf-8")
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_POST(self):
        self.send_error(405)

    def do_PUT(self):
        self.send_error(405)

    def do_DELETE(self):
        self.send_error(405)

    def log_message(self, *_args):
        pass


class SyntheticCouchDBTest(unittest.TestCase):
    def test_readonly_end_to_end_note_reassembly(self):
        FakeCouchDB.requests_seen = []
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), FakeCouchDB)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            url = "http://127.0.0.1:%s/synthetic/_all_docs?include_docs=true" % httpd.server_port
            with urlopen(url, timeout=3) as response:
                rows = json.load(response)["rows"]
            docs = {row["id"]: row["doc"] for row in rows}
            note = decode_plain_note(docs["f:demo"], docs)
            self.assertEqual(note, {"path": "Demo/Hello.md", "content": "Hello world"})
            self.assertEqual(FakeCouchDB.requests_seen,
                             [("GET", "/synthetic/_all_docs?include_docs=true")])
        finally:
            httpd.shutdown()
            httpd.server_close()
            thread.join(timeout=3)


if __name__ == "__main__":
    unittest.main()
