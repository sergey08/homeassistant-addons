"""Offline tests for bounded, ordered G-code staging chunks."""
import base64
import hashlib
import tempfile
import unittest
from pathlib import Path

from moonraker_chunk_staging import stage_chunk
from moonraker_staging import read_staged_gcode
from moonraker_upload import UploadError


class ChunkStagingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.root.chmod(0o700)
        self.data = b"; test G-code\nG28\n"
        self.digest = hashlib.sha256(self.data).hexdigest()

    def send(self, chunk, offset=0, final=False, digest=None, filename="sample.gcode"):
        return stage_chunk(filename, digest or self.digest, offset,
                           base64.b64encode(chunk).decode(), final, self.root)

    def test_two_chunks_then_verified_publication(self):
        first = self.send(self.data[:5])
        self.assertFalse(first["complete"])
        self.assertFalse((self.root / "sample.gcode").exists())
        last = self.send(self.data[5:], 5, True)
        self.assertTrue(last["complete"])
        self.assertEqual(read_staged_gcode("sample.gcode", self.digest, self.root), self.data)

    def test_wrong_offset_fails_closed(self):
        self.send(self.data[:5])
        with self.assertRaises(UploadError):
            self.send(self.data[5:], 6, True)
        self.assertFalse((self.root / "sample.gcode").exists())

    def test_bad_hash_never_publishes(self):
        with self.assertRaises(UploadError):
            self.send(self.data, final=True, digest="0" * 64)
        self.assertFalse((self.root / "sample.gcode").exists())

    def test_rejects_repeated_start(self):
        self.send(self.data[:5])
        with self.assertRaises(UploadError):
            self.send(self.data[:5])
        self.assertFalse((self.root / "sample.gcode").exists())

    def test_rejects_oversized_chunk(self):
        with self.assertRaises(UploadError):
            self.send(b"x" * 8193)

    def test_rejects_binary_chunk(self):
        with self.assertRaises(UploadError):
            self.send(b"G28\\x00", final=True)

    def test_never_overwrites_published_file(self):
        self.send(self.data, final=True)
        with self.assertRaises(UploadError):
            self.send(self.data, final=True)
        self.assertEqual((self.root / "sample.gcode").read_bytes(), self.data)


if __name__ == "__main__":
    unittest.main()
