import hashlib
import os
import stat
import struct
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tunnel_installer import TunnelInstallError, install_official_archive


class TunnelInstallerTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.base = self.root / "data"
        self.checksums = self.root / "SHA256SUMS.txt"
        self.destination = self.base / "tunnel/bin/tunnel-client"

    def release(self, arch, elf_machine, member="release/tunnel-client", mode=stat.S_IFREG):
        archive = self.root / f"tunnel-client-v0.0.20-linux-{arch}.zip"
        header = bytearray(64)
        header[:6] = b"\x7fELF\x02\x01"
        struct.pack_into("<HH", header, 16, 2, elf_machine)
        entry = zipfile.ZipInfo(member)
        entry.create_system = 3
        entry.external_attr = mode << 16
        with zipfile.ZipFile(archive, "w") as release:
            release.writestr(entry, header)
        self.checksums.write_text(f"{hashlib.sha256(archive.read_bytes()).hexdigest()}  {archive.name}\n")
        return archive

    def install(self, machine, archive):
        with patch("tunnel_installer.platform.machine", return_value=machine):
            return install_official_archive(archive, self.checksums, self.base)

    def test_native_architectures_and_aliases(self):
        for machine, arch, elf_machine in (
            ("x86_64", "amd64", 62), ("amd64", "amd64", 62),
            ("aarch64", "arm64", 183), ("arm64", "arm64", 183),
        ):
            with self.subTest(machine=machine):
                archive = self.release(arch, elf_machine)
                self.install(machine, archive)
                self.assertEqual(struct.unpack_from("<H", self.destination.read_bytes(), 18)[0], elf_machine)
                if os.name == "posix":
                    self.assertEqual(self.destination.stat().st_mode & 0o777, 0o700)
                self.destination.unlink()

    def test_rejects_wrong_archive_and_wrong_elf_in_either_direction(self):
        for machine, arch, other, wrong_elf in (
            ("x86_64", "amd64", "arm64", 183),
            ("aarch64", "arm64", "amd64", 62),
        ):
            with self.subTest(machine=machine):
                with self.assertRaisesRegex(TunnelInstallError, f"Expected an official Linux {arch}"):
                    self.install(machine, self.release(other, wrong_elf))
                with self.assertRaisesRegex(TunnelInstallError, f"{arch} ELF"):
                    self.install(machine, self.release(arch, wrong_elf))
                self.assertEqual(list(self.destination.parent.iterdir()), [])

    def test_rejects_unsupported_machine(self):
        with self.assertRaisesRegex(TunnelInstallError, "Unsupported"):
            self.install("armv7l", self.release("arm64", 183))

    def test_requires_matching_checksum(self):
        archive = self.release("arm64", 183)
        self.checksums.write_text(f"{'0' * 64}  {archive.name}\n")
        with self.assertRaisesRegex(TunnelInstallError, "checksum mismatch"):
            self.install("aarch64", archive)
        self.assertFalse(self.base.exists())

    def test_rejects_unsafe_paths_and_symlinks(self):
        for member, mode, error in (
            ("../tunnel-client", stat.S_IFREG, "Unsafe path"),
            ("release/tunnel-client", stat.S_IFLNK, "Non-regular"),
        ):
            with self.subTest(member=member, mode=mode):
                with self.assertRaisesRegex(TunnelInstallError, error):
                    self.install("aarch64", self.release("arm64", 183, member, mode))
                self.assertFalse(self.destination.exists())

    def test_preserves_existing_client(self):
        self.destination.parent.mkdir(parents=True)
        self.destination.write_bytes(b"existing")
        with self.assertRaisesRegex(TunnelInstallError, "replacement refused"):
            self.install("aarch64", self.release("arm64", 183))
        self.assertEqual(self.destination.read_bytes(), b"existing")
