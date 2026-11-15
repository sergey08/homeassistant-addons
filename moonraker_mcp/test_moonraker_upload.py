import hashlib
import io
import json
import unittest

from moonraker_upload import UploadError, upload_gcode

class FakeResponse:
    def __init__(self, payload):
        self.stream = io.BytesIO(json.dumps(payload).encode())
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, size): return self.stream.read(size)

class UploadTests(unittest.TestCase):
    def setUp(self):
        self.data = b"; sliced for Snapmaker U1\nG28\n"
        self.digest = hashlib.sha256(self.data).hexdigest()

    def test_upload_does_not_start_print(self):
        requests = []
        def opener(request, timeout):
            requests.append(request)
            return FakeResponse({"result": {"root": "gcodes", "item": {"path": "test.gcode"}}})
        result = upload_gcode("http://printer.local:7125", "test.gcode", self.data, self.digest, opener=opener)
        self.assertTrue(result["uploaded"])
        self.assertFalse(result["print_requested"])
        self.assertEqual(requests[0].get_method(), "POST")
        self.assertTrue(requests[0].full_url.endswith("/server/files/upload"))
        self.assertIn(b'name="print"\r\n\r\nfalse', requests[0].data)

    def test_rejects_unsafe_multipart_filename(self):
        for filename in ('bad"name.gcode', 'bad;name.gcode'):
            with self.subTest(filename=filename), self.assertRaises(UploadError):
                upload_gcode("http://printer.local:7125", filename, self.data, self.digest)

    def test_rejects_binary_nul(self):
        data = b"; header\nG28\x00\n"
        with self.assertRaises(UploadError):
            upload_gcode("http://printer.local:7125", "test.gcode", data,
                         hashlib.sha256(data).hexdigest())

    def test_rejects_malformed_item_response(self):
        with self.assertRaises(UploadError):
            upload_gcode("http://printer.local:7125", "test.gcode", self.data,
                         self.digest, opener=lambda req, timeout: FakeResponse(
                             {"result": {"root": "gcodes", "item": None}}))

    def test_uses_randomized_multipart_boundary(self):
        requests = []
        def opener(req, timeout):
            requests.append(req)
            return FakeResponse({"result": {"root": "gcodes", "item": {"path": "test.gcode"}}})
        for _ in range(2):
            upload_gcode("http://printer.local:7125", "test.gcode",
                         self.data, self.digest, opener=opener)
        self.assertNotEqual(requests[0].get_header("Content-type"),
                            requests[1].get_header("Content-type"))

    def test_rejects_nul_after_header(self):
        data = b"; header\n" + b"G1 X1\n" * 1000 + b"\x00"
        with self.assertRaises(UploadError):
            upload_gcode("http://printer.local:7125", "test.gcode", data,
                         hashlib.sha256(data).hexdigest())

    def test_rejects_hash_mismatch(self):
        with self.assertRaises(UploadError):
            upload_gcode("http://printer.local:7125", "test.gcode", self.data, "0" * 64)

    def test_rejects_traversal(self):
        with self.assertRaises(UploadError):
            upload_gcode("http://printer.local:7125", "../test.gcode", self.data, self.digest)

    def test_rejects_wrong_extension(self):
        with self.assertRaises(UploadError):
            upload_gcode("http://printer.local:7125", "test.cfg", self.data, self.digest)

    def test_rejects_oversized_file(self):
        with self.assertRaises(UploadError):
            upload_gcode("http://printer.local:7125", "test.gcode", b"x" * (32 * 1024 * 1024 + 1), self.digest)

    def test_rejects_unexpected_remote_path(self):
        with self.assertRaises(UploadError):
            upload_gcode("http://printer.local:7125", "test.gcode", self.data, self.digest,
                         opener=lambda req, timeout: FakeResponse({"result": {"root": "gcodes", "item": {"path": "other.gcode"}}}))

if __name__ == "__main__":
    unittest.main()
