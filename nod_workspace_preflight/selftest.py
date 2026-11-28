"""Fixed synthetic preflight. No user files, secrets, network or model calls."""
import os
import pathlib
import signal
import sys
import subprocess
import tempfile
import time
import docx
import openpyxl
from pypdf import PdfReader, PdfWriter

assert os.getuid() == os.getgid() == 1000
status = dict(line.split(":", 1) for line in pathlib.Path("/proc/self/status").read_text().splitlines() if ":" in line)
assert all(int(status[key].strip(), 16) == 0 for key in ("CapEff", "CapPrm", "CapBnd", "CapAmb"))
assert status["NoNewPrivs"].strip() == "1"
assert not pathlib.Path("/var/run/docker.sock").exists()
assert not pathlib.Path("/data/options.json").exists() or not os.access("/data/options.json", os.R_OK)
assert "SUPERVISOR_TOKEN" not in os.environ
with tempfile.TemporaryDirectory(prefix="nod-synthetic-", dir="/workspace") as folder:
    root = pathlib.Path(folder)
    document = docx.Document()
    document.add_paragraph("Nod workspace synthetic fixture")
    document.save(root / "fixture.docx")
    assert docx.Document(root / "fixture.docx").paragraphs[0].text == "Nod workspace synthetic fixture"
    book = openpyxl.Workbook()
    book.active["A1"] = 42
    book.save(root / "fixture.xlsx")
    assert openpyxl.load_workbook(root / "fixture.xlsx").active["A1"].value == 42
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=400)
    writer.write(root / "fixture.pdf")
    assert len(PdfReader(root / "fixture.pdf").pages) == 1
    assert subprocess.check_output(["node", "-e", "console.log(42)"], text=True).strip() == "42"
print("NOD_WORKSPACE_SYNTHETIC_ARTIFACTS_OK", flush=True)
print("NOD_WORKSPACE_UNPRIVILEGED_READY", flush=True)
if sys.argv[1:] == ['--once']:
    sys.exit(0)
signal.signal(signal.SIGTERM, lambda *_: exit(0))
while True:
    time.sleep(5)
