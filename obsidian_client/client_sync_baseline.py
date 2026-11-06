"""Private per-note baseline metadata; never modifies notes or CouchDB.

A baseline is created ONLY after an authenticated remote read and a matching
private local copy. A missing baseline is never inferred from a remote revision.
"""
from hashlib import sha256
from pathlib import Path
import json
import os
import re
import tempfile

SHA = re.compile(r"[0-9a-f]{64}\Z")


class BaselineError(ValueError):
    pass


def digest(content):
    if not isinstance(content, str):
        raise BaselineError("invalid_content")
    return sha256(content.encode("utf-8")).hexdigest()


def classify(baseline_hash, remote_content, local_content):
    """Three-way classification. Never treats a missing local copy as unchanged."""
    remote = digest(remote_content)
    local = digest(local_content) if local_content is not None else None
    if baseline_hash is None:
        return {"sync_state": "no_baseline", "baseline_available": False,
                "remote_changed": None, "local_changed": None}
    if not isinstance(baseline_hash, str) or not SHA.fullmatch(baseline_hash):
        raise BaselineError("invalid_baseline")
    if local is None:
        state = "local_missing"
    elif remote == baseline_hash and local == baseline_hash:
        state = "unchanged"
    elif remote != baseline_hash and local == baseline_hash:
        state = "remote_changed"
    elif remote == baseline_hash and local != baseline_hash:
        state = "local_changed"
    elif remote == local:
        state = "same_result_both_changed"
    else:
        state = "conflict_both_changed"
    return {"sync_state": state, "baseline_available": True,
            "remote_changed": remote != baseline_hash,
            "local_changed": None if local is None else local != baseline_hash}


def _filename(root, note_path):
    if (not isinstance(note_path, str) or not note_path.endswith(".md")
            or len(note_path) > 500 or note_path.startswith("/")
            or "\\" in note_path
            or any(p in ("", ".", "..") or p.startswith(".") for p in note_path.split("/"))):
        raise BaselineError("invalid_note_path")
    root = Path(root)
    if not root.is_absolute() or root.is_symlink():
        raise BaselineError("invalid_baseline_root")
    return root / (sha256(note_path.encode("utf-8")).hexdigest() + ".json")


def load_baseline(root, note_path):
    path = _filename(root, note_path)
    if path.is_symlink():
        raise BaselineError("unsafe_baseline")
    try:
        with path.open("rb") as f:
            raw = f.read(4097)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise BaselineError("baseline_unreadable") from exc
    if len(raw) > 4096:
        raise BaselineError("baseline_too_large")
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise BaselineError("baseline_invalid") from exc
    if (not isinstance(data, dict) or data.get("version") != 1
            or data.get("path") != note_path
            or not isinstance(data.get("sha256"), str)
            or not SHA.fullmatch(data["sha256"])):
        raise BaselineError("baseline_invalid")
    return data["sha256"]


def establish_baseline(root, note_path, remote_content, local_content):
    """Explicit private enrollment; require equal verified content; no overwrite."""
    if local_content is None or digest(remote_content) != digest(local_content):
        raise BaselineError("copies_not_identical")
    target = _filename(root, note_path)
    parent = target.parent
    if parent.is_symlink():
        raise BaselineError("invalid_baseline_root")
    parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if target.is_symlink():
        raise BaselineError("unsafe_baseline")
    if target.exists():
        existing = load_baseline(root, note_path)
        if existing == digest(remote_content):
            return {"created": False, "sha256": existing}
        raise BaselineError("baseline_already_exists")
    data = json.dumps({"version": 1, "path": note_path,
                       "sha256": digest(remote_content)}, ensure_ascii=False).encode("utf-8")
    fd, temporary = tempfile.mkstemp(prefix=".obsidian-baseline-", dir=parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        # An existing baseline must never be overwritten, including from another process.
        try:
            os.link(temporary, target, follow_symlinks=False)
        except FileExistsError as exc:
            raise BaselineError("baseline_already_exists") from exc
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return {"created": True, "sha256": digest(remote_content)}
