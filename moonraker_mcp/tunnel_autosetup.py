"""Provision official bundled OpenAI tunnel client and private key from HA options.

The official version and checksum are pinned at Docker image build time.
No network downloads or secret-bearing command arguments at startup.
"""
import hashlib
import hmac
import json
import os
import shutil
import stat
import tempfile
from pathlib import Path
from tunnel_provision import _private_directory, ProvisionError

UID = 65534
BUNDLED = Path("/opt/moonraker-mcp/vendor/tunnel-client")
EXPECTED_ZIP_SHA256 = "9ee9448592345a9dd1517fb79791ab54d24f051142eb92bcbe8cd355effc9142"


def _atomic_private(path, contents, uid=UID, mode=0o600):
    if path.is_symlink():
        raise ProvisionError("Refusing symbolic-link tunnel asset")
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=".private-")
    staged = Path(name)
    try:
        with os.fdopen(fd, "wb") as dest:
            dest.write(contents)
            dest.flush()
            os.fsync(dest.fileno())
        os.chown(staged, uid, uid)
        os.chmod(staged, mode)
        os.replace(staged, path)
    finally:
        staged.unlink(missing_ok=True)


def provision_from_options(base="/data", vendor=BUNDLED, uid=UID):
    root = Path(base)
    if root.is_symlink():
        raise ProvisionError("Unsafe data directory")
    options = root / "options.json"
    if options.is_symlink() or not options.is_file():
        raise ProvisionError("Missing trusted Home Assistant options file")
    with options.open(encoding="utf-8") as source:
        settings = json.load(source)
    if not isinstance(settings, dict):
        raise ProvisionError("Invalid Home Assistant options")
    tunnel = root / "tunnel"
    _private_directory(tunnel, uid)
    bindir = tunnel / "bin"
    _private_directory(bindir, uid)
    target = bindir / "tunnel-client"
    if target.is_symlink():
        raise ProvisionError("Refusing symbolic-link tunnel client")
    if not target.exists():
        if not vendor.is_file() or vendor.is_symlink():
            raise ProvisionError("Missing bundled official OpenAI tunnel client")
        # Binary was downloaded and SHA-256 checked during image build.
        # Use a private atomic copy so the client survives app upgrades.
        _atomic_private(target, vendor.read_bytes(), uid, 0o700)
    binary_info = target.stat()
    if not stat.S_ISREG(binary_info.st_mode) or binary_info.st_uid != uid or binary_info.st_mode & 0o077:
        raise ProvisionError("Insecure tunnel client ownership or permissions")
    raw = settings.get("openai_tunnel_api_key", "")
    if raw is None:
        raw = ""
    if not isinstance(raw, str):
        raise ProvisionError("OpenAI tunnel API key must be a string")
    key = tunnel / "api-key"
    if key.is_symlink():
        raise ProvisionError("Refusing symbolic-link tunnel API key")
    if raw:
        encoded = raw.encode("utf-8")
        if not 12 <= len(encoded) <= 8192 or any(c in encoded for c in (b"\x00", b"\r", b"\n")):
            raise ProvisionError("Invalid OpenAI tunnel API key format")
        existing = key.read_bytes() if key.exists() else b""
        if not hmac.compare_digest(existing, encoded):
            _atomic_private(key, encoded, uid)
    if not key.is_file():
        raise ProvisionError("Configure OpenAI tunnel API key in Home Assistant")
    key_info = key.stat()
    if not stat.S_ISREG(key_info.st_mode) or key_info.st_uid != uid or key_info.st_mode & 0o077:
        raise ProvisionError("Insecure tunnel API key ownership or permissions")
    return "Tunnel client and private key ready"


if __name__ == "__main__":
    print(provision_from_options())
