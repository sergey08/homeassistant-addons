"""Evidence collection for exact Go modules missing detected SBOM licenses.

This is not an SPDX classifier or legal clearance. It queries the public Go
module proxy for the exact version from the CycloneDX PURL, verifies with
the default public checksum database, and records LICENSE/NOTICE file hashes.
Never executes downloaded module code.
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit

ROOT_NAMES = re.compile(r"^(?:LICEN[CS]E(?:\..+)?|COPYING(?:\..+)?|NOTICE(?:\..+)?|COPYRIGHT(?:\..+)?|AUTHORS(?:\..+)?)$", re.I)
MODULE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._~!+/-]*$")
VERSION = re.compile(r"^v[0-9]+\.[0-9]+\.[0-9]+(?:[-+][A-Za-z0-9.-]+)?$")
HEADERS = ("name", "version", "purl", "bom_ref", "source_status", "module_sum", "license_file", "license_sha256", "license_bytes", "note")


def module_from_purl(purl, version):
    if not isinstance(purl, str) or not purl.startswith("pkg:golang/"):
        raise ValueError("Not a Go module PURL")
    source = purl.split("#", 1)[0].split("?", 1)[0][len("pkg:golang/"):]
    if "@" not in source:
        raise ValueError("No version in PURL")
    module, purl_version = source.rsplit("@", 1)
    module, purl_version = unquote(module), unquote(purl_version)
    if (not MODULE_NAME.fullmatch(module) or not VERSION.fullmatch(purl_version)
            or purl_version != version or ".." in module.split("/")):
        raise ValueError("Unsafe or inconsistent module reference")
    return module, purl_version


def license_files(path):
    """Find root-level evidence; never follow symlinks or unbounded files."""
    if not path.is_dir() or path.is_symlink():
        raise ValueError("Missing trusted module directory")
    matches = []
    for item in path.iterdir():
        if ROOT_NAMES.fullmatch(item.name) and item.is_file() and not item.is_symlink():
            size = item.stat().st_size
            if 0 < size <= 4 * 1024 * 1024:
                matches.append((item.name, hashlib.sha256(item.read_bytes()).hexdigest(), size))
    return sorted(matches)


def collect(rows, output, timeout=45):
    results = []
    for entry in rows:
        record = {k: str(entry.get(k, "")) for k in HEADERS}
        record["source_status"] = "NOT_CHECKED"
        record["note"] = "No legal conclusion"
        if entry.get("ecosystem") != "golang":
            record["source_status"] = "MANUAL_REVIEW"
            record["note"] = "No verified Go PURL"
            results.append(record)
            continue
        try:
            module, version = module_from_purl(entry["purl"], entry["version"])
            process = subprocess.run(
                ["go", "mod", "download", "-json", module + "@" + version],
                capture_output=True, text=True, timeout=timeout, check=False,
                env={**os.environ, "GOPROXY": "https://proxy.golang.org",
                     "GOSUMDB": "sum.golang.org", "GOPRIVATE": "", "GONOSUMDB": ""},
            )
            if process.returncode or len(process.stdout) > 100000:
                raise ValueError("Exact public module download failed")
            result = json.loads(process.stdout)
            if result.get("Error") or result.get("Path") != module or result.get("Version") != version:
                raise ValueError("Unexpected module metadata")
            if not (isinstance(result.get("Sum"), str) and result["Sum"].startswith("h1:")):
                raise ValueError("No verified Go module checksum")
            record["module_sum"] = result["Sum"]
            location = Path(result.get("Dir", ""))
            files = license_files(location)
            record["source_status"] = "SOURCE_LICENSE_FILES_FOUND" if files else "SOURCE_FILES_NOT_FOUND"
            record["note"] = ("License evidence only: names and hashes; SPDX and obligations require human review"
                              if files else "No bounded root-level license/notice file detected; manual investigation")
            if files:
                for filename, digest, size in files:
                    individual = dict(record)
                    individual.update(license_file=filename, license_sha256=digest,
                                      license_bytes=str(size))
                    results.append(individual)
                continue
        except (ValueError, KeyError, json.JSONDecodeError, subprocess.TimeoutExpired, OSError):
            record["source_status"] = "MANUAL_REVIEW"
            record["note"] = "Unable to verify exact module source and license evidence"
        results.append(record)
    output.mkdir(parents=True, exist_ok=True)
    with (output / "go-license-evidence.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(results)
    # Count unique exact SBOM entries, not extra NOTICE files per module.
    statuses = {}
    for row in results:
        statuses.setdefault(row["bom_ref"], row["source_status"])
    summary = {"reviewed_components": len(statuses),
               "statuses": {key: sum(v == key for v in statuses.values()) for key in sorted(set(statuses.values()))},
               "license_classification": "NOT_PERFORMED",
               "release_clearance": False,
               "note": "File hashes are verifiable evidence, not legal SPDX determinations"}
    (output / "go-license-evidence-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, sort_keys=True))
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("queue", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    with args.queue.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) > 500:
        raise ValueError("Refusing excessive SBOM queue size")
    collect(rows, args.output)


if __name__ == "__main__":
    main()
