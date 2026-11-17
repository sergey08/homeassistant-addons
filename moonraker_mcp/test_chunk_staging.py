"""Offline tests for bounded, ordered G-code staging chunks."""
import base64
import hashlib
import fcntl
import os
import tempfile
import unittest
from pathlib import Path

from moonraker_chunk_staging import stage_chunk, abort_staged_chunk
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

    def test_rejects_concurrent_writer_lock(self):
        self.send(self.data[:5])
        part = self.root / ("." + "sample.gcode" + "." + self.digest + ".part")
        fd = os.open(part, os.O_WRONLY)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(UploadError):
                self.send(self.data[5:], 5, True)
            self.assertEqual(part.stat().st_size, 5)
            self.assertFalse((self.root / "sample.gcode").exists())
        finally:
            os.close(fd)

    def test_rejects_filename_too_long_for_part_name(self):
        with self.assertRaises(UploadError):
            self.send(self.data, final=True, filename="a" * 160 + ".gcode")

    def test_directory_lock_prevents_concurrent_quota_reservations(self):
        fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(UploadError):
                self.send(self.data[:4])
            self.assertEqual(list(self.root.iterdir()), [])
        finally:
            os.close(fd)

    def test_abort_only_matching_incomplete_part(self):
        self.send(self.data[:4])
        with self.assertRaises(UploadError):
            abort_staged_chunk("other.gcode", self.digest, self.root)
        self.assertEqual(abort_staged_chunk("sample.gcode", self.digest, self.root)["aborted"], True)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_abort_never_deletes_published_gcode(self):
        self.send(self.data, final=True)
        with self.assertRaises(UploadError):
            abort_staged_chunk("sample.gcode", self.digest, self.root)
        self.assertEqual((self.root / "sample.gcode").read_bytes(), self.data)

    def test_abort_rejects_symlink_part(self):
        part = self.root / ("." + "sample.gcode" + "." + self.digest + ".part")
        part.symlink_to(self.root / "victim")
        with self.assertRaises(UploadError):
            abort_staged_chunk("sample.gcode", self.digest, self.root)
        self.assertTrue(part.is_symlink())

    def test_partial_session_count_quota(self):
        for i in range(4):
            self.send(self.data[:4], filename="session%d.gcode" % i)
        with self.assertRaisesRegex(UploadError, "quota"):
            self.send(self.data[:4], filename="session4.gcode")
        self.assertFalse((self.root / "session4.gcode").exists())

    def test_rejects_unsafe_inventory(self):
        (self.root / ".foreign.part").symlink_to(self.root / "missing")
        with self.assertRaises(UploadError):
            self.send(self.data[:4])

    def test_rejects_oversized_chunk(self):
        with self.assertRaises(UploadError):
            self.send(b"x" * 8193)

    def test_rejects_binary_chunk(self):
        with self.assertRaises(UploadError):
            self.send(b"G28" + bytes([0]), final=True)

    def test_rejects_actual_nul_before_writing(self):
        with self.assertRaises(UploadError):
            self.send(b"G28" + bytes([0]) + b"\\n", final=True)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_rejects_symlink_part(self):
        part = self.root / ("." + "sample.gcode" + "." + self.digest + ".part")
        part.symlink_to(self.root / "victim")
        with self.assertRaises(UploadError):
            self.send(self.data)
        self.assertFalse((self.root / "sample.gcode").exists())

    def test_rejects_wrong_final_hash_without_publishing(self):
        wrong = "f" * 64 if self.digest != "f" * 64 else "e" * 64
        with self.assertRaises(UploadError):
            self.send(self.data, final=True, digest=wrong)
        self.assertFalse((self.root / "sample.gcode").exists())

    def test_never_overwrites_published_file(self):
        self.send(self.data, final=True)
        with self.assertRaises(UploadError):
            self.send(self.data, final=True)
        self.assertEqual((self.root / "sample.gcode").read_bytes(), self.data)


if __name__ == "__main__":
    unittest.main()
