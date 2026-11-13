"""One-time, private tunnel runtime key provisioning. Never logs or returns secrets."""
import os
from pathlib import Path

class TunnelKeyError(Exception):
    pass

def store_runtime_key(raw, base):
    if not isinstance(raw, (str, bytes)):
        raise TunnelKeyError("Invalid tunnel key")
    secret = raw.encode("utf-8") if isinstance(raw, str) else raw
    if not 12 <= len(secret) <= 8192 or any(ch in secret for ch in (b"\x00", b"\r", b"\n")):
        raise TunnelKeyError("Invalid tunnel key size or format")
    root = Path(base) / "tunnel"
    target = root / "api-key"
    if target.exists() or target.is_symlink():
        raise TunnelKeyError("Runtime key already exists; refusing to overwrite")
    root.mkdir(parents=True, exist_ok=True)
    os.chmod(root, 0o700)
    try:
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise TunnelKeyError("Runtime key already exists") from None
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(secret)
            output.flush()
            os.fsync(output.fileno())
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    return "Tunnel runtime key stored privately. Add a verified official client executable and Tunnel ID before enabling the tunnel."
