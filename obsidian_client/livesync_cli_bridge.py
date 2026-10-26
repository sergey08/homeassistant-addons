"""Isolated CLI bridge for official Self-hosted LiveSync.

No shell, no remote CouchDB writes, no subprocess invocation unless an explicit
integration layer calls this module. The CLI owns protocol encoding.
"""
from pathlib import Path
import os
import re
import subprocess

class CLIUnavailable(RuntimeError):
    pass

def validate_cli_installation(binary, database_directory):
    executable = Path(binary)
    database = Path(database_directory)
    if not executable.is_absolute() or not executable.is_file():
        raise CLIUnavailable("cli_binary_missing")
    if not database.is_absolute() or not database.is_dir():
        raise CLIUnavailable("cli_database_missing")
    if database.is_symlink() or executable.is_symlink():
        raise CLIUnavailable("symlink_not_allowed")
    if not os.access(database, os.R_OK | os.W_OK | os.X_OK):
        raise CLIUnavailable("cli_database_unwritable")
    if executable.suffix not in (".cjs", ".js"):
        raise CLIUnavailable("unsupported_cli_entrypoint")
    if not os.access(executable, os.R_OK):
        raise CLIUnavailable("cli_entrypoint_unreadable")
    return str(executable), str(database)

def prepare_put_command(binary, database_directory, note_path):
    from livesync_write_preflight import validate_write_request
    validate_write_request(note_path, "", None, creating=True)
    executable, database = validate_cli_installation(binary, database_directory)
    return ["/usr/local/bin/node", executable, database, "put", note_path]

