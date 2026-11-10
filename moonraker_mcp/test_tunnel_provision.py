"""Offline tests only; all archives and secrets are synthetic."""
import hashlib
import os
import stat
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path

from tunnel_provision import ProvisionError, install_official_archive, provision_key


def fake_elf():
    header = bytearray(64)
    header[:4] = b"\x7fELF"
    header[4] = 2
    header[5] = 1
    struct.pack_into("<H", header, 16, 2)
    struct.pack_into("<H", header, 18, 62)
    return bytes(header) + b"TEST-ONLY-NOT-EXECUTABLE"


class ProvisionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.base = self.root / "data"
        self.base.mkdir()
        self.uid = os.getuid()
        self.archive = self.root / "tunnel-client-vTEST-linux-amd64.zip"
        self.manifest = self.root / "SHA256SUMS.txt"

    def make_release(self, contents=None, filename="tunnel-client"):
        with zipfile.ZipFile(self.archive, "w") as zipped:
            zipped.writestr(filename, fake_elf() if contents is None else contents)
        self.manifest.write_text(
            hashlib.sha256(self.archive.read_bytes()).hexdigest()
            + "  " + self.archive.name + "\n"
        )

    def test_install_verified_archive_non_overwriting_private(self):
        self.make_release()
        install_official_archive(self.archive, self.manifest, self.base, self.uid)
        binary = self.base / "tunnel/bin/tunnel-client"
        self.assertEqual(binary.read_bytes(), fake_elf())
        self.assertEqual(stat.S_IMODE(binary.stat().st_mode), 0o700)
        self.assertEqual(binary.stat().st_uid, self.uid)
        with self.assertRaises(ProvisionError):
            install_official_archive(self.archive, self.manifest, self.base, self.uid)

    def test_checksum_tampering_fails(self):
        self.make_release()
        self.manifest.write_text("0"*64 + "  " + self.archive.name + "\n")
        with self.assertRaisesRegex(ProvisionError, "checksum"):
            install_official_archive(self.archive, self.manifest, self.base, self.uid)
        self.assertFalse((self.base / "tunnel/bin/tunnel-client").exists())

    def test_non_elf_fails(self):
        self.make_release(b"NOT AN ELF")
        with self.assertRaisesRegex(ProvisionError, "ELF"):
            install_official_archive(self.archive, self.manifest, self.base, self.uid)

    def test_traversal_and_symbolic_zip_members_fail(self):
        self.make_release(filename="../tunnel-client")
        with self.assertRaisesRegex(ProvisionError, "Unsafe"):
            install_official_archive(self.archive, self.manifest, self.base, self.uid)

    def test_key_permissions_and_no_overwrite(self):
        provision_key(b"test-only-key-is-not-real", self.base, self.uid)
        key = self.base / "tunnel/api-key"
        self.assertEqual(stat.S_IMODE(key.stat().st_mode), 0o600)
        self.assertEqual(key.stat().st_uid, self.uid)
        self.assertEqual(key.read_bytes(), b"test-only-key-is-not-real")
        with self.assertRaisesRegex(ProvisionError, "refusing overwrite"):
            provision_key(b"another-test-only-key", self.base, self.uid)

    def test_invalid_key_rejected(self):
        for value in (b"", b"short", b"test-value\nwith-newline", b"test\x00embedded-secret"):
            with self.subTest(value=value):
                with self.assertRaises(ProvisionError):
                    provision_key(value, self.base, self.uid)

    def test_key_symlink_refused(self):
        directory = self.base / "tunnel"
        directory.mkdir()
        destination = self.root / "do-not-touch"
        destination.write_text("unchanged")
        (directory / "api-key").symlink_to(destination)
        with self.assertRaisesRegex(ProvisionError, "refusing overwrite"):
            provision_key(b"test-only-key-is-not-real", self.base, self.uid)
        self.assertEqual(destination.read_text(), "unchanged")

    def test_tunnel_directory_symlink_refused(self):
        (self.base / "tunnel").symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(ProvisionError, "symbolic-link"):
            provision_key(b"test-only-key-is-not-real", self.base, self.uid)


if __name__ == "__main__":
    unittest.main()
