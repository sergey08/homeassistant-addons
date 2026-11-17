"""Offline end-to-end staged upload with an in-process fake Moonraker HTTP server."""
import hashlib
import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from moonraker_staging import read_staged_gcode
from moonraker_upload import upload_gcode, UploadError


class FakeMoonraker(BaseHTTPRequestHandler):
    seen = []

    def do_POST(self):
        size = int(self.headers["Content-Length"])
        body = self.rfile.read(size)
        type_header = self.headers.get("Content-Type", "")
        FakeMoonraker.seen.append((self.path, body, type_header))
        # The fake deliberately does not emulate print/start or printer control.
        filename = "sample.gcode"
        payload = {"result": {"root": "gcodes", "item": {"path": filename}}}
        encoded = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, *args):
        pass


class UploadIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.payload = b"; Snapmaker U1\nG28\nG1 X10\n"
        self.digest = hashlib.sha256(self.payload).hexdigest()
        staged = self.dir / "sample.gcode"
        staged.write_bytes(self.payload)
        staged.chmod(0o600)
        FakeMoonraker.seen = []
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeMoonraker)
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.base = "http://127.0.0.1:%d" % self.server.server_address[1]

    def test_staged_file_uploaded_without_print(self):
        data = read_staged_gcode("sample.gcode", self.digest, self.dir)
        result = upload_gcode(self.base, "sample.gcode", data, self.digest)
        self.assertTrue(result["uploaded"])
        self.assertFalse(result["print_requested"])
        self.assertEqual(len(FakeMoonraker.seen), 1)
        path, body, mime = FakeMoonraker.seen[0]
        self.assertEqual(path, "/server/files/upload")
        self.assertIn(b'name="print"\r\n\r\nfalse\r\n', body)
        self.assertIn(b'name="root"\r\n\r\ngcodes\r\n', body)
        self.assertIn(self.payload, body)
        self.assertIn("multipart/form-data", mime)

    def test_hash_mismatch_never_contacts_printer(self):
        with self.assertRaises(UploadError):
            read_staged_gcode("sample.gcode", "0" * 64, self.dir)
        self.assertEqual(FakeMoonraker.seen, [])


if __name__ == "__main__":
    unittest.main()
