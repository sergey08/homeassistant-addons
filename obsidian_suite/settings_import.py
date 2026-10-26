"""Safe upload of pre-exported LiveSync CLI settings JSON.

This avoids putting a secret setup URI in the CLI process command line.
"""
import json
import os
from pathlib import Path

MAX_SETTINGS_BYTES = 131072

class SettingsImportError(Exception):
    pass

def import_settings_json(raw, base):
    if not isinstance(raw, (bytes, bytearray)) or not 0 < len(raw) <= MAX_SETTINGS_BYTES:
        raise SettingsImportError("Invalid settings file size")
    try:
        obj = json.loads(raw)
    except (UnicodeDecodeError, ValueError):
        raise SettingsImportError("Invalid JSON settings") from None
    if not isinstance(obj, dict) or not obj:
        raise SettingsImportError("Expected a non-empty settings JSON object")
    # We deliberately do not print, transform or infer encrypted settings.
    base = Path(base)
    folder = base / "settings"
    target = folder / "livesync-operativo.json"
    if target.exists() or target.is_symlink():
        raise SettingsImportError("Settings already exist: import refused to prevent overwrite")
    folder.mkdir(parents=True, exist_ok=True)
    os.chmod(folder, 0o700)
    try:
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise SettingsImportError("Settings already exist: import refused") from None
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    return "Settings file stored securely. Verify compatibility and CouchDB before enabling LiveSync."