def put_local_only(binary, database_directory, note_path, content, *, timeout=30):
    """Write to the CLI's LOCAL database only; never invokes 'sync'.

    A later sync requires a separate explicit authorization and isolated tests.
    """
    if not isinstance(content, str) or len(content.encode("utf-8")) > 2_000_000:
        raise ValueError("invalid_content")
    argv = prepare_put_command(binary, database_directory, note_path)
    try:
        result = subprocess.run(argv, input=content, text=True, capture_output=True,
                                timeout=timeout, check=False, shell=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CLIUnavailable("cli_execution_failed") from exc
    if result.returncode:
        raise CLIUnavailable("cli_put_failed")
    return True

def read_local_note(binary, database_directory, note_path, *, timeout=15):
    """Read a note from the isolated CLI database, without contacting remote."""
    argv = prepare_put_command(binary, database_directory, note_path)
    argv[3] = "cat"
    try:
        result = subprocess.run(argv, capture_output=True, timeout=timeout,
                                check=False, shell=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CLIUnavailable("cli_read_failed") from exc
    if result.returncode or len(result.stdout) > 2_000_000:
        raise CLIUnavailable("cli_read_failed")
    try:
        return result.stdout.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CLIUnavailable("cli_invalid_encoding") from exc


def verify_local_roundtrip(binary, database_directory, note_path, content):
    """Read-back verification after a local-only write, without syncing."""
    put_local_only(binary, database_directory, note_path, content)
    if read_local_note(binary, database_directory, note_path) != content:
        raise CLIUnavailable("cli_roundtrip_mismatch")
    return True

def cli_local_status(binary, database_directory):
    """Inspect local CLI prerequisites without reading note contents or syncing."""
    executable, database = validate_cli_installation(binary, database_directory)
    root = Path(database)
    return {
        "entrypoint_present": Path(executable).is_file(),
        "database_directory_present": root.is_dir(),
        "settings_present": (root / ".livesync" / "settings.json").is_file(),
        "livesync_directory_present": (root / ".livesync").is_dir(),
        "remote_write_ready": False,
    }

def verify_local_cli_runtime(binary, database_directory, *, timeout=10):
    """Run CLI help only; never touch a remote database or mutate a note."""
    executable, _database = validate_cli_installation(binary, database_directory)
    try:
        result = subprocess.run(
            ["/usr/local/bin/node", executable, "--help"],
            capture_output=True, timeout=timeout, check=False, shell=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CLIUnavailable("cli_runtime_failed") from exc
    if result.returncode != 0:
        raise CLIUnavailable("cli_runtime_failed")
    return True

def sync_configured_remote(binary, database_directory, *, timeout=120):
    """Explicit replication only after local settings exist; never fetch/rebuild.

    Caller must enforce authorization, conflict checks and safe UI flow.
    This method is intentionally NOT exposed by a web route.
    """
    executable, database = validate_cli_installation(binary, database_directory)
    if not (Path(database) / ".livesync" / "settings.json").is_file():
        raise CLIUnavailable("cli_settings_missing")
    try:
        result = subprocess.run(
            ["/usr/local/bin/node", executable, database, "sync"],
            capture_output=True, timeout=timeout, check=False, shell=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CLIUnavailable("cli_sync_failed") from exc
    if result.returncode:
        raise CLIUnavailable("cli_sync_failed")
    return True

def safe_update_local_note(binary, database_directory, note_path, expected_content, new_content):
    """Optimistic local conflict check; never overwrite a changed local note."""
    from livesync_write_preflight import validate_write_request
    validate_write_request(note_path, new_content, None, creating=True)
    # Local optimistic concurrency uses exact content comparison, not CouchDB _rev.
    if not isinstance(expected_content, str):
        raise ValueError("invalid_expected_content")
    notes = list_local_note_paths(binary, database_directory)
    if (note_path not in notes or notes[note_path].get("conflict", True) or
            any(existing != note_path and existing.casefold() == note_path.casefold() for existing in notes)):
        raise CLIUnavailable("cli_local_conflict")
    current = read_local_note(binary, database_directory, note_path)
    if current != expected_content:
        raise CLIUnavailable("cli_local_conflict")
    return verify_local_roundtrip(binary, database_directory, note_path, new_content)

def safe_create_local_note(binary, database_directory, note_path, content):
    """Create only when the note is absent from the local CLI database.

    This does not guarantee remote uniqueness; the caller must sync and check
    the remote state before publishing any new note.
    """
    from livesync_write_preflight import validate_write_request
    validate_write_request(note_path, content, None, creating=True)
    notes = list_local_note_paths(binary, database_directory)
    if any(existing.casefold() == note_path.casefold() for existing in notes):
        raise CLIUnavailable("cli_note_already_exists")
    return verify_local_roundtrip(binary, database_directory, note_path, content)

def list_local_note_paths(binary, database_directory, *, timeout=30):
    """Query official CLI ls, rejecting ambiguous or malformed output."""
    executable, database = validate_cli_installation(binary, database_directory)
    try:
        result = subprocess.run(
            ["/usr/local/bin/node", executable, database, "ls"],
            capture_output=True, timeout=timeout, check=False, shell=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CLIUnavailable("cli_list_failed") from exc
    if result.returncode or len(result.stdout) > 2_000_000:
        raise CLIUnavailable("cli_list_failed")
    try:
        lines = result.stdout.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise CLIUnavailable("cli_list_invalid_encoding") from exc
    # Pinned upstream CLI documents: path<TAB>size<TAB>mtime<TAB>revision[*].
    # Reject non-data output rather than treating it as an empty database.
    notes = {}
    for line in lines:
        fields = line.split("\\t") if "\\t" in line else line.split("\t")
        if len(fields) != 4:
            raise CLIUnavailable("cli_list_invalid_format")
        path, size, mtime, revision = fields
        from livesync_write_preflight import validate_write_request, UnsafeWrite
        try:
            validate_write_request(path, "", None, creating=True)
        except UnsafeWrite as exc:
            raise CLIUnavailable("cli_list_invalid_format") from exc
        if (not size.isdigit() or not mtime.isdigit() or
                not re.fullmatch(r"[1-9][0-9]*-[0-9a-fA-F]{32}\*?", revision) or
                path in notes):
            raise CLIUnavailable("cli_list_invalid_format")
        notes[path] = {"size": int(size), "mtime": int(mtime),
                       "revision": revision.rstrip("*"), "conflict": revision.endswith("*")}
    return notes
