"""Bounded, sequential G-code staging. Does not contact or control a printer.

Each chunk is base64, strictly sequenced, and capped at 8 KiB decoded.
The final file is published atomically only after a full SHA-256 match.
A session is one filename+hash pair, never an arbitrary path.
"""
import base64
import binascii
import fcntl
import hashlib
import os
import re
import stat
from pathlib import Path

from moonraker_staging import STAGING_DIR
from moonraker_upload import MAX_UPLOAD_BYTES, UploadError

MAX_CHUNK_BYTES = 8192
SHA_RE = re.compile(r"^[a-fA-F0-9]{64}$")
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._ -]{0,149}\.(?:gcode|gco)$", re.I)


def _validate(filename, digest):
    if type(filename) is not str or not NAME_RE.fullmatch(filename) or filename in (".", ".."):
        raise UploadError("Invalid staging filename")
    if type(digest) is not str or not SHA_RE.fullmatch(digest):
        raise UploadError("Invalid staging SHA-256")


def stage_chunk(filename, expected_sha256, offset, chunk_b64, final=False, directory=STAGING_DIR):
    _validate(filename, expected_sha256)
    if type(offset) is not int or not 0 <= offset <= MAX_UPLOAD_BYTES:
        raise UploadError("Invalid staging offset")
    if type(final) is not bool or type(chunk_b64) is not str or len(chunk_b64) > 11000:
        raise UploadError("Invalid chunk")
    try:
        chunk = base64.b64decode(chunk_b64, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise UploadError("Invalid base64 chunk") from exc
    if not 0 < len(chunk) <= MAX_CHUNK_BYTES or offset + len(chunk) > MAX_UPLOAD_BYTES:
        raise UploadError("Chunk exceeds staging limits")
    if bytes([0]) in chunk:
        raise UploadError("Binary G-code refused")
    directory = Path(directory)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    try:
        dirfd = os.open(directory, flags)
        try:
            dstat = os.fstat(dirfd)
            if dstat.st_mode & 0o077:
                raise UploadError("Staging directory is not private")
            # The hidden part filename is derived solely from the approved
            # destination. O_EXCL ensures no concurrent or stale overwrite.
            part = "." + filename + "." + expected_sha256.lower() + ".part"
            if offset == 0:
                fd = os.open(part, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                             0o600, dir_fd=dirfd)
            else:
                fd = os.open(part, os.O_WRONLY | os.O_NOFOLLOW, dir_fd=dirfd)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                info = os.fstat(fd)
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_mode & 0o077:
                    raise UploadError("Unsafe staging part")
                if info.st_size != offset:
                    raise UploadError("Out-of-order chunk")
                os.lseek(fd, offset, os.SEEK_SET)
                written = os.write(fd, chunk)
                if written != len(chunk):
                    os.ftruncate(fd, offset)
                    raise UploadError("Short staging write")
                os.fsync(fd)
                if not final:
                    return {"received_bytes": offset + len(chunk), "complete": False}
                # Finalization requires full integrity verification.
                readfd = os.open(part, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=dirfd)
                try:
                    with os.fdopen(readfd, "rb") as stream:
                        payload = stream.read(MAX_UPLOAD_BYTES + 1)
                except Exception:
                    raise
                if len(payload) != offset + len(chunk) or hashlib.sha256(payload).hexdigest() != expected_sha256.lower():
                    raise UploadError("Final SHA-256 mismatch")
                if bytes([0]) in payload:
                    raise UploadError("Binary G-code refused")
                # Never overwrite a previously published destination.
                os.link(part, filename, src_dir_fd=dirfd, dst_dir_fd=dirfd, follow_symlinks=False)
                os.unlink(part, dir_fd=dirfd)
                return {"received_bytes": len(payload), "complete": True,
                        "filename": filename, "sha256": expected_sha256.lower()}
            finally:
                os.close(fd)
        finally:
            os.close(dirfd)
    except OSError as exc:
        raise UploadError("Unable to stage G-code safely") from exc
