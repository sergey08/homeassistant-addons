"""Append-only, authenticated encrypted backup storage for isolated tests.

Never touches CouchDB and never enabled for production. The HMAC secret must
be supplied by an isolated caller from a separate trusted source, not saved
alongside backups. Files contain LiveSync ciphertext and sensitive metadata.
"""
import hashlib
import hmac
import json
import os
import re
import secrets
from pathlib import Path
from livesync_isolated_backup import BackupRejected, MAX_BACKUP_BYTES, _canonical, _checksum
from livesync_write_preflight import UnsafeWrite

_ID = re.compile(r"[0-9a-f]{32}\Z")
_MAX_RECORD = MAX_BACKUP_BYTES + 4096


def _gate(isolated_test, remote_writes_enabled):
    if isolated_test is not True or remote_writes_enabled is not False:
        raise UnsafeWrite("isolated_persistent_backup_only")


def _key(secret):
    if not isinstance(secret, bytes) or len(secret) < 32:
        raise BackupRejected("separate_backup_key_required")
    return secret


def _root(root, *, create=False):
    if not isinstance(root, (str, os.PathLike)):
        raise BackupRejected("invalid_backup_directory")
    path = Path(root)
    if not path.is_absolute() or path.is_symlink():
        raise BackupRejected("unsafe_backup_directory")
    if create:
        path.mkdir(mode=0o700, parents=False, exist_ok=True)
    if not path.is_dir() or path.is_symlink() or (path.stat().st_mode & 0o077):
        raise BackupRejected("insecure_backup_directory")
    return path


def _sign(payload, secret):
    return hmac.new(_key(secret), _canonical(payload), hashlib.sha256).hexdigest()


def _verified_envelope(backup):
    if (not isinstance(backup, dict)
            or set(backup) != {"schema", "kind", "snapshot", "sha256"}
            or backup["schema"] not in (1, 2)
            or not isinstance(backup["snapshot"], dict)
            or (backup["schema"] == 2 and "path" in backup["snapshot"])
            or backup["kind"] != "isolated_encrypted_snapshot"
            or not isinstance(backup["sha256"], str)
            or len(backup["sha256"]) != 64):
        raise BackupRejected("invalid_backup")
    try:
        valid = hmac.compare_digest(_checksum(backup["snapshot"]), backup["sha256"])
    except (TypeError, ValueError, OverflowError, UnicodeError) as exc:
        raise BackupRejected("invalid_backup") from exc
    if not valid:
        raise BackupRejected("backup_checksum_mismatch")


def store_signed_backup(root, backup, secret, *, isolated_test=False,
                        remote_writes_enabled=False):
    """Persist an isolated backup with exclusive creation and durable fsync."""
    _gate(isolated_test, remote_writes_enabled)
    _verified_envelope(backup)
    try:
        encoded = _canonical(backup)
    except (TypeError, ValueError, OverflowError, UnicodeError) as exc:
        raise BackupRejected("invalid_backup") from exc
    if len(encoded) > MAX_BACKUP_BYTES:
        raise BackupRejected("backup_too_large")
    # The standalone SHA alone is not authentication; HMAC signs entire record.
    backup_id = secrets.token_hex(16)
    payload = {"version": 1, "backup_id": backup_id, "backup": backup}
    record = {**payload, "mac": _sign(payload, secret)}
    serialized = _canonical(record)
    if len(serialized) > _MAX_RECORD:
        raise BackupRejected("record_too_large")
    directory = _root(root, create=True)
    location = directory / (backup_id + ".json")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    try:
        fd = os.open(location, flags, 0o600)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(serialized)
                handle.flush()
                os.fsync(handle.fileno())
        except BaseException:
            # A partially written file remains visible as evidence; never
            # silently reuse its ID or replace an existing backup.
            raise
        dir_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except OSError as exc:
        raise BackupRejected("backup_persist_failed") from exc
    return {"backup_id": backup_id, "durable": True, "immutable": True,
            "remote_writes_enabled": False, "restore_enabled": False}


def read_signed_backup(root, backup_id, secret, *, isolated_test=False,
                       remote_writes_enabled=False):
    """Authenticate a stored record. Never expose plaintext or permit restore."""
    _gate(isolated_test, remote_writes_enabled)
    if not isinstance(backup_id, str) or not _ID.fullmatch(backup_id):
        raise BackupRejected("invalid_backup_id")
    directory = _root(root)
    location = directory / (backup_id + ".json")
    try:
        fd = os.open(location, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as handle:
            if os.fstat(handle.fileno()).st_mode & 0o077:
                raise BackupRejected("insecure_backup_permissions")
            data = handle.read(_MAX_RECORD + 1)
    except OSError as exc:
        raise BackupRejected("backup_unavailable") from exc
    if len(data) > _MAX_RECORD:
        raise BackupRejected("backup_record_too_large")
    try:
        record = json.loads(data)
        if not isinstance(record, dict) or set(record) != {
                "version", "backup_id", "backup", "mac"}:
            raise BackupRejected("invalid_backup_record")
        if record["version"] != 1 or record["backup_id"] != backup_id:
            raise BackupRejected("backup_record_mismatch")
        mac = record["mac"]
        if not isinstance(mac, str) or len(mac) != 64:
            raise BackupRejected("backup_signature_invalid")
        unsigned = {key: record[key] for key in ("version", "backup_id", "backup")}
        if not hmac.compare_digest(_sign(unsigned, secret), mac):
            raise BackupRejected("backup_authentication_failed")
        _verified_envelope(record["backup"])
        return {"backup": record["backup"], "authenticated": True,
                "restore_enabled": False, "remote_writes_enabled": False}
    except (ValueError, TypeError, UnicodeDecodeError) as exc:
        if isinstance(exc, BackupRejected):
            raise
        raise BackupRejected("backup_record_corrupt") from exc
