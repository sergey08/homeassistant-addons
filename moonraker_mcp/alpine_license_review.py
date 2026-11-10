"""Triage installed Alpine APKv2 package license expressions for maintainer review.

This is not legal advice and does not authorize distribution. Records are read
from offline installed database fields P/V/L, not remote index metadata.
"""
import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path

FIELDS=("package","version","license_expression","review_category","review_status")
TOKEN=re.compile(r"[A-Za-z][A-Za-z0-9.+-]*")
COPYLEFT=re.compile(r"(?i)(?:^|[^a-z])(a?gpl|lgpl|mpl|epl|cddl|osl|eupl|cc-by-sa|artistic)(?:[-.0-9+]|$)")
PERMISSIVE=re.compile(r"(?i)^(?:MIT|BSD(?:-[0-9]+-Clause)?|Apache-2[.]0|ISC|Zlib|0BSD|Unlicense|CC0-1[.]0|Public-Domain)(?:\s+OR\s+(?:MIT|BSD(?:-[0-9]+-Clause)?|Apache-2[.]0|ISC|Zlib|0BSD|Unlicense|CC0-1[.]0|Public-Domain))*$")


def read_records(text):
    records=[]
    current={}
    for line in text.splitlines():
        if not line.strip():
            continue
        if len(line)<3 or line[1]!=":" or line[0] not in "PVL":
            raise ValueError("Unexpected APK metadata line")
        name={"P":"package","V":"version","L":"license_expression"}[line[0]]
        if name in current:
            if set(current) != set(("package","version","license_expression")):
                raise ValueError("Incomplete APK record")
            records.append(current)
            current={}
        value=line[2:].strip()
        if not value or len(value)>2000:
            raise ValueError("Missing or oversized APK field")
        current[name]=value
    if current:
        if set(current)!=set(("package","version","license_expression")):
            raise ValueError("Trailing incomplete APK record")
        records.append(current)
    if not records:
        raise ValueError("Empty APK package metadata")
    seen=set()
    for row in records:
        key=(row["package"],row["version"])
        if key in seen:
            raise ValueError("Duplicated installed APK package")
        seen.add(key)
    return records


def classify(expression):
    if not isinstance(expression,str) or not expression.strip():
        return "UNKNOWN"
    if COPYLEFT.search(expression):
        return "COPYLEFT_OR_RECIPROCAL_REVIEW"
    if PERMISSIVE.fullmatch(expression.strip()):
        return "STANDARD_PERMISSIVE_CANDIDATE"
    return "OTHER_OR_COMPOUND_REVIEW"


def report(records, out):
    out.mkdir(parents=True,exist_ok=True)
    rows=[]
    for record in records:
        category=classify(record["license_expression"])
        rows.append(dict(record,review_category=category,review_status="PENDING"))
    with (out/"alpine-license-review.csv").open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(sorted(rows,key=lambda x:x["package"]))
    summary={"installed_packages":len(rows),
             "by_category":dict(sorted(Counter(r["review_category"] for r in rows).items())),
             "release_clearance":False,
             "warning":"Regex triage for human legal review; SPDX expressions and obligations are NOT validated"}
    (out/"alpine-license-review-summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
    print(json.dumps(summary,sort_keys=True))
    for row in rows:
        if row["review_category"] != "STANDARD_PERMISSIVE_CANDIDATE":
            print("REVIEW_APK:",row["package"],row["version"],row["license_expression"],row["review_category"])
    return summary


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("metadata",type=Path)
    parser.add_argument("output",type=Path)
    args=parser.parse_args()
    report(read_records(args.metadata.read_text()),args.output)


if __name__=="__main__":
    main()
