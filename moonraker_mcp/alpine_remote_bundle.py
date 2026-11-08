"""Collect exact Alpine source bytes with SHA-512 verification, never claim completeness.

For a release-review artifact ONLY. Missing archives stay missing, not approved.
"""
import argparse
import hashlib
import json
import re
import tempfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from alpine_remote_source_integrity import ALLOWED_HOSTS, COMMIT, MAX_BYTES, CHUNK

ALLOWED_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,160}$")


def fetch_verified(item, directory, *, opener=urlopen):
    name = item["file"]
    expected = item["sha512"]
    if not ALLOWED_NAME.fullmatch(name):
        raise ValueError("Unsafe filename")
    if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{128}", expected):
        raise ValueError("Malformed SHA-512")

    urls = [item["url"]]
    if urlparse(urls[0]).hostname == "gitlab.alpinelinux.org" and name in {
        "apk-tools-v2.14.13.tar.gz", "ca-certificates-20261020.tar.bz2"
    }:
        urls.append("https://distfiles.alpinelinux.org/distfiles/v3.22/" + name)
    problems = []
    for url in urls:
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
            raise ValueError("Unapproved URL")
        destination = directory / name
        h = hashlib.sha512()
        size = 0
        try:
            with tempfile.NamedTemporaryFile(dir=directory, prefix=".partial-", delete=True) as temp:
                request = Request(url, headers={"User-Agent": "MoonrakerMCP-SourceReview/0.1"})
                with opener(request, timeout=90) as source:
                    redirected = urlparse(source.geturl())
                    if redirected.scheme != "https" or redirected.hostname not in ALLOWED_HOSTS:
                        raise ValueError("Unapproved redirect")
                    while True:
                        block = source.read(CHUNK)
                        if not block:
                            break
                        size += len(block)
                        if size > MAX_BYTES:
                            raise ValueError("Source exceeds size limit")
                        h.update(block)
                        temp.write(block)
                if size <= 0 or h.hexdigest() != expected:
                    raise ValueError("Wrong or empty source SHA-512")
                temp.flush()
                # Temporary file closes and deletes on context exit; copy only
                # after success so failures never leave an approved-looking file.
                temp.seek(0)
                with destination.open("xb") as target:
                    while True:
                        block = temp.read(CHUNK)
                        if not block:
                            break
                        target.write(block)
            return {"file": name, "status": "VERIFIED_SHA512", "sha512": expected,
                    "bytes": size, "url": url}
        except (OSError, ValueError, TimeoutError, HTTPError, URLError) as exc:
            destination.unlink(missing_ok=True)
            problems.append(type(exc).__name__)
    return {"file": name, "status": "UNVERIFIED", "error_types": problems}


def collect(manifest_path, out_dir, *, fetcher=fetch_verified):
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    items = manifest.get("items")
    if manifest.get("aports_commit") != COMMIT or not isinstance(items, list) or len(items) != 11:
        raise ValueError("Unexpected Alpine manifest")
    names = [x.get("file") for x in items]
    if len(set(names)) != 11:
        raise ValueError("Duplicate Alpine source")
    out_dir.mkdir(parents=True, exist_ok=True)
    statuses = []
    for item in items:
        record = fetcher(item, out_dir)
        statuses.append(record)
        print(f"{record['status']}: {record['file']}", flush=True)
    good = sum(x["status"] == "VERIFIED_SHA512" for x in statuses)
    report = {"aports_commit": COMMIT, "status": "INCOMPLETE_REVIEW_MATERIAL",
              "verified": good, "expected": 11, "unverified": 11-good,
              "license_approved": False, "corresponding_source_complete": False,
              "items": statuses}
    (out_dir / "MANIFEST.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest", type=Path)
    ap.add_argument("output_dir", type=Path)
    args = ap.parse_args()
    report = collect(args.manifest, args.output_dir)
    print(f"VERIFIED {report['verified']}/11. NOT COMPLETE CORRESPONDING SOURCE.")
    return 0  # Partial results are intentional for review; never interpreted as release pass.


if __name__ == "__main__":
    raise SystemExit(main())
