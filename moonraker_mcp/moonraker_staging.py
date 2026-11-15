"""Read an explicitly staged G-code from a fixed private directory.

No arbitrary filesystem paths, URL downloads or printer actions. The caller
must separately approve the exact filename and SHA-256 before upload.
"""
import hashlib
import os
import stat
from pathlib import Path

from moonraker_upload import MAX_UPLOAD_BYTES, UploadError

STAGING_DIR = Path("/data/safe-gcode-staging")


def read_staged_gcode(filename, expected_sha256, directory=STAGING_DIR):
    if type(filename) is not str or not filename or filename in (".", ".."):
        raise UploadError("Invalid staged filename")
    if len(filename) > 255 or any(c in filename for c in ('/', '\\', '%', '"', ';', '\x00')):
        raise UploadError("Unsafe staged filename")
    if not filename.lower().endswith((".gcode", ".gco")):
        raise UploadError("Only G-code accepted")
    if any(ord(c) < 32 or ord(c) == 127 for c in filename):
        raise UploadError("Invalid staged filename")
    if type(expected_sha256) is not str or len(expected_sha256) != 64 or any(
            c not in "0123456789abcdefABCDEF" for c in expected_sha256):
        raise UploadError("Invalid SHA-256")
    # Open the directory itself without following a symlink; openat prevents
    # traversal and the file cannot be swapped by renaming its pathname.
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    try:
        dirfd = os.open(os.fspath(directory), flags)
        try:
            fd = os.open(filename, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=dirfd)
            try:
                info = os.fstat(fd)
                if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= MAX_UPLOAD_BYTES:
                    raise UploadError("Staged G-code must be a bounded regular file")
                if info.st_mode & 0o022:
                    raise UploadError("Staged file must not be group/world writable")
                with os.fdopen(os.dup(fd), "rb") as stream:
                    content = stream.read(MAX_UPLOAD_BYTES + 1)
            finally:
                os.close(fd)
        finally:
            os.close(dirfd)
    except OSError as exc:
        raise UploadError("Staged G-code unavailable or unsafe") from exc
    if len(content) != info.st_size or len(content) > MAX_UPLOAD_BYTES:
        raise UploadError("Staged G-code size changed")
    if hashlib.sha256(content).hexdigest() != expected_sha256.lower():
        raise UploadError("Staged G-code SHA-256 mismatch")
    if b"\x00" in content:
        raise UploadError("Binary G-code refused")
    return content
