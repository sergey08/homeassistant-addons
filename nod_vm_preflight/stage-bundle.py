#!/usr/bin/env python3
"""Stage the pinned upstream archive without executing or extracting it."""
import hashlib
import os
from pathlib import Path
import shutil
import stat
import tempfile

NAME = "nod-server-linux-amd64-6670bc233b6b7dddaa75b25b89b4a89f0e92bcac.zip"
SIZE = 1819319467
SHA = "12697d29935880163af1292a1264632776ab6740e2a38460f4261d4d63b5b4e9"

def stage(source, destination, size=SIZE, digest=SHA):
    if destination.exists():
        with destination.open("rb") as stream:
            if destination.stat().st_size == size and hashlib.file_digest(stream, "sha256").hexdigest() == digest:
                return "NOD_BUNDLE_VERIFIED"
        raise ValueError("Existing cached bundle failed verification; preserve it for investigation")
    if not source.exists():
        return "NOD_BUNDLE_PENDING"
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if shutil.disk_usage(destination.parent).free < size + 256 * 1024**2:
        raise ValueError("Insufficient free space for bundle")
    temp = None
    try:
        with os.fdopen(os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as src:
            info = os.fstat(src.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size != size:
                raise ValueError("Invalid bundle file type or size")
            h = hashlib.sha256()
            with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as out:
                temp = Path(out.name)
                remaining = size
                while remaining:
                    chunk = src.read(min(1024**2, remaining))
                    if not chunk:
                        raise ValueError("Truncated bundle")
                    h.update(chunk)
                    out.write(chunk)
                    remaining -= len(chunk)
                if src.read(1) or h.hexdigest() != digest:
                    raise ValueError("Bundle checksum mismatch")
                out.flush()
                os.fsync(out.fileno())
            os.replace(temp, destination)
            temp = None
        return "NOD_BUNDLE_VERIFIED"
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)

if __name__ == "__main__":
    print(stage(Path("/config") / NAME, Path("/data/nod-bundles") / NAME), flush=True)
