"""Independent Obsidian Client (experimental)."""
import html
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
    return jsonify(decode_plain_note(parent, chunks), source="synthetic",
                   read_only=True)

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
    if (o.get("couchdb_username") or o.get("couchdb_password")) and parsed.scheme != "https":
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
    if (username or password) and parsed.scheme != "https":
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
    status = '<p><a href="api/connection">CouchDB connection diagnostics / Diagnóstico de conexión CouchDB (JSON)</a></p>'
    if not root.is_dir():
        return page("<h1>Obsidian Client</h1><p>Local vault not found / Bóveda local no encontrada.</p>" + status +
                    '<p class="muted">LiveSync document decoding and editing are not implemented yet / El descifrado y la edición todavía no están implementados.</p>')
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
