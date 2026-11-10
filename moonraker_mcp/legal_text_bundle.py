"""Archive verified, exact-version third-party legal texts for human review.

The archive contains legal text only, not module source, binaries, or keys.
Source hashes are rechecked against the preceding Go evidence inventory.
This does not classify or approve licenses.
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
from zipfile import ZipFile, ZIP_DEFLATED

from go_license_evidence import module_from_purl


def collect_texts(rows, archive_path, *, runner=subprocess.run):
    records = []
    total = 0
    missing = []
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as z:
        for idx, row in enumerate(rows):
            if row.get("source_status") != "SOURCE_LICENSE_FILES_FOUND":
                continue
            ref, filename = row.get("bom_ref", ""), row.get("license_file", "")
            if not filename or "/" in filename or "\\" in filename or filename in (".", ".."):
                raise ValueError("Unsafe legal filename")
            module, version = module_from_purl(row.get("purl", ""), row.get("version", ""))
            result = runner(["go", "mod", "download", "-json", module+"@"+version],
                            capture_output=True, text=True, check=False, timeout=45,
                            env={**os.environ, "GOPROXY": "https://proxy.golang.org",
                                 "GOSUMDB": "sum.golang.org", "GOPRIVATE": "", "GONOSUMDB": ""})
            if result.returncode or len(result.stdout) > 100000:
                missing.append(ref)
                continue
            data = json.loads(result.stdout)
            if (data.get("Path") != module or data.get("Version") != version
                    or data.get("Sum") != row.get("module_sum")):
                raise ValueError("Module checksum or identity changed")
            root = Path(data.get("Dir", ""))
            source = root / filename
            if not root.is_dir() or root.is_symlink() or not source.is_file() or source.is_symlink():
                missing.append(ref)
                continue
            size = source.stat().st_size
            if not 0 < size <= 4 * 1024 * 1024 or total + size > 16 * 1024 * 1024:
                raise ValueError("Legal-text bundle exceeds size limits")
            raw = source.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            if digest != row.get("license_sha256") or len(raw) != int(row.get("license_bytes", "0")):
                raise ValueError("License file changed relative to earlier verified evidence")
            destination = f"legal/{idx:04d}/{filename}"
            z.writestr(destination, raw)
            total += size
            records.append({"bom_ref": ref, "module": module, "version": version,
                            "module_sum": data["Sum"], "license_file": filename,
                            "license_sha256": digest, "archive_path": destination})
        z.writestr("MANIFEST.json", json.dumps(
            {"entries": records, "missing": sorted(set(missing)),
             "release_approved": False,
             "warning": "Source-file evidence only; all legal obligations require human review"},
            indent=2, sort_keys=True))
    return {"files": len(records), "bytes": total,
            "modules_with_files": len(set(r["bom_ref"] for r in records)),
            "missing_components": len(set(missing)), "release_approved": False}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("evidence_csv", type=Path)
    ap.add_argument("output_zip", type=Path)
    args = ap.parse_args()
    with args.evidence_csv.open(newline="", encoding="utf-8") as f:
        entries = list(csv.DictReader(f))
    if len(entries) > 500:
        raise ValueError("Excessive legal files")
    summary = collect_texts(entries, args.output_zip)
    (args.output_zip.parent / "legal-text-bundle-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
