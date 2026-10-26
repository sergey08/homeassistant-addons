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

def validate_remote_configuration(options):
    """Validate configured CouchDB/E2EE options without network or side effects.

    Returns non-secret readiness flags. This does not authorize replication.
    """
    from urllib.parse import urlsplit
    configured = options if isinstance(options, dict) else {}
    uri = configured.get("couchdb_url")
    dbname = configured.get("couchdb_database")
    username = configured.get("couchdb_username")
    password = configured.get("couchdb_password")
    encrypted = configured.get("livesync_encryption_enabled") is True
    passphrase = configured.get("livesync_e2ee_passphrase")
    valid_url = False
    if isinstance(uri, str):
        try:
            parsed = urlsplit(uri)
            valid_url = (
                parsed.scheme in ("http", "https")
                and bool(parsed.hostname)
                and parsed.username is None and parsed.password is None
                and not parsed.path.strip("/") and not parsed.query and not parsed.fragment
            )
        except ValueError:
            valid_url = False
    valid_db = isinstance(dbname, str) and bool(re.fullmatch(r"[a-z][a-z0-9_$()+/-]*", dbname))
    valid_auth = isinstance(username, str) and bool(username.strip()) and isinstance(password, str) and bool(password)
    valid_crypto = encrypted and isinstance(passphrase, str) and bool(passphrase)
    return {
        "endpoint_valid": valid_url,
        "database_valid": valid_db,
        "credentials_present": valid_auth,
        "encryption_ready": valid_crypto,
        "configuration_complete": bool(valid_url and valid_db and valid_auth and valid_crypto),
        "remote_writes_enabled": False,
    }


def prepare_official_cli_settings(config):
    """Build official CLI settings in memory; never replicate or expose secrets.

    A separate, explicit setup operation must persist these settings. No
    background sync or automatic activation is permitted.
    """
    from urllib.parse import urlsplit
    if not validate_remote_configuration(config)["configuration_complete"]:
        raise CLIUnavailable("cli_remote_config_incomplete")
    uri = config["couchdb_url"].rstrip("/")
    parsed = urlsplit(uri)
    if parsed.scheme == "http" and parsed.hostname not in (
        "localhost", "127.0.0.1", "::1"
    ) and not (parsed.hostname or "").endswith(".internal"):
        # Plain HTTP is acceptable only for an explicitly configured private
        # network endpoint. Never assume arbitrary public HTTP is safe.
        import ipaddress
        try:
            ip = ipaddress.ip_address(parsed.hostname)
            private = ip.is_private
        except ValueError:
            private = False
        if not private and not re.fullmatch(r"[0-9a-f]{8}-[a-z0-9_-]+", parsed.hostname or ""):
            raise CLIUnavailable("cli_remote_plain_http_untrusted")
    # Official CLI >= pinned build selects a remote via activeConfigurationId.
    # Legacy couchDB_* fields alone are NOT registered remotes.
    from urllib.parse import quote, urlencode
    from uuid import uuid4
    user = quote(config["couchdb_username"], safe="")
    password = quote(config["couchdb_password"], safe="")
    host_path = uri.split("://", 1)[1]
    connection = (
        f"sls+{parsed.scheme}://{user}:{password}@{host_path}"
        f"?{urlencode({'db': config['couchdb_database']})}"
    )
    remote_id = "ha-" + uuid4().hex
    return {
        "remoteConfigurations": {
            remote_id: {
                "id": remote_id,
                "name": "Home Assistant CouchDB",
                "uri": connection,
                "isEncrypted": False,
            }
        },
        "activeConfigurationId": remote_id,
        "couchDB_URI": uri,
        "couchDB_USER": config["couchdb_username"],
        "couchDB_PASSWORD": config["couchdb_password"],
        "couchDB_DBNAME": config["couchdb_database"],
        "liveSync": False,
        "syncOnSave": False,
        "syncOnStart": False,
        "encrypt": True,
        "passphrase": config["livesync_e2ee_passphrase"],
        "usePluginSync": False,
        "isConfigured": True,
    }


