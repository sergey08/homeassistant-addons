"""Independent Obsidian Client (experimental)."""
import html
import json
import re
import ssl
from pathlib import Path
from urllib.parse import quote, urlsplit
from urllib.request import Request, build_opener, HTTPBasicAuthHandler, HTTPPasswordMgrWithDefaultRealm
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

@app.get("/api/connection")
def connection():
    """Read-only CouchDB connectivity check. Never return secrets."""
    o = options()
    uri = (o.get("couchdb_url") or "").strip().rstrip("/")
    database = (o.get("couchdb_database") or "").strip()
    if not uri:
        return jsonify(configured=False, connected=False, status="not_configured")
    parsed = urlsplit(uri)
    if parsed.scheme not in ("https", "http") or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        return jsonify(configured=True, connected=False, status="invalid_url"), 400
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", database) or not database:
        return jsonify(configured=True, connected=False, status="invalid_database"), 400
    target = uri + "/" + quote(database, safe="")
    try:
        headers = {"Accept": "application/json"}
        username = o.get("couchdb_username") or ""
        password = o.get("couchdb_password") or ""
        if username:
            import base64
            token = base64.b64encode((username + ":" + password).encode()).decode()
            headers["Authorization"] = "Basic " + token
        from urllib.request import urlopen
        req = Request(target, headers=headers, method="GET")
        with urlopen(req, timeout=5) as response:
            info = json.load(response)
        return jsonify(configured=True, connected=True, status="connected",
                       database=database, document_count=info.get("doc_count"))
    except Exception:
        return jsonify(configured=True, connected=False, status="connection_failed"), 502

@app.get("/")
def home():
    root = vault_dir()
    status = '<p><a href="api/connection">CouchDB status / Estado CouchDB (JSON)</a></p>'
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
