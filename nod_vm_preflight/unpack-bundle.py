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
        archive_name = "nod-server-linux-amd64-" + REV + ".tar.gz"
        names = [i.filename for i in members]
        if sorted(names) == sorted([archive_name, archive_name + ".sha256"]):
            i = z.getinfo(archive_name)
            checksum = z.getinfo(archive_name + ".sha256")
            for item in (i, checksum):
                if stat.S_IFMT(item.external_attr >> 16) not in (0, stat.S_IFREG):
                    raise ValueError("Unsafe nested archive member")
            if i.file_size > LIMIT or checksum.file_size > 4096:
                raise ValueError("Nested archive size limit")
            fields = z.read(checksum).decode("ascii").split()
            if len(fields) != 2 or fields[1].lstrip("*") != archive_name:
                raise ValueError("Unexpected nested checksum format")
            digest = fields[0].lower()
            if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                raise ValueError("Invalid nested checksum")
            with tempfile.TemporaryFile(dir=dest.parent) as tmp:
                h = hashlib.sha256()
                with z.open(i) as stream:
                    while chunk := stream.read(1024**2):
                        h.update(chunk)
                        tmp.write(chunk)
                if h.hexdigest() != digest:
                    raise ValueError("Nested archive checksum mismatch")
                print("NOD_NESTED_ARCHIVE_VERIFIED", flush=True)
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