def install_official_cli_settings(config, database_directory):
    """Install settings only in the isolated CLI directory; never contact remote.

    Existing settings are never overwritten, so changing a vault requires a
    separate reviewed migration instead of silently repointing the client.
    """
    import json
    import stat
    settings = prepare_official_cli_settings(config)
    root = Path(database_directory)
    if not root.is_absolute() or not root.is_dir() or root.is_symlink():
        raise CLIUnavailable("cli_database_missing")
    folder = root / ".livesync"
    if folder.is_symlink():
        raise CLIUnavailable("cli_settings_symlink")
    folder.mkdir(mode=0o700, exist_ok=True)
    if not folder.is_dir() or folder.is_symlink():
        raise CLIUnavailable("cli_settings_directory_invalid")
    os.chmod(folder, 0o700)
    target = folder / "settings.json"
    if target.exists() or target.is_symlink():
        raise CLIUnavailable("cli_settings_already_exist")
    descriptor = None
    try:
        descriptor = os.open(str(target), os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            descriptor = None
            json.dump(settings, handle, ensure_ascii=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(target, stat.S_IRUSR | stat.S_IWUSR)
    except (OSError, ValueError) as exc:
        if descriptor is not None:
            os.close(descriptor)
        try:
            target.unlink()
        except OSError:
            pass
        raise CLIUnavailable("cli_settings_install_failed") from exc
    return {"installed": True, "remote_synced": False, "remote_writes_enabled": False}


def probe_remote_status(config, *, timeout=45):
    """Read-only CLI remote-status probe using ephemeral settings and database."""
    import tempfile
    with tempfile.TemporaryDirectory(prefix="obsidian-remote-status-") as temp:
        database = Path(temp) / "db"
        database.mkdir(mode=0o700)
        install_official_cli_settings(config, str(database))
        binary = "/opt/livesync-cli/dist/index.cjs"
        executable, _ = validate_cli_installation(binary, str(database))
        try:
            result = subprocess.run(
                ["/usr/local/bin/node", executable, str(database), "remote-status"],
                capture_output=True, timeout=timeout, check=False, shell=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise CLIUnavailable("cli_status_probe_execution_failed") from exc
        # Parse only a strict allowlist of compatibility fields.
        # Never return raw CLI output, note paths or credentials.
        import json
        safe = {"cli_exit_ok": result.returncode == 0,
                "remote_writes_enabled": False}
        if result.returncode == 0:
            try:
                raw = result.stdout.decode("utf-8", errors="strict")
                start = raw.find("{")
                end = raw.rfind("}")
                status = json.loads(raw[start:end + 1]) if start >= 0 and end > start else {}
                if isinstance(status, dict):
                    # Traverse only bounded, known metadata names, never content.
                    allowed = {"version", "schemaVersion", "remoteVersion",
                               "acceptedNodeCount", "locked", "isLocked",
                               "nodeCount", "compatibility", "minimumVersion",
                               "status", "info", "database", "replication",
                               "node", "remote", "sync", "compatibilityStatus"}
                    found = {}
                    def inspect(obj, prefix="", depth=0):
                        if depth > 3 or not isinstance(obj, dict):
                            return
                        for key, value in list(obj.items())[:60]:
                            if key not in allowed:
                                continue
                            name = prefix + key
                            if isinstance(value, dict):
                                inspect(value, name + ".", depth + 1)
                            elif type(value) in (bool, int) or (
                                isinstance(value, str) and len(value) <= 32
                                and re.fullmatch(r"[A-Za-z0-9._-]+", value)):
                                found[name] = value
                    inspect(status)
                    safe["compatibility_metadata"] = found
            except (ValueError, UnicodeError):
                pass
        return safe


def probe_official_remote_registration(config, *, timeout=30):
    """Inspect remote registration without revealing remote URI or credentials."""
    import tempfile
    with tempfile.TemporaryDirectory(prefix="obsidian-remote-registration-") as temp:
        database = Path(temp) / "db"
        database.mkdir(mode=0o700)
        install_official_cli_settings(config, str(database))
        executable, _ = validate_cli_installation(
            "/opt/livesync-cli/dist/index.cjs", str(database))
        try:
            result = subprocess.run(
                ["/usr/local/bin/node", executable, str(database), "remote-ls"],
                capture_output=True, timeout=timeout, check=False, shell=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise CLIUnavailable("cli_remote_registration_failed") from exc
        if result.returncode:
            raise CLIUnavailable("cli_remote_registration_failed")
        # Never return raw output: remote-ls includes redacted but private URIs.
        rows = result.stdout.decode("utf-8", errors="replace").splitlines()
        active = sum(1 for line in rows if len(line.split("\\t")) == 4
                     and line.split("\\t")[2] == "active")
        return {"registered_remote_count": sum(
                    1 for line in rows if len(line.split("\\t")) == 4),
                "active_remote_count": active, "remote_writes_enabled": False}


def publish_isolated_test_note(config, note_path, content, *, timeout=120):
    """Publish one explicitly chosen test note from a disposable CLI database.

    Does not sync the editor's persistent database, which may contain drafts.
    Only intended for a unique new test path after a remote absence check.
    """
    import tempfile
    from livesync_write_preflight import validate_write_request
    validate_write_request(note_path, content, None, creating=True)
    if not note_path.startswith("Pruebas ChatGPT/"):
        raise CLIUnavailable("test_namespace_required")
    with tempfile.TemporaryDirectory(prefix="obsidian-publish-one-") as temp:
        database = Path(temp) / "db"
        database.mkdir(mode=0o700)
        install_official_cli_settings(config, str(database))
        binary = "/opt/livesync-cli/dist/index.cjs"
        verify_local_roundtrip(binary, str(database), note_path, content)
        sync_configured_remote(binary, str(database), timeout=timeout)
        return {"cli_sync_completed": True, "path": note_path,
                "verified_remotely": False}


def fetch_remote_to_disposable_database(config, *, timeout=120):
    """Fetch remote notes into a new temporary CLI database, never into live local data.

    The official CLI 'fetch --force' replaces only the disposable local database.
    It must not be used to overwrite the persistent editor database.
    """
    import tempfile
    settings = prepare_official_cli_settings(config)
    with tempfile.TemporaryDirectory(prefix="obsidian-remote-preview-") as temp:
        database = Path(temp) / "db"
        vault = Path(temp) / "vault"
        database.mkdir(mode=0o700)
        vault.mkdir(mode=0o700)
        install_official_cli_settings(config, str(database))
        binary = "/opt/livesync-cli/dist/index.cjs"
        executable, _ = validate_cli_installation(binary, str(database))
        try:
            result = subprocess.run(
                ["/usr/local/bin/node", executable, str(database), "fetch",
                 "--force", "--vault", str(vault)],
                capture_output=True, timeout=timeout, check=False, shell=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise CLIUnavailable("cli_preview_fetch_failed") from exc
        if result.returncode:
            # Only fixed categories: never expose CLI output or credentials.
            output = (result.stderr + result.stdout).decode("utf-8", errors="replace").lower()[-12000:]
            if any(term in output for term in ("unauthorized", "forbidden", "authentication failed", "401", "403")):
                reason = "authentication"
            elif any(term in output for term in ("econnrefused", "enotfound", "getaddrinfo", "timeout", "network")):
                reason = "network"
            elif any(term in output for term in ("decrypt", "passphrase", "encryption", "encrypted")):
                reason = "encryption"
            elif any(term in output for term in ("no remote", "remote not", "not configured", "not initialized")):
                reason = "remote_configuration"
            elif any(term in output for term in ("404", "not found", "database does not exist")):
                reason = "database"
            elif any(term in output for term in ("database is locked", "remote database is locked", "node_locked", "node_cleaned")):
                reason = "remote_locked"
            elif any(term in output for term in ("version mismatch", "incompatible", "compatibility rejection")):
                reason = "version_incompatible"
            elif any(term in output for term in ("fetch failed", "failed to fetch", "failed to retrieve")):
                reason = "fetch_operation"
            elif any(term in output for term in ("database is locked", "database locked", "database closed")):
                reason = "local_database"
            elif any(term in output for term in ("typeerror", "referenceerror", "syntaxerror", "uncaught", "exception")):
                reason = "cli_exception"
            else:
                reason = "cli_failure"
            raise CLIUnavailable("cli_preview_" + reason)
        notes = list_local_note_paths(binary, str(database))
        return {"note_count": len(notes), "paths": sorted(notes),
                "remote_writes_enabled": False, "persistent_local_modified": False}


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
        # Do not expose stderr, stdout, remote URLs, passwords or note content.
        output = (result.stderr + result.stdout).decode("utf-8", errors="replace").lower()[-16000:]
        if any(x in output for x in ("node_locked", "node_cleaned", "remote database is locked", "please unlock")):
            reason = "remote_locked"
        elif any(x in output for x in ("version mismatch", "incompatible", "compatibility rejection")):
            reason = "version_incompatible"
        elif any(x in output for x in ("unauthorized", "forbidden", "authentication failed", "401", "403")):
            reason = "authentication"
        elif any(x in output for x in ("decrypt", "passphrase", "encryption failed")):
            reason = "encryption"
        elif any(x in output for x in ("econnrefused", "enotfound", "getaddrinfo", "network error")):
            reason = "network"
        elif any(x in output for x in ("typeerror", "referenceerror", "uncaught", "exception")):
            reason = "cli_exception"
        else:
            reason = "unknown"
        raise CLIUnavailable("cli_sync_" + reason)
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
    folded_paths = set()
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
                path in notes or path.casefold() in folded_paths):
            raise CLIUnavailable("cli_list_invalid_format")
        folded_paths.add(path.casefold())
        notes[path] = {"size": int(size), "mtime": int(mtime),
                       "revision": revision.rstrip("*"), "conflict": revision.endswith("*")}
    return notes
