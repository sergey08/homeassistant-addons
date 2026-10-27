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
        # Match the publisher's registration and activation sequence.
        configure_disposable_remote_with_cli(config, database)
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
                    # Only property names, never values. Useful when upstream
                    # changes its remote-status schema.
                    safe["status_shape"] = sorted(
                        key for key in status
                        if isinstance(key, str)
                        and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,35}", key)
                        and not any(secret in key.lower() for secret in (
                            "password", "passphrase", "token", "credential",
                            "secret", "uri", "url", "path", "username", "user",
                            "document", "content", "note", "header", "cookie",
                            "key", "salt"))
                    )[:25]
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
        import json
        settings_path = database / ".livesync" / "settings.json"
        settings_data = json.loads(settings_path.read_text(encoding="utf-8"))
        declared_remotes = settings_data.get("remoteConfigurations", {})
        declared_active = settings_data.get("activeConfigurationId", "")
        executable, _ = validate_cli_installation(
            "/opt/livesync-cli/dist/index.cjs", str(database))
        try:
            result = subprocess.run(
                ["/usr/local/bin/node", executable, str(database), "--verbose", "remote-ls"],
                capture_output=True, timeout=timeout, check=False, shell=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise CLIUnavailable("cli_remote_registration_failed") from exc
        if result.returncode:
            raise CLIUnavailable("cli_remote_registration_failed")
        # Only expose a fixed boolean; never expose verbose output or URI.
        stderr = result.stderr.decode("utf-8", errors="replace")
        settings_loaded = "[Settings] Loaded from" in stderr
        settings_defaults = "[Settings] File not found, using defaults" in stderr
        rows = result.stdout.decode("utf-8", errors="replace").splitlines()
        active = sum(1 for line in rows if len(line.split("\t")) == 4
                     and line.split("\t")[2] == "active")
        return {"registered_remote_count": sum(
                    1 for line in rows if len(line.split("\t")) == 4),
                "active_remote_count": active,
                "settings_registered_remote_count": len(declared_remotes) if isinstance(declared_remotes, dict) else 0,
                "settings_active_remote_present": bool(declared_active and isinstance(declared_remotes, dict) and declared_active in declared_remotes),
                "cli_reported_settings_loaded": settings_loaded,
                "cli_reported_settings_defaults": settings_defaults,
                "remote_writes_enabled": False}


def probe_official_remote_add(config, *, timeout=45):
    """Register a remote using official CLI in disposable storage only.

    No sync, fetch, publish, unlock, or mutation of persistent editor settings.
    Never return a URI, subprocess output or credentials.
    """
    import tempfile
    import json
    with tempfile.TemporaryDirectory(prefix="obsidian-remote-add-test-") as temp:
        database = Path(temp) / "db"
        database.mkdir(mode=0o700)
        install_official_cli_settings(config, str(database))
        settings_file = database / ".livesync" / "settings.json"
        data = json.loads(settings_file.read_text(encoding="utf-8"))
        configs = data.get("remoteConfigurations", {})
        active_id = data.get("activeConfigurationId")
        if not isinstance(configs, dict) or active_id not in configs:
            raise CLIUnavailable("cli_remote_registration_missing")
        connection = configs[active_id]["uri"]
        # Start without a registered remote so official remote-add owns creation.
        data["remoteConfigurations"] = {}
        data["activeConfigurationId"] = ""
        settings_file.write_text(json.dumps(data), encoding="utf-8")
        os.chmod(settings_file, 0o600)
        executable, _ = validate_cli_installation(
            "/opt/livesync-cli/dist/index.cjs", str(database))
        prefix = ["/usr/local/bin/node", executable, str(database)]
        try:
            added = subprocess.run(
                prefix + ["remote-add", "Home Assistant CouchDB", connection],
                capture_output=True, timeout=timeout, check=False, shell=False)
            after_add = json.loads(settings_file.read_text(encoding="utf-8"))
            listed = subprocess.run(
                prefix + ["remote-ls"],
                capture_output=True, timeout=timeout, check=False, shell=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise CLIUnavailable("cli_remote_add_probe_failed") from exc
        rows = listed.stdout.decode("utf-8", errors="replace").splitlines()
        remote_rows = [line.split("\t") for line in rows]
        remote_rows = [row for row in remote_rows if len(row) == 4]
        after_configs = after_add.get("remoteConfigurations", {})
        after_active = after_add.get("activeConfigurationId", "")
        return {"settings_after_add_count": len(after_configs) if isinstance(after_configs, dict) else 0,
                "settings_after_add_active": bool(isinstance(after_configs, dict) and after_active in after_configs),
                "remote_add_succeeded": added.returncode == 0,
                "remote_list_succeeded": listed.returncode == 0,
                "registered_remote_count": len(remote_rows),
                "active_remote_count": sum(row[2] == "active" for row in remote_rows),
                "persistent_editor_modified": False,
                "remote_notes_modified": False}


def merge_official_cli_defaults_for_disposable_database(database, *, timeout=45):
    """Merge complete official CLI defaults into isolated temporary settings only."""
    import json
    import tempfile
    database = Path(database)
    if database.name != "db" or not database.is_dir() or database.is_symlink():
        raise CLIUnavailable("cli_disposable_database_required")
    settings_path = database / ".livesync" / "settings.json"
    if not settings_path.is_file() or settings_path.is_symlink():
        raise CLIUnavailable("cli_settings_missing")
    executable, _ = validate_cli_installation(
        "/opt/livesync-cli/dist/index.cjs", str(database))
    with tempfile.TemporaryDirectory(prefix="obsidian-cli-defaults-") as temp:
        target = Path(temp) / "defaults.json"
        try:
            result = subprocess.run(
                ["/usr/local/bin/node", executable, "init-settings", str(target)],
                capture_output=True, timeout=timeout, check=False, shell=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise CLIUnavailable("cli_defaults_generation_failed") from exc
        if result.returncode or not target.is_file():
            raise CLIUnavailable("cli_defaults_generation_failed")
        try:
            defaults = json.loads(target.read_text(encoding="utf-8"))
            overrides = json.loads(settings_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise CLIUnavailable("cli_defaults_invalid") from exc
        if not isinstance(defaults, dict) or not isinstance(overrides, dict):
            raise CLIUnavailable("cli_defaults_invalid")
        merged = {**defaults, **overrides}
        staged = settings_path.with_name("settings.next.json")
        if staged.exists() or staged.is_symlink():
            raise CLIUnavailable("cli_defaults_staging_exists")
        with staged.open("x", encoding="utf-8") as handle:
            json.dump(merged, handle, ensure_ascii=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(staged, 0o600)
        os.replace(staged, settings_path)
    return True


def configure_disposable_remote_with_cli(config, database, *, timeout=45):
    """Let the official CLI register its own remote in disposable storage."""
    import json
    database = Path(database)
    settings_file = database / ".livesync" / "settings.json"
    data = json.loads(settings_file.read_text(encoding="utf-8"))
    configs = data.get("remoteConfigurations", {})
    active_id = data.get("activeConfigurationId")
    if not isinstance(configs, dict) or active_id not in configs:
        raise CLIUnavailable("cli_remote_registration_missing")
    connection = configs[active_id]["uri"]
    data["remoteConfigurations"] = {}
    data["activeConfigurationId"] = ""
    settings_file.write_text(json.dumps(data), encoding="utf-8")
    os.chmod(settings_file, 0o600)
    executable, _ = validate_cli_installation(
        "/opt/livesync-cli/dist/index.cjs", str(database))
    prefix = ["/usr/local/bin/node", executable, str(database)]
    try:
        added = subprocess.run(
            prefix + ["remote-add", "Home Assistant CouchDB", connection],
            capture_output=True, timeout=timeout, check=False, shell=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CLIUnavailable("cli_remote_add_failed") from exc
    if added.returncode:
        raise CLIUnavailable("cli_remote_add_failed")
    # remote-add may leave a pre-existing default profile active.
    # Activate the exact ID returned by the official command.
    import re
    stdout = added.stdout.decode("utf-8", errors="replace")
    ids = re.findall(r"(?m)^([A-Za-z0-9_-]{8,128})\tHome Assistant CouchDB\t", stdout)
    if len(ids) != 1:
        raise CLIUnavailable("cli_remote_add_id_missing")
    remote_id = ids[0]
    try:
        activated = subprocess.run(
            prefix + ["remote-activate", remote_id],
            capture_output=True, timeout=timeout, check=False, shell=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CLIUnavailable("cli_remote_activate_failed") from exc
    if activated.returncode:
        raise CLIUnavailable("cli_remote_activate_failed")
    registered = json.loads(settings_file.read_text(encoding="utf-8"))
    remotes = registered.get("remoteConfigurations", {})
    active = registered.get("activeConfigurationId")
    if not isinstance(remotes, dict) or active != remote_id or remote_id not in remotes:
        raise CLIUnavailable("cli_remote_add_not_active")
    if remotes[remote_id].get("name") != "Home Assistant CouchDB":
        raise CLIUnavailable("cli_remote_add_not_active")


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
        merge_official_cli_defaults_for_disposable_database(database)
        try:
            configure_disposable_remote_with_cli(config, database)
        except CLIUnavailable as exc:
            raise CLIUnavailable("publish_registration_" + str(exc)) from None
        binary = "/opt/livesync-cli/dist/index.cjs"
        executable, db_path = validate_cli_installation(binary, str(database))
        try:
            remote_probe = subprocess.run(
                ["/usr/local/bin/node", executable, db_path, "remote-status"],
                capture_output=True, timeout=min(timeout, 45), check=False,
                shell=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise CLIUnavailable("publish_remote_preflight_execution_failed") from exc
        if remote_probe.returncode:
            raise CLIUnavailable("publish_remote_preflight_rejected")
        try:
            verify_local_roundtrip(binary, str(database), note_path, content)
        except CLIUnavailable:
            raise CLIUnavailable("publish_local_roundtrip_failed") from None
        try:
            sync_configured_remote(binary, str(database), timeout=timeout)
        except CLIUnavailable as exc:
            raise CLIUnavailable("publish_" + str(exc)) from None
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
        merge_official_cli_defaults_for_disposable_database(database)
        configure_disposable_remote_with_cli(config, database)
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
            fetch_diag = re.search(
                r"\\[ha_fetch_failure\\] type=([a-z0-9_-]{1,40}) code=([a-z0-9_-]{1,40})",
                output,
            )
            if fetch_diag:
                error_type, error_code = fetch_diag.groups()
                known_codes = {"econnrefused", "enotfound", "etimedout", "eai_again",
                               "eacces", "enoent", "econnreset"}
                known_types = {"typeerror", "referenceerror", "syntaxerror",
                               "rangeerror", "aggregateerror", "error"}
                if error_code in known_codes:
                    raise CLIUnavailable("cli_preview_code_" + error_code)
                if error_type in known_types:
                    raise CLIUnavailable("cli_preview_type_" + error_type)
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
        import re
        diagnostic = re.search(
            r"\[ha_sync_status\] status=([a-z0-9_-]{1,64}) reason=([a-z0-9_-]{1,64})",
            output,
        )
        if diagnostic:
            status, hint = diagnostic.groups()
            # Expose only presence of known metadata fields, never their values.
            fields_match = re.search(
                r"\\[ha_sync_status\\][^\\r\\n]{0,400} fields=([a-z0-9,]{1,240})",
                output,
            )
            if fields_match and status == "failed" and hint == "unspecified":
                names = set(fields_match.group(1).split(","))
                known = {"error", "errors", "cause", "detail", "details",
                         "message", "recoveryhint", "reason", "phase"}
                for field in ("error", "errors", "cause", "detail", "details",
                              "message", "recoveryhint", "reason", "phase"):
                    if field in names and field in known:
                        raise CLIUnavailable("cli_sync_result_has_" + field)
            # Fixed allowlist only. No arbitrary upstream strings reach the API.
            hints = {
                "node_locked": "device_not_accepted",
                "node_cleaned": "device_not_accepted",
                "version_mismatch": "version_incompatible",
                "authentication": "authentication",
                "network": "network",
            }
            reason = hints.get(hint.lower())
            if reason is None:
                # The upstream engine may provide additional reason codes.
                # Only fixed, harmless categories are exposed to the API.
                safe_hints = {
                    "remote_locked", "node_rejected", "remote_not_configured",
                    "replication_not_permitted", "connection_failed",
                    "couchdb_error", "missing_remote", "invalid_remote",
                    "database_locked", "remote_version_mismatch",
                    "remote_not_found", "remote_unavailable",
                }
                reason = ("hint_" + hint.lower()) if hint.lower() in safe_hints else (
                    "upstream_" + status if status in
                    ("failed", "cancelled", "skipped", "interrupted")
                    else "unclassified_replication_failure")
            raise CLIUnavailable("cli_sync_" + reason)
        # Match specific replication diagnostics, not generic startup words
        # such as "incompatible" appearing in unrelated CLI notices.
        if any(x in output for x in (
            "remote database is locked and this device is not yet accepted",
            "node_locked", "node_cleaned", "please unlock the database")):
            reason = "device_not_accepted"
        elif any(x in output for x in (
            "replication rejected: version mismatch",
            "remote protocol version mismatch",
            "central compatibility rejection: version")):
            reason = "version_incompatible"
        elif any(x in output for x in ("unauthorized", "authentication failed", "http 401", "http 403")):
            reason = "authentication"
        elif any(x in output for x in ("decryption failed", "invalid passphrase", "encryption failed")):
            reason = "encryption"
        elif any(x in output for x in ("econnrefused", "enotfound", "getaddrinfo", "network error")):
            reason = "network"
        elif any(x in output for x in ("typeerror:", "referenceerror:", "uncaught exception")):
            reason = "cli_exception"
        else:
            # The upstream CLI currently returns only a boolean for several
            # replication failures. Do not invent a compatibility diagnosis.
            reason = "unclassified_replication_failure"
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
