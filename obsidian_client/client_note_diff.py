"""Bounded, read-only Markdown line differences for the independent Client."""
import difflib

MAX_INPUT_BYTES = 256_000
MAX_INPUT_LINES = 5000
MAX_DIFF_LINES = 800
MAX_DIFF_BYTES = 96_000


class DiffUnavailable(ValueError):
    pass


def compare_lines(remote, local):
    """Returns an explicitly bounded unified diff; never resolves conflicts."""
    if not isinstance(remote, str) or not isinstance(local, str):
        raise DiffUnavailable("local_copy_required")
    for content in (remote, local):
        if len(content.encode("utf-8")) > MAX_INPUT_BYTES:
            raise DiffUnavailable("diff_input_too_large")
        if len(content.splitlines(keepends=True)) > MAX_INPUT_LINES:
            raise DiffUnavailable("too_many_lines")
    changed = remote != local
    if not changed:
        return {"different": False, "diff": "", "truncated": False,
                "direction": "remote_to_local", "lines": 0}
    lines = difflib.unified_diff(
        remote.splitlines(keepends=True), local.splitlines(keepends=True),
        fromfile="CouchDB remoto (solo lectura)", tofile="Markdown privado",
        n=3, lineterm="\n")
    parts = []
    byte_count = 0
    truncated = False
    for index, line in enumerate(lines):
        encoded = line.encode("utf-8")
        if index >= MAX_DIFF_LINES or byte_count + len(encoded) > MAX_DIFF_BYTES:
            truncated = True
            break
        parts.append(line)
        byte_count += len(encoded)
    return {"different": True, "diff": "".join(parts), "truncated": truncated,
            "direction": "remote_to_local", "lines": len(parts)}
