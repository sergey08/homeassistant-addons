from pathlib import Path
import os
import shutil
import datetime
from mcp.server.fastmcp import FastMCP

ROOT = Path("/vault").resolve()
TRASH = Path("/trash").resolve()
mcp = FastMCP("Obsidian HA", host="0.0.0.0", port=8765, stateless_http=True, json_response=True)


def note_path(name: str, must_exist: bool = False) -> Path:
    if not name or "\\" in name or "\x00" in name:
        raise ValueError("Invalid note name")
    p = Path(name)
    if p.is_absolute() or ".." in p.parts or p.suffix.lower() != ".md" or any(part.startswith(".") for part in p.parts):
        raise ValueError("Only Markdown (.md) files inside the vault are allowed")
    dest = ROOT / p
    if not dest.resolve().is_relative_to(ROOT):
        raise ValueError("Path is outside the vault")
    if must_exist and (not dest.is_file() or dest.is_symlink()):
        raise FileNotFoundError(name)
    return dest


@mcp.tool()
def list_notes() -> list[str]:
    """List Markdown notes in the Obsidian vault."""
    return sorted(
        str(p.relative_to(ROOT))
        for p in ROOT.rglob("*.md")
        if p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(ROOT)
    )


@mcp.tool()
def search_notes(text: str, max_results: int = 30) -> list[dict]:
    """Search note contents and return matching line excerpts."""
    if not text or len(text) > 200:
        raise ValueError("Invalid search text")
    found = []
    for name in list_notes():
        p = note_path(name, True)
        for line_no, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if text.casefold() in line.casefold():
                found.append({"note": name, "line": line_no, "excerpt": line[:400]})
                if len(found) >= max(1, min(max_results, 100)):
                    return found
    return found


@mcp.tool()
def read_note(name: str) -> str:
    """Read the complete contents of a Markdown note."""
    return note_path(name, True).read_text(encoding="utf-8")


@mcp.tool()
def write_note(name: str, content: str, overwrite: bool = False) -> str:
    """Create a Markdown note. Replacing an existing note requires overwrite=True."""
    p = note_path(name)
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists() and not overwrite:
        raise FileExistsError("Note already exists; use overwrite=True to replace it")
    if p.exists() and (not p.is_file() or p.is_symlink()):
        raise ValueError("Invalid destination")
    if p.exists():
        backup = TRASH / "versions" / datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%f") / name
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, backup)
    # Use a unique, exclusively created temporary file: fixed names can be symlinks.
    import tempfile
    fd, temp_name = tempfile.mkstemp(prefix=".mcp-", suffix=".tmp", dir=p.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            out.write(content)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temp_name, p)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    return f"Saved: {name}"


@mcp.tool()
def append_note(name: str, content: str) -> str:
    """Append content to an existing Markdown note."""
    p = note_path(name, True)
    with p.open("a", encoding="utf-8") as f:
        f.write(content)
    return f"Updated: {name}"


@mcp.tool()
def rename_note(source: str, destination: str) -> str:
    """Move or rename a note without overwriting an existing destination."""
    src, dst = note_path(source, True), note_path(destination)
    if dst.exists():
        raise FileExistsError(destination)
    dst.parent.mkdir(parents=True, exist_ok=True)
    src.rename(dst)
    return f"Moved: {source} -> {destination}"


@mcp.tool()
def delete_note(name: str) -> str:
    """Move a note to private recoverable trash instead of permanently deleting it."""
    p = note_path(name, True)
    dest = TRASH / "deleted" / datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%f") / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(p), str(dest))
    return f"Removed from vault: {name}. Recoverable copy retained."


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
