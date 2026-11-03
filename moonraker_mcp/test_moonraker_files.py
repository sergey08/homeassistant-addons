"""Unit tests with fake Moonraker HTTP responses; no printer access."""
import io
import json
import unittest
import urllib.request
import urllib.error
from moonraker_files import _NoRedirect, FileAccessError, validate_filename, validate_root, list_gcodes, gcode_metadata


class FakeResponse:
    def __init__(self, data):
        self.stream = io.BytesIO(json.dumps({"result": data}).encode())

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size):
        return self.stream.read(size)


class FileApiTests(unittest.TestCase):
    def test_roots_are_restricted(self):
        self.assertEqual(validate_root("gcodes"), "gcodes")
        for root in ("config", "logs", "../gcodes", ""):
            with self.assertRaises(FileAccessError):
                validate_root(root)

    def test_reject_unsafe_filenames(self):
        for name in ("../printer.cfg", "/etc/passwd", "dir/../x.gcode", "dir//x.gcode",
                     "dir/./x.gcode", "x\\y", "", "a\x00b", "a\nb"):
            with self.subTest(name=name), self.assertRaises(FileAccessError):
                validate_filename(name)
        self.assertEqual(validate_filename("parts/benchy.gcode"), "parts/benchy.gcode")

    def test_list_is_get_and_gcode_root_only(self):
        calls = []
        def fake(req, timeout):
            calls.append((req.full_url, req.get_method(), req.get_header("X-api-key")))
            return FakeResponse([{"path": "benchy.gcode"}])
        result = list_gcodes("http://printer.local:7125", "secret", fake)
        self.assertEqual(result[0]["path"], "benchy.gcode")
        self.assertIn("/server/files/list?root=gcodes", calls[0][0])
        self.assertEqual(calls[0][1], "GET")
        self.assertEqual(calls[0][2], "secret")

    def test_metadata_escapes_filename(self):
        calls = []
        def fake(req, timeout):
            calls.append(req.full_url)
            return FakeResponse({"size": 123})
        self.assertEqual(gcode_metadata("http://printer.local:7125", "my parts/a & b.gcode", opener=fake)["size"], 123)
        self.assertIn("filename=my+parts%2Fa+%26+b.gcode", calls[0])

    def test_redirects_are_blocked_to_protect_api_key(self):
        req = urllib.request.Request("http://printer.local:7125/server/files/list",
                                     headers={"X-Api-Key": "secret"})
        with self.assertRaises(FileAccessError):
            _NoRedirect().redirect_request(req, None, 302, "Found",
                                           {"Location": "https://untrusted.example/"},
                                           "https://untrusted.example/")

    def test_invalid_json_is_rejected(self):
        class BrokenResponse:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, size): return b"not json"
        with self.assertRaises(FileAccessError):
            list_gcodes("http://printer.local:7125", opener=lambda req, timeout: BrokenResponse())

    def test_reject_oversized_reply(self):
        def fake(req, timeout):
            return FakeResponse("x" * (1024 * 1024))
        with self.assertRaises(FileAccessError):
            list_gcodes("http://printer.local:7125", opener=fake)


if __name__ == "__main__":
    unittest.main()
