import hashlib
import os
import tempfile
import unittest
from pathlib import Path

from moonraker_staging import read_staged_gcode
from moonraker_upload import UploadError


class StagingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.data = b"; Snapmaker U1\\nG28\\n"
        self.digest = hashlib.sha256(self.data).hexdigest()
        self.file = self.root / "sample.gcode"
        self.file.write_bytes(self.data)
        self.file.chmod(0o600)

    def test_reads_matching_file(self):
        self.assertEqual(read_staged_gcode("sample.gcode", self.digest, self.root), self.data)

    def test_rejects_wrong_hash(self):
        with self.assertRaises(UploadError):
            read_staged_gcode("sample.gcode", "0" * 64, self.root)

    def test_rejects_traversal(self):
        with self.assertRaises(UploadError):
            read_staged_gcode("../sample.gcode", self.digest, self.root)

    def test_rejects_symlink(self):
        (self.root / "link.gcode").symlink_to(self.file)
        with self.assertRaises(UploadError):
            read_staged_gcode("link.gcode", self.digest, self.root)

    def test_rejects_group_writable_file(self):
        self.file.chmod(0o620)
        with self.assertRaises(UploadError):
            read_staged_gcode("sample.gcode", self.digest, self.root)

    def test_rejects_binary_input(self):
        data = self.data + bytes([0])
        self.file.write_bytes(data)
        with self.assertRaises(UploadError):
            read_staged_gcode("sample.gcode", hashlib.sha256(data).hexdigest(), self.root)

    def test_rejects_symlink_directory(self):
        alias = self.root.parent / (self.root.name + "-alias")
        alias.symlink_to(self.root, target_is_directory=True)
        self.addCleanup(alias.unlink)
        with self.assertRaises(UploadError):
            read_staged_gcode("sample.gcode", self.digest, alias)


if __name__ == "__main__":
    unittest.main()
