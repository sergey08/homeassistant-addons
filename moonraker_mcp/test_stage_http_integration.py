"""HTTP end-to-end staging and simulated upload. Never contacts a printer."""
import base64
import hashlib
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch
from http.server import ThreadingHTTPServer

from gateway import Handler, STAGE_CHUNK_TOOL, RESERVED_UPLOAD_TOOL
from moonraker_chunk_staging import stage_chunk
from moonraker_staging import read_staged_gcode


class StagingHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.root.chmod(0o700)
        self.data = b"; Snapmaker U1 test\nG28\nM84\n"
        self.digest = hashlib.sha256(self.data).hexdigest()
        self.old_allowed, self.old_token = Handler.allowed, Handler.token
        Handler.allowed = frozenset({STAGE_CHUNK_TOOL, RESERVED_UPLOAD_TOOL})
        Handler.token = "offline-test"
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.cleanup_server)

    def cleanup_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        Handler.allowed, Handler.token = self.old_allowed, self.old_token

    def call(self, name, args):
        message = {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                   "params": {"name": name, "arguments": args}}
        req = urllib.request.Request(
            "http://127.0.0.1:%s/mcp" % self.server.server_port,
            data=json.dumps(message).encode(),
            headers={"Authorization": "Bearer offline-test",
                     "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read())

    def test_staging_then_simulated_upload_never_starts_print(self):
        calls = []
        def fake_upload(url, filename, content, digest, api_key):
            calls.append((filename, content, digest))
            return {"uploaded": True, "print_requested": False}
        def stage_local(filename, digest, offset, chunk, final):
            return stage_chunk(filename, digest, offset, chunk, final, self.root)
        def read_local(filename, digest):
            return read_staged_gcode(filename, digest, self.root)
        with patch("gateway.stage_chunk", side_effect=stage_local), \\
             patch("gateway.read_staged_gcode", side_effect=read_local), \\
             patch("gateway.upload_gcode", side_effect=fake_upload), \\
             patch.dict("os.environ", {"MOONRAKER_URL": "http://127.0.0.1:7125", "MOONRAKER_API_KEY": ""}):
            for offset, chunk, final in [(0, self.data[:10], False),
                                         (10, self.data[10:], True)]:
                status, result = self.call(STAGE_CHUNK_TOOL, {
                    "filename": "sample.gcode", "sha256": self.digest,
                    "offset": offset, "chunk_b64": base64.b64encode(chunk).decode(),
                    "final": final, "confirmation": "CONFIRM_STAGE"})
                self.assertEqual(status, 200)
                self.assertFalse(result["result"]["isError"])
                self.assertEqual(json.loads(result["result"]["content"][0]["text"])["complete"], final)
            self.assertEqual(calls, [])
            status, result = self.call(RESERVED_UPLOAD_TOOL, {
                "filename": "sample.gcode", "sha256": self.digest,
                "confirmation": "CONFIRM_UPLOAD"})
            self.assertEqual(status, 200)
            self.assertFalse(result["result"]["isError"])
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0], ("sample.gcode", self.data, self.digest))
            self.assertFalse(json.loads(result["result"]["content"][0]["text"])["print_requested"])

    def test_invalid_confirmation_cannot_stage(self):
        status, result = self.call(STAGE_CHUNK_TOOL, {
            "filename": "sample.gcode", "sha256": self.digest, "offset": 0,
            "chunk_b64": base64.b64encode(self.data).decode(), "final": True,
            "confirmation": "CONFIRM_UPLOAD"})
        self.assertNotEqual(status, 200)
        self.assertEqual(list(self.root.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
