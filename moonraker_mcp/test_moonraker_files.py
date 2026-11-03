"""Unit tests with fake Moonraker HTTP responses; no printer access."""
import io
import json
import unittest
import urllib.request
import urllib.error
from moonraker_files import _NoRedirect, FileAccessError, validate_filename, validate_root, validate_base_url, list_gcodes, gcode_metadata, gcode_preview


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
    def test_base_url_is_fixed_origin(self):
        self.assertEqual(validate_base_url("http://printer.local:7125/"), "http://printer.local:7125")
        for url in ("http://user:pass@printer.local:7125", "http://printer.local:7125/evil",
                    "http://printer.local:7125?key=secret", "http://printer.local:7125/#frag",
                    "file:///etc/passwd", "http://printer.local:invalid", "",
                    "http://printer.local:7125\\n", "http://printer.local:7125 ",
                    "http://printer.local%2F.evil:7125", "http://printer.local@evil.test",
                    "http://printer.local:7125\\t"):
            with self.subTest(url=url), self.assertRaises(FileAccessError):
                validate_base_url(url)

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

    def test_reject_encoded_path_traversal(self):
        for name in ("%2e%2e/secret.gcode", "dir%2fsecret.gcode",
                     "file%252fgcode", "parts/%2E%2E/secret.gcode"):
            with self.subTest(name=name), self.assertRaises(FileAccessError):
                validate_filename(name)

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

    def test_gcode_preview_only_and_bounded(self):
        class RawResponse:
            def __init__(self, payload): self.payload = payload
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, size): return self.payload[:size]
        calls = []
        def fake(req, timeout):
            calls.append((req.full_url, req.get_header("Range"), req.get_method()))
            return RawResponse(b"; sample\\nG1 X1\\n")
        result = gcode_preview("http://printer.local:7125", "parts/test.gcode", opener=fake)
        self.assertEqual(result["preview"], "; sample\\nG1 X1\\n")
        self.assertEqual(calls[0][1], "bytes=0-16383")
        self.assertEqual(calls[0][2], "GET")
        for name in ("printer.cfg", "../secret.gcode", "/tmp/test.gcode", "secret.txt"):
            with self.subTest(name=name), self.assertRaises(FileAccessError):
                gcode_preview("http://printer.local:7125", name, opener=fake)
        with self.assertRaises(FileAccessError):
            gcode_preview("http://printer.local:7125", "test.gcode",
                          opener=lambda req, timeout: RawResponse(b"x" * 16385))

    def test_preview_never_reads_beyond_limit(self):
        class BoundedResponse:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, size):
                self.requested = size
                return b"G1 X1\\n"
        response = BoundedResponse()
        result = gcode_preview("http://printer.local:7125", "part.gcode",
                               opener=lambda req, timeout: response)
        self.assertEqual(result["preview"], "G1 X1\\n")
        self.assertEqual(response.requested, 16385)

    def test_preview_rejects_binary_content(self):
        class BinaryResponse:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, size): return bytes((0, 1))
        with self.assertRaises(FileAccessError):
            gcode_preview("http://printer.local:7125", "part.gcode",
                          opener=lambda req, timeout: BinaryResponse())

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
