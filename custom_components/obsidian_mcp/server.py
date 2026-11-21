"""MCP tools ported from the Obsidian MCP application."""
import asyncio
from functools import wraps
from pathlib import Path
import os
import shutil
import datetime
import hashlib
import threading
import fcntl
from contextlib import contextmanager
try:
    from mcp.server.mcpserver import MCPServer
except ModuleNotFoundError as err:
    if err.name != "mcp.server.mcpserver":
        raise
    from mcp.server.fastmcp import FastMCP

    MCPServer = None


def create_app(root: Path, trash: Path):
    """Create an isolated server bound to a specific vault."""
    write_lock = threading.RLock()
    if MCPServer is None:
        mcp = FastMCP(
            "Obsidian HA", host="127.0.0.1", stateless_http=True, json_response=True
        )
    else:
        mcp = MCPServer("Obsidian HA", subscriptions=False)

    def tool(func):
        @wraps(func)
        async def run_in_worker(*args, **kwargs):
            return await asyncio.to_thread(func, *args, **kwargs)

        mcp.tool()(run_in_worker)
        return func

    @contextmanager
    def vault_write_lock():
        """Serialize MCP edits with Obsidian Client edits on a shared /share vault.

        This protects inter-addon changes, not the independent LiveSync process.
        """
        with write_lock:
            fd = os.open(root / ".obsidian-write.lock",
                         os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(fd, fcntl.LOCK_UN)
            finally:
                os.close(fd)



    def note_path(name: str, must_exist: bool = False) -> Path:
        if not name or "\\" in name or "\x00" in name:
            raise ValueError("Invalid note name")
        p = Path(name)
        if p.is_absolute() or ".." in p.parts or p.suffix.lower() != ".md" or any(part.startswith(".") for part in p.parts):
            raise ValueError("Only Markdown (.md) files inside the vault are allowed")
        dest = root / p
        cursor = root
        for part in p.parts:
            cursor = cursor / part
            if cursor.is_symlink():
                raise ValueError("Symlinked Markdown paths are not allowed")
        if not dest.resolve().is_relative_to(root):
            raise ValueError("Path is outside the vault")
        if must_exist and (not dest.is_file() or dest.is_symlink()):
            raise FileNotFoundError(name)
        return dest


    @tool
    def list_notes() -> list[str]:
        """List Markdown notes in the Obsidian vault."""
        return sorted(
            str(p.relative_to(root))
            for p in root.rglob("*.md")
            if p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(root)
            and not any(parent.is_symlink() for parent in p.parents if parent != root and parent.is_relative_to(root))
        )


    @tool
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


    @tool
    def read_note(name: str) -> str:
        """Read the complete contents of a Markdown note."""
        return note_path(name, True).read_text(encoding="utf-8")


    @tool
    def read_note_with_revision(name: str) -> dict:
        """Read a note with its SHA-256 revision. Pass sha256 as expected_sha256 when editing."""
        with vault_write_lock():
            content = note_path(name, True).read_bytes()
            return {"name": name, "content": content.decode("utf-8"),
                    "sha256": hashlib.sha256(content).hexdigest()}


    @tool
    def note_revision(name: str) -> str:
        """Return SHA-256 of a note for safe optimistic updates."""
        return hashlib.sha256(note_path(name, True).read_bytes()).hexdigest()


    def check_revision(path: Path, expected_sha256: str) -> None:
        """Reject stale edits when a revision is supplied by the caller."""
        if expected_sha256 and (not path.is_file() or
            hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha256):
            raise RuntimeError("Note changed since it was read; refusing modification")


    @tool
    def write_note(name: str, content: str, overwrite: bool = False, expected_sha256: str = "") -> str:
        """Create a Markdown note. Replacing an existing note requires overwrite=True."""
        with vault_write_lock():
            p = note_path(name)
            p.parent.mkdir(parents=True, exist_ok=True)
            if p.exists() and not overwrite:
                raise FileExistsError("Note already exists; use overwrite=True to replace it")
            if p.exists() and (not p.is_file() or p.is_symlink()):
                raise ValueError("Invalid destination")
            check_revision(p, expected_sha256)
            if p.exists():
                backup = trash / "versions" / datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%f") / name
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


    @tool
    def append_note(name: str, content: str, expected_sha256: str = "") -> str:
        """Append content to an existing Markdown note."""
        with vault_write_lock():
            p = note_path(name, True)
            check_revision(p, expected_sha256)
            with p.open("a", encoding="utf-8") as f:
                f.write(content)
            return f"Updated: {name}"


    @tool
    def rename_note(source: str, destination: str, expected_sha256: str = "") -> str:
        """Move or rename a note without overwriting an existing destination."""
        with vault_write_lock():
            src, dst = note_path(source, True), note_path(destination)
            check_revision(src, expected_sha256)
            if dst.exists():
                raise FileExistsError(destination)
            dst.parent.mkdir(parents=True, exist_ok=True)
            src.rename(dst)
            return f"Moved: {source} -> {destination}"


    @tool
    def delete_note(name: str, expected_sha256: str = "") -> str:
        """Move a note to private recoverable trash instead of permanently deleting it."""
        with vault_write_lock():
            p = note_path(name, True)
            check_revision(p, expected_sha256)
            dest = trash / "deleted" / datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%f") / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(p), str(dest))
            return f"Removed from vault: {name}. Recoverable copy retained."

    if MCPServer is None:
        return mcp.streamable_http_app()
    return mcp.streamable_http_app(stateless_http=True, json_response=True)
