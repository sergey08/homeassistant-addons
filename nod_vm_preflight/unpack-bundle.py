#!/usr/bin/env python3
"""Verify and extract only the expected upstream server bundle files."""
import hashlib
import pathlib
import shutil
import stat
import sys
import tarfile
import tempfile
import zipfile

FILES = set(".env.example Caddyfile docker-proxy.mjs setup.sh backup.sh restore.sh install.sh compose.yaml source-revision architecture images.txt images.tar.gz checksums.sha256".split())
REV = "6670bc233b6b7dddaa75b25b89b4a89f0e92bcac"
LIMIT = 8 * 1024**3

def extract_members(entries, opener, dest):
    seen = set()
    total = 0
    for name, size, regular in entries:
        p = pathlib.PurePosixPath(name)
        if p.is_absolute() or ".." in p.parts or not regular:
            raise ValueError("Unsafe archive member")
        if p.name not in FILES:
            print("NOD_BUNDLE_EXTRA_SKIPPED="+repr(name), flush=True)
            continue
        if p.name in seen:
            raise ValueError("Duplicate required archive file: "+repr(name))
        total += size
        if total > LIMIT or (p.name != "images.tar.gz" and size > 2*1024**2):
            raise ValueError("Archive size limit")
        with opener(name) as src, (dest / p.name).open("xb") as out:
            shutil.copyfileobj(src, out, 1024**2)
        seen.add(p.name)
    if seen != FILES:
        raise ValueError("Missing bundle files: "+repr(sorted(FILES-seen)))

def unpack(source, dest):
    with zipfile.ZipFile(source) as z:
        members = [i for i in z.infolist() if not i.is_dir()]
        if len(members) == 1 and members[0].filename.endswith((".tar.gz", ".tgz")):
            i = members[0]
            if i.file_size > LIMIT:
                raise ValueError("Nested archive size limit")
            with tempfile.TemporaryFile(dir=dest.parent) as tmp:
                with z.open(i) as stream:
                    shutil.copyfileobj(stream, tmp, 1024**2)
                tmp.seek(0)
                with tarfile.open(fileobj=tmp, mode="r:gz") as t:
                    entries = [(m.name,m.size,m.isfile()) for m in t if not m.isdir()]
                    extract_members(entries, t.extractfile, dest)
        else:
            extract_members([(i.filename,i.file_size,stat.S_IFMT(i.external_attr >> 16) in (0,stat.S_IFREG)) for i in members], z.open, dest)
    checks = {}
    for line in (dest/"checksums.sha256").read_text().splitlines():
        digest, name = line.split()
        if name not in FILES - {"checksums.sha256"}:
            continue
        if name in checks:
            raise ValueError("Duplicate checksum entry")
        checks[name] = digest
    if set(checks) != FILES - {"checksums.sha256"}:
        raise ValueError("Incomplete checksums")
    for name,digest in checks.items():
        with (dest/name).open("rb") as f:
            if hashlib.file_digest(f,"sha256").hexdigest() != digest:
                raise ValueError("Inner checksum mismatch: "+name)
    if (dest/"architecture").read_text().strip() != "amd64" or (dest/"source-revision").read_text().strip() != REV:
        raise ValueError("Unexpected revision or architecture")
    print("NOD_BUNDLE_CONTENT_OK", flush=True)

if __name__ == "__main__":
    unpack(pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]))
