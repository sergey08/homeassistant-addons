"""Isolated CLI bridge for official Self-hosted LiveSync.

No shell, no remote CouchDB writes, no subprocess invocation unless an explicit
integration layer calls this module. The CLI owns protocol encoding.
"""
from pathlib import Path
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
    if executable.suffix not in (".cjs", ".js"):
        raise CLIUnavailable("unsupported_cli_entrypoint")
    return str(executable), str(database)

def prepare_put_command(binary, database_directory, note_path):
    from livesync_write_preflight import validate_write_request
    validate_write_request(note_path, "", None, creating=True)
    executable, database = validate_cli_installation(binary, database_directory)
    return ["node", executable, database, "put", note_path]

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
