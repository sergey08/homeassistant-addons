"""Explicit stable-release vulnerability gate for Trivy container reports.

Development CI intentionally reports vulnerabilities without blocking the
developer's feedback loop. Maintainers invoke this gate before stable release;
there is no waiver or automatic ignore mechanism.
"""
import argparse
import json
from collections import Counter
from pathlib import Path


def counts(report):
    results = report.get("Results")
    if not isinstance(results, list):
        raise ValueError("Invalid or incomplete Trivy JSON: missing Results list")
    out = Counter()
    for item in results:
        if not isinstance(item, dict):
            raise ValueError("Invalid Trivy result")
        for vuln in item.get("Vulnerabilities") or []:
            if not isinstance(vuln, dict) or not vuln.get("VulnerabilityID"):
                raise ValueError("Invalid vulnerability finding")
            out[str(vuln.get("Severity", "UNKNOWN")).upper()] += 1
    return out


def gate(report):
    findings = counts(report)
    return findings, not any(findings[k] for k in ("HIGH", "CRITICAL"))


def main():
    parser = argparse.ArgumentParser(description="Fail stable releases with critical/high Trivy findings")
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    findings, safe = gate(json.loads(args.report.read_text()))
    for level in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"):
        print(f"{level}: {findings[level]}")
    if not safe:
        print("BLOCKED: high or critical vulnerabilities require remediation and re-scan")
        return 1
    print("Vulnerability threshold passed; licensing and other release gates still apply")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
