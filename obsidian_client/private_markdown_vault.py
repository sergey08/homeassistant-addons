"""Private Markdown vault for the Obsidian Client.

This module never communicates with CouchDB or invokes LiveSync.
It deliberately uses a private /data directory, not the real /share vault.
"""
from pathlib import Path
import hashlib
import os
import re
import shutil
import tempfile
from datetime import datetime, timezone

MAX_BYTES = 2_000_000
SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class LocalVaultError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _root(root):
    root = Path(root)
    if not root.is_absolute() or root.is_symlink():
        raise LocalVaultError("unsafe_vault_root")
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not root.is_dir():
        raise LocalVaultError("unsafe_vault_root")
    return root.resolve(strict=True)


def _path(root, name):
    if (not isinstance(name, str) or len(name) > 500 or not name
            or "\\" in name or "\x00" in name):
        raise LocalVaultError("invalid_note_path")
    relative = Path(name)
    if (relative.is_absolute() or relative.suffix.lower() != ".md"
            or any(part in ("", ".", "..") or part.startswith(".")
                   for part in relative.parts)):
        raise LocalVaultError("invalid_note_path")
    base = _root(root)
    current = base
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise LocalVaultError("symlink_not_allowed")
    if not current.resolve(strict=False).is_relative_to(base):
        raise LocalVaultError("outside_vault")
    return base, current


def _content_bytes(content):
    if not isinstance(content, str):
        raise LocalVaultError("invalid_content")
    try:
        encoded = content.encode("utf-8")
    except UnicodeError as exc:
        raise LocalVaultError("invalid_content") from exc
    if len(encoded) > MAX_BYTES:
        raise LocalVaultError("note_too_large")
    return encoded


def read_note(root, name):
    _base, target = _path(root, name)
    if not target.is_file():
        raise LocalVaultError("note_not_found")
    data = target.read_bytes()
    if len(data) > MAX_BYTES:
        raise LocalVaultError("note_too_large")
    try:
        content = data.decode("utf-8")
    except UnicodeError as exc:
        raise LocalVaultError("invalid_utf8") from exc
    return {"path": name, "content": content, "sha256": hashlib.sha256(data).hexdigest()}


def save_note(root, backup_root, name, content, mode, expected_sha256=None):
    """Caller serializes access with one process-level lock."""
    base, target = _path(root, name)
    data = _content_bytes(content)
    if mode not in ("create", "update"):
        raise LocalVaultError("invalid_mode")
    exists = target.exists()
    if mode == "create" and exists:
        raise LocalVaultError("note_exists")
    if mode == "update":
        if not isinstance(expected_sha256, str) or not SHA256.fullmatch(expected_sha256):
            raise LocalVaultError("expected_revision_required")
        if not exists or not target.is_file():
            raise LocalVaultError("note_not_found")
        previous = target.read_bytes()
        if hashlib.sha256(previous).hexdigest() != expected_sha256:
            raise LocalVaultError("revision_conflict")
        if len(previous) > MAX_BYTES:
            raise LocalVaultError("note_too_large")
        # Backups are private, outside the served vault.
        backup_base = _root(backup_root)
        relative = target.relative_to(base)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        backup = backup_base / stamp / relative
        if not backup.resolve(strict=False).is_relative_to(backup_base):
            raise LocalVaultError("unsafe_backup_path")
        backup.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if backup.is_symlink() or backup.exists():
            raise LocalVaultError("backup_collision")
        with backup.open("xb") as out:
            out.write(previous)
            out.flush()
            os.fsync(out.fileno())
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Revalidate after directory creation to catch pre-existing symlinks.
    _path(root, name)
    fd, tmp = tempfile.mkstemp(prefix=".obsidian-", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as out:
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmp, target)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return {"path": name, "sha256": hashlib.sha256(data).hexdigest(),
            "status": "saved_private_markdown_only", "remote_synced": False}


def list_notes(root, *, limit=500):
    """List only ordinary Markdown files under the isolated private vault."""
    base = _root(root)
    names = []
    for candidate in base.rglob("*.md"):
        relative = candidate.relative_to(base)
        if (any(part.startswith(".") for part in relative.parts)
                or any(part.is_symlink() for part in [base / Path(*relative.parts[:i])
                                                     for i in range(1, len(relative.parts) + 1)])
                or not candidate.is_file()
                or not candidate.resolve(strict=False).is_relative_to(base)):
            continue
        names.append(relative.as_posix())
        if len(names) >= limit:
            break
    return sorted(names, key=str.casefold)
