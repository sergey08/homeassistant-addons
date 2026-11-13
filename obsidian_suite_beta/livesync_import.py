"""Safe, one-time LiveSync setup URI import for fresh installs.

The URI is sensitive. Never print it or the CLI output. Do not overwrite
existing configuration. An isolated temporary database prevents failed setup
from altering an active vault.
"""
import os
import subprocess
import tempfile
from pathlib import Path

CLI = "/usr/local/bin/livesync-cli"
MAX_URI_BYTES = 16000

class ImportErrorSafe(Exception):
    pass

def import_setup_uri(uri, base, cli=CLI, timeout=30):
    if not isinstance(uri, str) or not uri.startswith("obsidian://setuplivesync?settings="):
        raise ImportErrorSafe("Expected a Self-hosted LiveSync setup URI")
    if len(uri.encode("utf-8")) > MAX_URI_BYTES or any(x in uri for x in "\r\n\x00"):
        raise ImportErrorSafe("Invalid setup URI length or characters")
    base = Path(base)
    settings_dir = base / "settings"
    target = settings_dir / "livesync-operativo.json"
    if target.exists() or target.is_symlink():
        raise ImportErrorSafe("LiveSync settings already exist; import refused to prevent overwrite")
    settings_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(settings_dir, 0o700)
    # Set up against an isolated DB; never touch the production vault here.
    with tempfile.TemporaryDirectory(prefix=".livesync-import-", dir=base) as temp:
        temp_dir = Path(temp)
        staged = temp_dir / "settings.json"
        try:
            proc = subprocess.run(
                [cli, str(temp_dir), "--settings", str(staged), "setup", uri],
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, timeout=timeout, check=False,
                env={**os.environ, "NO_COLOR": "1"},
            )
        except (OSError, subprocess.TimeoutExpired):
            raise ImportErrorSafe("LiveSync CLI setup failed; check the binary and setup URI") from None
        if proc.returncode or not staged.is_file() or staged.stat().st_size == 0:
            raise ImportErrorSafe("LiveSync rejected the setup URI; no active configuration was changed")
        os.chmod(staged, 0o600)
        # Exclusive destination creation; avoids overwriting existing config.
        try:
            fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            try:
                with os.fdopen(fd, "wb") as output, staged.open("rb") as src:
                    output.write(src.read())
            except BaseException:
                target.unlink(missing_ok=True)
                raise
        except FileExistsError:
            raise ImportErrorSafe("Settings appeared concurrently; import refused") from None
    return "Configuration imported. Verify CouchDB and LiveSync before enabling synchronization."
