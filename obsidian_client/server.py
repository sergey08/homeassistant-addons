"""Independent Obsidian Client (experimental)."""
import html
import socket
import ssl
from urllib.error import HTTPError, URLError
import json
import re
from pathlib import Path
from urllib.parse import quote, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
import markdown
from flask import Flask, abort, request, jsonify

app = Flask(__name__)

def options():
    try:
        return json.loads(Path("/data/options.json").read_text())
    except (OSError, ValueError):
        return {}

def vault_dir():
    root = Path(options().get("vault_path") or "/share/obsidian-client/vault").resolve()
    if not root.is_relative_to(Path("/share").resolve()):
        abort(400, "Vault path must be inside /share")
    return root

def page(content):
    return '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <style>:root{color-scheme:light dark}body{max-width:950px;margin:auto;padding:24px;background:Canvas;color:CanvasText;font:16px system-ui}
    a{color:#8774df}article{line-height:1.6;overflow-wrap:anywhere}pre{overflow:auto;background:#8882;padding:12px}input{padding:10px;width:100%;box-sizing:border-box}
    li{margin:9px 0}.muted{opacity:.75}</style></head><body>''' + content + "</body></html>"


@app.get("/api/demo")
def demo_note():
    """Offline example only / Ejemplo aislado, sin acceso a CouchDB."""
    from livesync_plain import decode_plain_note
    parent = {"type": "plain", "path": "Demo/Hello.md",
              "children": ["first", "second"], "size": 11}
    chunks = {"first": {"type": "leaf", "data": "Hello "},
              "second": {"type": "leaf", "data": "world"}}
    result = decode_plain_note(parent, chunks)
    return jsonify({**result, "source": "synthetic", "read_only": True})

@app.get("/api/e2ee/status")
def e2ee_status():
    """Only boolean configuration status; never exposes the E2EE passphrase."""
    configured = bool(options().get("livesync_e2ee_passphrase"))
    return jsonify(configured=configured, decryption_implemented=False,
                   status="awaiting_compatible_decoder", read_only=True)

@app.get("/api/discovery")
def discovery():
    """Detect known HA CouchDB add-on via DNS only. No port scanning or credentials."""
    # Explicit known integration, not a network-wide scan.
    host = "db21ed7f-obsidian-syncserver-ssl"
    try:
        socket.getaddrinfo(host, 6984, type=socket.SOCK_STREAM)
        detected = True
    except (socket.gaierror, OSError):
        detected = False
    configured = options()
    return jsonify(
        source="known_ha_addon",
        found=detected,
        suggested_host=host if detected else None,
        suggested_https_port=6984 if detected else None,
        configured_database=bool(configured.get("couchdb_database")),
        credentials_configured=bool(configured.get("couchdb_username") and configured.get("couchdb_password")),
        status="candidate_detected" if detected else "not_detected",
        note="DNS only; HTTPS certificate and authenticated access not verified"
    )

@app.get("/api/internal-diagnostics")
def internal_diagnostics():
    """Credential-free TCP probes and verified TLS / Pruebas seguras sin credenciales."""
    host = "db21ed7f-obsidian-syncserver-ssl"
    results = {}
    for port in (5984, 6984):
        state = {"tcp": "not_checked"}
        try:
            with socket.create_connection((host, port), timeout=3) as raw:
                state["tcp"] = "reachable"
                if port == 6984:
                    try:
                        with ssl.create_default_context().wrap_socket(raw, server_hostname=host) as tls:
                            state["tls"] = "verified"
                            state["tls_version"] = tls.version()
                    except ssl.SSLCertVerificationError:
                        state["tls"] = "certificate_verification_failed"
                    except ssl.SSLError:
                        state["tls"] = "handshake_failed"
        except socket.gaierror:
            state["tcp"] = "dns_failed"
        except (TimeoutError, socket.timeout):
            state["tcp"] = "timeout"
        except OSError:
            state["tcp"] = "connection_failed"
        results[str(port)] = state
    # Probe response protocol without credentials or document access.
    for port in (5984, 6984):
        if results[str(port)]["tcp"] != "reachable":
            continue
        try:
            with socket.create_connection((host, port), timeout=3) as raw:
                raw.settimeout(3)
                raw.sendall(b"GET / HTTP/1.0\r\nHost: internal\r\nConnection: close\r\n\r\n")
                prefix = raw.recv(32)
                results[str(port)]["protocol"] = "http" if prefix.startswith(b"HTTP/") else "unknown"
        except (OSError, TimeoutError):
            results[str(port)]["protocol"] = "unknown"
    # Try the public certificate's SNI while connecting to the internal host.
    if results["6984"]["tcp"] == "reachable":
        try:
            with socket.create_connection((host, 6984), timeout=3) as raw:
                with ssl.create_default_context().wrap_socket(
                    raw, server_hostname="casamedia.duckdns.org"
                ) as tls:
                    results["6984"]["public_sni_tls"] = "verified"
                    results["6984"]["public_sni_tls_version"] = tls.version()
        except ssl.SSLCertVerificationError:
            results["6984"]["public_sni_tls"] = "certificate_verification_failed"
        except ssl.SSLError:
            results["6984"]["public_sni_tls"] = "handshake_failed"
        except OSError:
            results["6984"]["public_sni_tls"] = "connection_failed"
    return jsonify(host=host, ports=results, authenticated="not_checked")

@app.get("/api/encryption/probe")
def encryption_probe():
    """One read-only HKDF decryption probe; no plaintext or secrets in result."""
    cfg = options()
    if cfg.get("livesync_encryption_enabled") is not True or not cfg.get("livesync_e2ee_passphrase"):
        return jsonify(status="e2ee_not_configured"), 400
    url = (cfg.get("couchdb_url") or "").strip().rstrip("/")
    db = cfg.get("couchdb_database") or ""
    if url != "http://db21ed7f-obsidian-syncserver-ssl:5984" or not re.fullmatch(r"[A-Za-z0-9_.-]+", db):
        return jsonify(status="unsupported_connection"), 400
    import base64
    from livesync_crypto import decrypt_hkdf_string, UnsupportedEncryption
    user = cfg.get("couchdb_username") or ""
    password = cfg.get("couchdb_password") or ""
    headers = {"Accept": "application/json"}
    if user:
        headers["Authorization"] = "Basic " + base64.b64encode((user + ":" + password).encode()).decode()
    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    opener = build_opener(NoRedirect())
    root = url + "/" + quote(db, safe="")
    def fetch(path, limit):
        with opener.open(Request(root + path, headers=headers), timeout=8) as response:
            content = response.read(limit + 1)
        if len(content) > limit:
            raise ValueError("too_large")
        return json.loads(content)
    try:
        meta = fetch("/_local/obsidian_livesync_sync_parameters", 50000)
        salt = meta.get("pbkdf2salt")
        if not isinstance(salt, str) or not salt:
            return jsonify(status="pbkdf2_salt_unavailable"), 422
        result = fetch("/_all_docs?include_docs=true&limit=100", 2_000_000)
        sample = next((item["doc"]["path"][3:] for item in result.get("rows", [])
                       if isinstance(item.get("doc"), dict)
                       and item["doc"].get("type") == "plain"
                       and isinstance(item["doc"].get("path"), str)
                       and item["doc"]["path"].startswith("/\\:")
                       and item["doc"]["path"][3:].startswith(("%=", "%$"))), None)
        if sample is None:
            return jsonify(status="no_supported_ciphertext_in_sample"), 422
        decrypted = decrypt_hkdf_string(sample, cfg["livesync_e2ee_passphrase"], salt)
        return jsonify(status="decryption_authenticated", success=True, read_only=True,
                       result_type="json" if decrypted.startswith("{") else "string",
                       content_returned=False)
    except UnsupportedEncryption:
        return jsonify(status="decryption_failed_or_key_mismatch", success=False), 422
    except (OSError, ValueError, HTTPError, URLError):
        return jsonify(status="metadata_read_failed", success=False), 502


@app.get("/api/encryption/status")
def encryption_status():
    """Configuration readiness only. Never expose passphrases or derived keys."""
    o = options()
    enabled = o.get("livesync_encryption_enabled") is True
    phrase = o.get("livesync_e2ee_passphrase")
    has_phrase = isinstance(phrase, str) and bool(phrase)
    return jsonify(
        status="configured_waiting_for_decoder" if enabled and has_phrase else
               "passphrase_required" if enabled else "disabled",
        encryption_enabled=enabled,
        passphrase_configured=has_phrase,
        decryption_implemented=False,
        read_only=True,
        note="A configured passphrase does not prove it matches this vault"
    )


@app.get("/api/crypto/preflight")
def crypto_preflight():
    """Read only: verify one encrypted path without revealing plaintext or keys."""
    from livesync_crypto import decrypt_hkdf_string, UnsupportedEncryption
    import base64
    o = options()
    if o.get("livesync_encryption_enabled") is not True or not o.get("livesync_e2ee_passphrase"):
        return jsonify(status="encryption_not_configured"), 400
    url = (o.get("couchdb_url") or "").rstrip("/")
    db = o.get("couchdb_database") or ""
    if url != "http://db21ed7f-obsidian-syncserver-ssl:5984" or not re.fullmatch(r"[A-Za-z0-9_.-]+", db):
        return jsonify(status="unsupported_connection"), 400
    headers = {"Accept": "application/json"}
    user = o.get("couchdb_username") or ""
    if user:
        headers["Authorization"] = "Basic " + base64.b64encode(
            (user + ":" + (o.get("couchdb_password") or "")).encode()).decode()
    base = url + "/" + quote(db, safe="")
    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    opener = build_opener(NoRedirect())
    def fetch(endpoint):
        with opener.open(Request(base + endpoint, headers=headers), timeout=6) as response:
            raw = response.read(350001)
        if len(raw) > 350000:
            raise ValueError("too_large")
        return json.loads(raw)
    try:
        params = fetch("/_local/obsidian_livesync_sync_parameters")
        salt = params.get("pbkdf2salt")
        if not isinstance(salt, str) or not salt:
            return jsonify(status="sync_salt_unavailable", read_only=True)
        rows = fetch("/_all_docs?include_docs=true&limit=40").get("rows", [])
        candidates = [
            d.get("path") for row in rows if isinstance(row, dict)
            for d in [row.get("doc")] if isinstance(d, dict)
            if d.get("type") in ("plain", "newnote") and not d.get("deleted")
            and isinstance(d.get("path"), str) and d["path"].startswith("/\\:%=")
        ]
        if not candidates:
            return jsonify(status="no_supported_path_in_sample", read_only=True)
        try:
            result = decrypt_hkdf_string(candidates[0][3:], o["livesync_e2ee_passphrase"], salt)
        except UnsupportedEncryption:
            return jsonify(status="decryption_failed", read_only=True)
        return jsonify(status="decrypted", valid_path=bool(result), read_only=True,
                       note="Decrypted path withheld / Ruta descifrada no divulgada")
    except (OSError, ValueError, HTTPError, URLError):
        return jsonify(status="probe_failed", read_only=True), 502


@app.get("/api/connection")
def connection():
    """Read-only CouchDB connectivity check. Never return secrets."""
    o = options()
    uri = (o.get("couchdb_url") or "").strip().rstrip("/")
    database = (o.get("couchdb_database") or "").strip()
    if not uri:
        return jsonify(configured=False, connected=False, status="not_configured")
    try:
        parsed = urlsplit(uri)
        port = parsed.port
    except ValueError:
        return jsonify(configured=True, connected=False, status="invalid_url"), 400
    if parsed.scheme not in ("https", "http") or not parsed.hostname or parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment:
        return jsonify(configured=True, connected=False, status="invalid_url"), 400
    if (o.get("couchdb_username") or o.get("couchdb_password")) and parsed.scheme != "https" and not (parsed.scheme == "http" and parsed.hostname == "db21ed7f-obsidian-syncserver-ssl" and parsed.port == 5984):
        return jsonify(configured=True, connected=False, status="https_required"), 400
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", database) or not database:
        return jsonify(configured=True, connected=False, status="invalid_database"), 400
    if parsed.path not in ("", "/"):
        return jsonify(configured=True, connected=False, status="invalid_url_path"), 400
    target = uri + "/" + quote(database, safe="")
    try:
        headers = {"Accept": "application/json"}
        username = o.get("couchdb_username") or ""
        password = o.get("couchdb_password") or ""
        if username:
            import base64
            token = base64.b64encode((username + ":" + password).encode()).decode()
            headers["Authorization"] = "Basic " + token
        req = Request(target, headers=headers, method="GET")
        class NoRedirect(HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None
        opener = build_opener(NoRedirect())
        with opener.open(req, timeout=5) as response:
            info = json.load(response)
        return jsonify(configured=True, connected=True, status="connected",
                       database=database, document_count=info.get("doc_count"))
    except HTTPError as exc:
        reason = {401: "authentication_failed", 403: "access_denied",
                  404: "database_not_found"}.get(exc.code, "http_error")
        return jsonify(configured=True, connected=False, status=reason,
                       http_status=exc.code), 502
    except ssl.SSLCertVerificationError:
        return jsonify(configured=True, connected=False, status="tls_certificate_error"), 502
    except (socket.gaierror,):
        return jsonify(configured=True, connected=False, status="dns_error"), 502
    except (TimeoutError, socket.timeout):
        return jsonify(configured=True, connected=False, status="timeout"), 502
    except (ConnectionRefusedError, ConnectionResetError):
        return jsonify(configured=True, connected=False, status="network_error"), 502
    except URLError as exc:
        cause = exc.reason
        if isinstance(cause, ssl.SSLCertVerificationError):
            status = "tls_certificate_error"
        elif isinstance(cause, socket.gaierror):
            status = "dns_error"
        elif isinstance(cause, (TimeoutError, socket.timeout)):
            status = "timeout"
        else:
            status = "network_error"
        return jsonify(configured=True, connected=False, status=status), 502
    except Exception:
        return jsonify(configured=True, connected=False, status="connection_failed"), 502



@app.get("/api/remote/inspect")
def inspect_remote():
    """Limited read-only structure probe / Inspección limitada de solo lectura."""
    o = options()
    uri = (o.get("couchdb_url") or "").strip().rstrip("/")
    database = (o.get("couchdb_database") or "").strip()
    if not uri:
        return jsonify(configured=False, status="not_configured")
    try:
        parsed = urlsplit(uri)
        parsed.port
    except ValueError:
        return jsonify(status="invalid_url"), 400
    if (parsed.scheme not in ("http", "https") or not parsed.hostname
            or parsed.username is not None or parsed.password is not None
            or parsed.query or parsed.fragment or parsed.path not in ("", "/")
            or not re.fullmatch(r"[A-Za-z0-9_.-]+", database)):
        return jsonify(status="invalid_configuration"), 400
    username = o.get("couchdb_username") or ""
    password = o.get("couchdb_password") or ""
    if (username or password) and parsed.scheme != "https" and not (parsed.scheme == "http" and parsed.hostname == "db21ed7f-obsidian-syncserver-ssl" and parsed.port == 5984):
        return jsonify(status="https_required"), 400
    headers = {"Accept": "application/json"}
    if username:
        import base64
        headers["Authorization"] = "Basic " + base64.b64encode(
            (username + ":" + password).encode()).decode()
    target = uri + "/" + quote(database, safe="") + "/_all_docs?include_docs=true&limit=20"
    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    try:
        req = Request(target, headers=headers, method="GET")
        with build_opener(NoRedirect()).open(req, timeout=5) as response:
            raw = response.read(1_000_001)
            if len(raw) > 1_000_000:
                return jsonify(status="response_too_large"), 413
            result = json.loads(raw)
        rows = result.get("rows", [])
        if not isinstance(rows, list):
            raise ValueError("Invalid CouchDB response")
        kinds = {}
        for row in rows:
            doc = row.get("doc") if isinstance(row, dict) else None
            doc = doc if isinstance(doc, dict) else {}
            raw_type = doc.get("type")
            kind = raw_type if raw_type in ("plain", "newnote", "notes", "leaf", "chunk", "milestone") else "other"
            kinds[kind] = kinds.get(kind, 0) + 1
        return jsonify(status="ok", sample_count=len(rows), types=kinds,
                       note="Metadata only / Solo metadatos; no document contents returned")
    except Exception:
        return jsonify(status="connection_failed"), 502

def remote_note_index():
    """Read-only bounded index of non-deleted plaintext Markdown paths."""
    o = options()
    uri = (o.get("couchdb_url") or "").strip().rstrip("/")
    database = (o.get("couchdb_database") or "").strip()
    try:
        parsed = urlsplit(uri)
        parsed.port
    except ValueError:
        return None, "invalid_url"
    if (parsed.scheme not in ("https", "http") or not parsed.hostname
            or parsed.path not in ("", "/") or parsed.username or parsed.password
            or parsed.query or parsed.fragment
            or not re.fullmatch(r"[A-Za-z0-9_.-]+", database)):
        return None, "invalid_configuration"
    local_allowed = (parsed.scheme == "http" and parsed.hostname ==
                     "db21ed7f-obsidian-syncserver-ssl" and parsed.port == 5984)
    if parsed.scheme != "https" and not local_allowed:
        return None, "https_required"
    import base64
    headers = {"Accept": "application/json"}
    username = o.get("couchdb_username") or ""
    if username:
        headers["Authorization"] = "Basic " + base64.b64encode(
            (username + ":" + (o.get("couchdb_password") or "")).encode()).decode()
    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    target = uri + "/" + quote(database, safe="") + "/_all_docs?include_docs=true&limit=1000"
    try:
        with build_opener(NoRedirect()).open(Request(target, headers=headers), timeout=8) as resp:
            raw = resp.read(5_000_001)
        if len(raw) > 5_000_000:
            return None, "response_too_large"
        records = json.loads(raw)
    except (OSError, ValueError, HTTPError, URLError):
        return None, "connection_failed"
    notes = []
    rows = records.get("rows", [])
    for item in rows:
        doc = item.get("doc") if isinstance(item, dict) else None
        if not isinstance(doc, dict) or doc.get("type") != "plain":
            continue
        if doc.get("deleted") or doc.get("_deleted") or doc.get("_conflicts"):
            continue
        path = doc.get("path")
        if (isinstance(path, str) and path.endswith(".md") and
                not path.startswith("/") and "\\\\" not in path and
                all(part not in ("", ".", "..") for part in path.split("/"))):
            notes.append(path)
    return sorted(set(notes), key=str.casefold), None


@app.get("/api/remote/format")
def remote_format():
    """Safe schema probe. Never include note IDs, paths or contents."""
    o = options()
    url = (o.get("couchdb_url") or "").strip().rstrip("/")
    if url != "http://db21ed7f-obsidian-syncserver-ssl:5984":
        return jsonify(status="unsupported_host"), 400
    import base64
    username = o.get("couchdb_username") or ""
    password = o.get("couchdb_password") or ""
    headers = {"Accept": "application/json"}
    if username:
        headers["Authorization"] = "Basic " + base64.b64encode((username + ":" + password).encode()).decode()
    database = o.get("couchdb_database") or ""
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", database):
        return jsonify(status="invalid_database"), 400
    target = url + "/" + quote(database, safe="") + "/_all_docs?include_docs=true&limit=100"
    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    try:
        with build_opener(NoRedirect()).open(Request(target, headers=headers), timeout=8) as resp:
            raw = resp.read(1_000_001)
        if len(raw) > 1_000_000:
            return jsonify(status="response_too_large"), 413
        rows = json.loads(raw).get("rows", [])
    except (OSError, ValueError):
        return jsonify(status="connection_failed"), 502
    shapes = {}
    for item in rows:
        doc = item.get("doc") if isinstance(item, dict) else None
        if not isinstance(doc, dict):
            continue
        kind = doc.get("type")
        kind = kind if kind in ("plain", "newnote", "leaf", "chunk") else "other"
        slot = shapes.setdefault(kind, {"count": 0, "path_present": 0, "path_md": 0,
                                       "path_f_prefix": 0, "path_other": 0,
                                       "keys": {}})
        slot["count"] += 1
        for key in doc:
            if key in ("_id", "_rev", "path", "data", "children", "mtime", "ctime", "size", "type", "deleted", "eden", "e_"):
                slot["keys"][key] = slot["keys"].get(key, 0) + 1
        path = doc.get("path")
        if isinstance(path, str):
            slot["path_present"] += 1
            if path.endswith(".md"):
                slot["path_md"] += 1
            elif path.startswith("f:"):
                slot["path_f_prefix"] += 1
            else:
                slot["path_other"] += 1
    for item in rows:
        doc = item.get("doc") if isinstance(item, dict) else None
        if not isinstance(doc, dict) or not isinstance(doc.get("path"), str):
            continue
        path = doc["path"]
        kind = doc.get("type")
        kind = kind if kind in ("plain", "newnote", "leaf", "chunk") else "other"
        slot = shapes[kind]
        slot.setdefault("path_features", {"contains_slash": 0, "contains_dot": 0,
                     "contains_colon": 0, "hex_only": 0, "base64_chars_only": 0,
                     "length_1_32": 0, "length_33_80": 0, "length_over_80": 0})
        f = slot["path_features"]
        if "/" in path: f["contains_slash"] += 1
        if "." in path: f["contains_dot"] += 1
        if ":" in path: f["contains_colon"] += 1
        f.setdefault("metadata_encrypted_prefix", 0)
        f.setdefault("prefix_obfuscated", 0)
        if path.startswith("/\\:"):
            f["metadata_encrypted_prefix"] += 1
            f.setdefault("encrypted_payload_shapes", {"percent_equal": 0, "percent_dollar": 0, "other": 0})
            # Classify prefixes only: do not return actual paths, suffixes or lengths.
            suffix = path[3:]
            typ = "percent_equal" if suffix.startswith("%=") else ("percent_dollar" if suffix.startswith("%$") else "other")
            f["encrypted_payload_shapes"][typ] += 1
        if path.startswith("f:"): f["prefix_obfuscated"] += 1
        if path.startswith("/\\:"):
            payload = path[3:]
            categories = f.setdefault("encrypted_payload_shape", {
                "hkdf_percent_equals": 0, "hkdf_percent_dollar": 0,
                "legacy_percent": 0, "base64_like": 0, "other": 0
            })
            if payload.startswith("%="):
                categories["hkdf_percent_equals"] += 1
            elif payload.startswith("%$"):
                categories["hkdf_percent_dollar"] += 1
            elif payload.startswith("%"):
                categories["legacy_percent"] += 1
            elif re.fullmatch(r"[A-Za-z0-9+/=_-]+", payload):
                categories["base64_like"] += 1
            else:
                categories["other"] += 1
        if re.fullmatch(r"[0-9a-fA-F]+", path): f["hex_only"] += 1
        if re.fullmatch(r"[A-Za-z0-9+/=_:-]+", path): f["base64_chars_only"] += 1
        bucket = "length_1_32" if len(path) <= 32 else ("length_33_80" if len(path) <= 80 else "length_over_80")
        f[bucket] += 1
    return jsonify(status="ok", inspected=len(rows), shapes=shapes, read_only=True)


@app.get("/api/remote/notes")
def remote_notes():
    notes, error = remote_note_index()
    if error:
        return jsonify(status=error, notes=[]), 502
    term = request.args.get("q", "").strip().casefold()
    if len(term) > 200:
        return jsonify(status="query_too_long"), 400
    filtered = [note for note in notes if term in note.casefold()]
    return jsonify(status="ok", read_only=True, count=len(filtered),
                   notes=filtered, content_available=False,
                   note="Paths only; chunk decoding not yet validated against real data")


@app.get("/api/notes")
def list_notes():
    """Read-only local Markdown index / Índice local de solo lectura."""
    root = vault_dir()
    if not root.is_dir():
        return jsonify(notes=[], count=0, status="vault_not_found")
    term = request.args.get("q", "").strip().casefold()
    if len(term) > 200:
        return jsonify(error="query_too_long"), 400
    notes = []
    for p in root.rglob("*.md"):
        relative = p.relative_to(root)
        if any(part.startswith(".") for part in relative.parts):
            continue
        if not p.resolve().is_relative_to(root) or not p.is_file():
            continue
        name = relative.as_posix()
        if term and term not in name.casefold():
            continue
        notes.append(name)
        if len(notes) >= 2000:
            break
    notes.sort(key=str.casefold)
    return jsonify(notes=notes, count=len(notes), truncated=len(notes) >= 2000)

@app.get("/")
def home():
    root = vault_dir()
    status = ('<p><a href="api/demo">Offline example / Ejemplo aislado (JSON)</a> · '
              '<a href="api/connection">CouchDB diagnostics / Diagnóstico CouchDB (JSON)</a></p>')
    if not root.is_dir():
        cfg = options()
        if cfg.get("livesync_encryption_enabled"):
            ready = bool(cfg.get("livesync_e2ee_passphrase"))
            return page(
                "<h1>Obsidian Client</h1><h2>LiveSync · Bóveda cifrada / Encrypted vault</h2>" +
                "<p>Servidor configurado / Server configured: " +
                ("Sí / Yes" if cfg.get("couchdb_url") else "No") + "</p>" +
                "<p>Frase E2EE configurada / E2EE passphrase configured: " +
                ("Sí / Yes" if ready else "No") + "</p>" +
                "<p>Lectura de metadatos / Metadata diagnostics: " +
                '<a href="api/connection">Conexión</a> · <a href="api/remote/format">Formato</a></p>' +
                "<p><strong>Descifrado pendiente / Decryption not implemented yet.</strong> "
                "No se muestran rutas cifradas como si fueran notas válidas. / "
                "Encrypted paths are not presented as readable notes.</p>" + status
            )
        notes, error = remote_note_index()
        if error:
            return page("<h1>Obsidian Client</h1><p>Remote vault unavailable / Bóveda remota no disponible: " +
                        html.escape(error) + "</p>" + status)
        term = request.args.get("q", "").strip().casefold()
        visible = [p for p in notes if term in p.casefold()][:500]
        rows = "".join("<li>" + html.escape(p) + "</li>" for p in visible)
        return page("<h1>Obsidian Client</h1><p>LiveSync · Solo lectura: " +
                    str(len(notes)) + " rutas Markdown detectadas</p>" + status +
                    '<form><input name="q" placeholder="Buscar notas" value="' +
                    html.escape(request.args.get("q", ""), quote=True) +
                    '"></form><ul>' + rows + "</ul><p class='muted'>Índice de rutas únicamente; lectura del contenido aún no validada.</p>")
    relative = request.args.get("path")
    if relative is not None:
        if "\x00" in relative or "\\" in relative:
            abort(400)
        target = (root / relative).resolve()
        if not target.is_relative_to(root) or target.suffix.lower() != ".md" or not target.is_file():
            abort(404)
        content = target.read_text(encoding="utf-8", errors="replace")
        rendered = markdown.markdown(html.escape(content), extensions=["tables", "fenced_code"])
        return page('<p><a href="./">← Back / Volver</a></p><h1>' + html.escape(target.stem) +
                    '</h1><article>' + rendered + '</article>')
    term = request.args.get("q", "").strip().casefold()
    paths = []
    for p in root.rglob("*.md"):
        rel = p.relative_to(root)
        if any(part.startswith(".") for part in rel.parts):
            continue
        if term and term not in rel.as_posix().casefold():
            continue
        paths.append(rel.as_posix())
        if len(paths) >= 2000:
            break
    paths.sort(key=str.casefold)
    rows = "".join('<li><a href="?path=' + quote(p, safe="") + '">' + html.escape(p) + '</a></li>' for p in paths)
    return page('<h1>Obsidian Client</h1>' + status + '<p>Local Markdown preview / Vista previa Markdown local (' +
                str(len(paths)) + ')</p><form><input name="q" placeholder="Search notes / Buscar notas" value="' +
                html.escape(request.args.get("q", ""), quote=True) + '"></form><ul>' + rows + "</ul>")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8099)
