"""Offline installer for an official, separately verified tunnel-client release.

Never downloads executable code or overwrites an existing tunnel client.
Requires a SHA256SUMS file from the same trusted OpenAI release.
For higher assurance, verify upstream Sigstore release provenance separately.
"""
import argparse
import hashlib
import os
import platform
import shutil
import stat
import struct
import tempfile
import zipfile
from pathlib import Path

class TunnelInstallError(Exception):
    pass

def install_official_archive(archive_path, checksums_path, base):
    machine = platform.machine().lower()
    targets = {
        "x86_64": ("amd64", 62),
        "amd64": ("amd64", 62),
        "aarch64": ("arm64", 183),
        "arm64": ("arm64", 183),
    }
    if machine not in targets:
        raise TunnelInstallError(f"Unsupported tunnel client architecture: {machine}")
    release_arch, elf_machine = targets[machine]
    archive = Path(archive_path)
    checksums = Path(checksums_path)
    if not archive.is_file() or not checksums.is_file():
        raise TunnelInstallError("Release ZIP and matching SHA256SUMS.txt are required")
    if not archive.name.startswith("tunnel-client-") or not archive.name.endswith(f"-linux-{release_arch}.zip"):
        raise TunnelInstallError(f"Expected an official Linux {release_arch} tunnel-client ZIP")
    if archive.stat().st_size > 150 * 1024 * 1024 or checksums.stat().st_size > 1024 * 1024:
        raise TunnelInstallError("Release package or manifest is too large")
    candidates = {}
    for line in checksums.read_text(encoding="utf-8").splitlines():
        fields = line.strip().split(maxsplit=1)
        if len(fields) == 2 and len(fields[0]) == 64:
            candidates[fields[1].lstrip("*").removeprefix("./")] = fields[0].lower()
    expected = candidates.get(archive.name)
    if not expected:
        raise TunnelInstallError("Archive was not listed in the matching official checksum manifest")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest != expected:
        raise TunnelInstallError("Release ZIP checksum mismatch")
    target_dir = Path(base) / "tunnel/bin"
    dest = target_dir / "tunnel-client"
    if dest.exists() or dest.is_symlink():
        raise TunnelInstallError("Tunnel client already exists: replacement refused")
    target_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(target_dir, 0o700)
    try:
        with zipfile.ZipFile(archive) as zf:
            infos = zf.infolist()
            if not infos or len(infos) > 150:
                raise TunnelInstallError("Unexpected ZIP archive structure")
            binary = []
            for item in infos:
                path = Path(item.filename)
                if path.is_absolute() or ".." in path.parts or len(path.parts) > 4:
                    raise TunnelInstallError("Unsafe path in ZIP")
                mode = (item.external_attr >> 16) & 0o170000
                if mode not in (0, stat.S_IFREG, stat.S_IFDIR):
                    raise TunnelInstallError("Non-regular ZIP member rejected")
                if not item.is_dir() and path.name == "tunnel-client":
                    binary.append(item)
            if len(binary) != 1 or binary[0].file_size > 90 * 1024 * 1024:
                raise TunnelInstallError("Expected exactly one tunnel-client executable")
            with tempfile.NamedTemporaryFile(dir=target_dir, prefix=".staged-", delete=False) as temp:
                staging = Path(temp.name)
                try:
                    with zf.open(binary[0]) as stream:
                        shutil.copyfileobj(stream, temp)
                    temp.flush()
                    os.fsync(temp.fileno())
                except BaseException:
                    staging.unlink(missing_ok=True)
                    raise
            # ELF64 little-endian executable or PIE for the running architecture.
            with staging.open("rb") as exe:
                header = exe.read(64)
            if (len(header) < 64 or header[:4] != b"\x7fELF"
                    or header[4] != 2 or header[5] != 1
                    or struct.unpack_from("<H", header, 16)[0] not in (2, 3)
                    or struct.unpack_from("<H", header, 18)[0] != elf_machine):
                staging.unlink(missing_ok=True)
                raise TunnelInstallError(f"Archive does not contain a Linux {release_arch} ELF executable")
            staging.chmod(0o700)
            try:
                os.link(staging, dest)
            except FileExistsError:
                raise TunnelInstallError("Tunnel client already exists") from None
            finally:
                staging.unlink(missing_ok=True)
    except zipfile.BadZipFile:
        raise TunnelInstallError("Invalid release ZIP") from None
    return "Official release checksum matched; client staged. Verify upstream provenance before enabling the tunnel."


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("checksums", type=Path)
    parser.add_argument("base", type=Path, help="Persistent add-on directory containing the vault")
    args = parser.parse_args()
    try:
        print(install_official_archive(args.archive, args.checksums, args.base))
    except (TunnelInstallError, OSError, UnicodeError) as exc:
        parser.exit(1, f"{exc}\n")
