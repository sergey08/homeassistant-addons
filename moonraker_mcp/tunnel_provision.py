"""Offline, fail-closed provisioning for Moonraker's own OpenAI tunnel client.

Does not download releases or access the network. The release ZIP and its
SHA256SUMS manifest MUST be sourced and verified independently. Provisioning is
a separate operator action, never invoked during add-on startup.
"""
import hashlib
import os
import shutil
import stat
import struct
import tempfile
import zipfile
from pathlib import Path


class ProvisionError(ValueError):
    pass


def _private_directory(path: Path, uid: int):
    if path.is_symlink():
        raise ProvisionError("Refusing symbolic-link tunnel directory")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not path.is_dir():
        raise ProvisionError("Tunnel path is not a directory")
    os.chmod(path, 0o700)
    os.chown(path, uid, uid)


def install_official_archive(archive_path, manifest_path, base="/data", uid=65534):
    """Install a locally supplied, verified linux-amd64 ELF. Never replace."""
    archive, manifest = Path(archive_path), Path(manifest_path)
    if not archive.is_file() or not manifest.is_file():
        raise ProvisionError("A release ZIP and SHA256SUMS manifest are required")
    if (not archive.name.startswith("tunnel-client-")
            or "linux-amd64" not in archive.name or archive.suffix != ".zip"):
        raise ProvisionError("Expected an official linux-amd64 tunnel-client ZIP")
    if archive.stat().st_size > 150_000_000 or manifest.stat().st_size > 1_000_000:
        raise ProvisionError("Release archive or manifest exceeds limits")
    checksum = None
    for line in manifest.read_text("utf-8").splitlines():
        fields = line.strip().split(maxsplit=1)
        if len(fields) != 2:
            continue
        candidate = fields[1].lstrip("*").removeprefix("./")
        if candidate == archive.name and len(fields[0]) == 64:
            if checksum is not None:
                raise ProvisionError("Duplicate manifest entry")
            checksum = fields[0].lower()
    if checksum is None or any(c not in "0123456789abcdef" for c in checksum):
        raise ProvisionError("Missing or invalid release manifest entry")
    digest = hashlib.file_digest(archive.open("rb"), "sha256").hexdigest()
    if digest != checksum:
        raise ProvisionError("Release checksum mismatch")
    root = Path(base)
    if root.is_symlink():
        raise ProvisionError("Refusing symbolic-link data directory")
    _private_directory(root / "tunnel", uid)
    destdir = root / "tunnel/bin"
    _private_directory(destdir, uid)
    dest = destdir / "tunnel-client"
    if dest.exists() or dest.is_symlink():
        raise ProvisionError("Tunnel binary already exists: refusing replacement")
    with zipfile.ZipFile(archive) as z:
        members = z.infolist()
        if not 1 <= len(members) <= 150:
            raise ProvisionError("Unexpected archive layout")
        found = []
        for item in members:
            p = Path(item.filename)
            mode = (item.external_attr >> 16) & 0o170000
            if p.is_absolute() or ".." in p.parts or len(p.parts) > 4:
                raise ProvisionError("Unsafe archive path")
            if mode not in (0, stat.S_IFREG, stat.S_IFDIR):
                raise ProvisionError("Archive has non-regular entries")
            if not item.is_dir() and p.name == "tunnel-client":
                found.append(item)
        if len(found) != 1 or found[0].file_size > 90_000_000:
            raise ProvisionError("Expected exactly one tunnel-client executable")
        with tempfile.NamedTemporaryFile(dir=destdir, prefix=".staged-", delete=False) as tmp:
            staged = Path(tmp.name)
            try:
                with z.open(found[0]) as source:
                    shutil.copyfileobj(source, tmp)
                tmp.flush()
                os.fsync(tmp.fileno())
            except BaseException:
                staged.unlink(missing_ok=True)
                raise
    try:
        with staged.open("rb") as f:
            header = f.read(64)
        if (len(header) < 64 or header[:4] != b"\x7fELF"
                or header[4] != 2 or header[5] != 1
                or struct.unpack_from("<H", header, 16)[0] not in (2, 3)
                or struct.unpack_from("<H", header, 18)[0] != 62):
            raise ProvisionError("Invalid linux-amd64 ELF binary")
        os.chmod(staged, 0o700)
        os.chown(staged, uid, uid)
        os.link(staged, dest)
    finally:
        staged.unlink(missing_ok=True)
    return "Verified ZIP checksum and installed private ELF. Verify vendor provenance separately."


def provision_key(raw: bytes, base="/data", uid=65534):
    """Write a distinct per-Moonraker key without overwriting or logging it."""
    if not isinstance(raw, bytes) or not 12 <= len(raw) <= 8192:
        raise ProvisionError("Invalid key format or size")
    if any(ch in raw for ch in (b"\x00", b"\r", b"\n")):
        raise ProvisionError("Key contains forbidden control characters")
    directory = Path(base) / "tunnel"
    _private_directory(directory, uid)
    target = directory / "api-key"
    if target.exists() or target.is_symlink():
        raise ProvisionError("Private key already exists: refusing overwrite")
    fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        os.fchown(fd, uid, uid)
        with os.fdopen(fd, "wb") as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    return "Stored private tunnel key without printing it."
