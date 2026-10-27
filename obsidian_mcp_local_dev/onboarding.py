#!/usr/bin/env python3
"""Read-only, local onboarding status page for Home Assistant Ingress.

No secrets or note contents are returned. Supervisor Ingress provides access
control; this server must never be published as a host port.
"""
import html
import json
import os
import secrets
from urllib.parse import parse_qs
from settings_import import import_settings_json, SettingsImportError
from couchdb_check import check_couchdb, CouchCheckError
from tunnel_key import store_runtime_key, TunnelKeyError
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from vault_selection import select_storage

DATA = Path("/data")
LEGACY = Path("/app_configs/obsidian_bridge")
CSRF_TOKEN = secrets.token_urlsafe(32)
MAX_REQUEST = 180000

def collect_status(data=DATA, legacy=LEGACY):
    base = data
    try:
        options = json.loads((data / "options.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        options = {}
    def exists(path):
        return path.is_file() and path.stat().st_size > 0
    tunnel = bool(options.get("enable_tunnel", False))
    try:
        mode, vault, sync = select_storage(options, base / "vault")
        vault_ready = vault.is_dir()
        vault_error = ""
    except (ValueError, OSError) as exc:
        mode = "invalid"
        vault_ready = False
        vault_error = str(exc)
        sync = False
    return {
        "vault": vault_ready,
        "storage_mode": mode,
        "vault_error": vault_error,
        "trash": (base / "mcp-trash").is_dir(),
        "sync_enabled": sync,
        "sync_settings": exists(base / "settings/livesync-operativo.json"),
        "tunnel_enabled": tunnel,
        "tunnel_id": bool(str(options.get("tunnel_id", "")).strip()),
        "tunnel_binary": (base / "tunnel/bin/tunnel-client").is_file() and os.access(base / "tunnel/bin/tunnel-client", os.X_OK),
        "tunnel_key": exists(base / "tunnel/api-key"),
    }

def render_page(status, message=""):
    items = [
        ("Markdown vault (" + status["storage_mode"] + ")", status["vault"],
         status["vault_error"] or "Check vault_path in Configuration if using local mode"),
        ("Recoverable trash", status["trash"], "Created on first startup"),
        ("LiveSync settings", status["sync_settings"], "Import settings from your Obsidian client"),
        ("LiveSync enabled", status["sync_enabled"], "Enable only after configuring synchronization"),
        ("Tunnel client executable", status["tunnel_binary"], "File present; official provenance and connectivity must be verified separately"),
        ("Tunnel runtime key", status["tunnel_key"], "Private key file present; does not prove validity"),
        ("Tunnel ID set", status["tunnel_id"], "Copy the tunnel ID into Configuration"),
        ("Tunnel enabled", status["tunnel_enabled"], "Enable after provisioning credentials"),
    ]
    rows = "".join(
        "<tr><td>"+html.escape(label)+"</td><td>"+("Ready" if ready else "Not configured")+
        "</td><td>"+html.escape(hint)+"</td></tr>"
        for label, ready, hint in items
    )
    message_html = ("<p role='status'>" + html.escape(message) + "</p>") if message else ""
    setup_form = ""
    if status["storage_mode"] == "livesync" and not status["sync_settings"] and not status["sync_enabled"]:
        setup_form = (
            "<h2>Import existing LiveSync CLI settings</h2>"
            "<p>Paste the contents of a trusted, pre-exported LiveSync CLI settings JSON file. "
            "Do not paste the Obsidian setup URI here. The JSON remains private and is never returned by this page.</p>"
            "<form method='post' action='./'>"
            "<input type='hidden' name='csrf' value='" + CSRF_TOKEN + "'>"
            "<label for='settings'>LiveSync CLI settings JSON</label>"
            "<textarea id='settings' name='settings' rows='8' required autocomplete='off' spellcheck='false' "
            "style='display:block;width:100%;max-width:100%;margin:.5em 0;background:#282b38;color:white'></textarea>"
            "<button type='submit'>Import settings once</button></form>"
        )
    if status["storage_mode"] == "livesync" and status["sync_settings"]:
        setup_form += (
            "<h2>Check CouchDB connection</h2>"
            "<p>Read-only: checks authentication, database metadata and TLS. Never starts synchronization.</p>"
            "<form method='post' action='./'>"
            "<input type='hidden' name='csrf' value='" + CSRF_TOKEN + "'>"
            "<input type='hidden' name='action' value='check_couchdb'>"
            "<button type='submit'>Check CouchDB</button></form>"
        )
    if not status["tunnel_key"] and not status["tunnel_enabled"]:
        setup_form += (
            "<h2>Secure MCP tunnel runtime key</h2>"
            "<p>Only enter an OpenAI tunnel runtime API key from your own organization. "
            "The key is stored locally and never displayed again. Do not paste your tunnel ID here.</p>"
            "<form method='post' action='./'>"
            "<input type='hidden' name='csrf' value='" + CSRF_TOKEN + "'>"
            "<input type='hidden' name='action' value='save_tunnel_key'>"
            "<label for='tunnel_key'>Runtime API key</label>"
            "<input id='tunnel_key' type='password' name='tunnel_key' required "
            "autocomplete='new-password' style='display:block;width:100%;max-width:100%;margin:.5em 0'>"
            "<button type='submit'>Store private key</button></form>"
        )
    return ("<!doctype html><html lang='en'><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>Obsidian MCP setup</title>"
        "<style>body{font:16px system-ui;max-width:960px;margin:2em auto;padding:0 1em;"
        "background:#171925;color:#f7f8fc}a{color:#6dd8ff}table{width:100%;border-collapse:collapse}"
        "td,th{padding:12px;border-bottom:1px solid #444;text-align:left}"
        "h1{color:#bda3ff}.hint{color:#bac0d3}</style>"
        "<h1>Obsidian MCP for Home Assistant</h1>"
        "<p>Setup checklist: file presence is not proof of secure installation or working connectivity. No secrets or note contents are displayed.</p>"
        "<table><thead><tr><th>Requirement</th><th>Status</th><th>Next step</th></tr></thead>"
        "<tbody>"+rows+"</tbody></table>"+message_html+setup_form
        +"<p class='hint'>CouchDB connection and end-to-end synchronization have not been verified by this checklist.</p>"
        "<p><a href='https://github.com/sergey08/homeassistant-addons/blob/main/obsidian_suite/DOCS.md'"
        " target='_blank' rel='noopener noreferrer'>Setup documentation</a></p></html>")

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.split("?", 1)[0] not in ("/", "/index.html"):
            self.send_error(404)
            return
        content = render_page(collect_status()).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'self'")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)
    def do_POST(self):
        # CSRF-protected Ingress-only action; no request contents in logs/errors.
        length = self.headers.get("Content-Length", "")
        if not length.isdecimal() or not 0 < int(length) <= MAX_REQUEST:
            self.send_error(413)
            return
        if self.headers.get("Content-Type", "").split(";", 1)[0] != "application/x-www-form-urlencoded":
            self.send_error(415)
            return
        try:
            data = parse_qs(self.rfile.read(int(length)).decode("utf-8"), strict_parsing=True)
        except (ValueError, UnicodeDecodeError):
            self.send_error(400)
            return
        if data.get("csrf") != [CSRF_TOKEN]:
            self.send_error(403)
            return
        status = collect_status()
        if data.get("action") == ["save_tunnel_key"]:
            base = DATA
            if status["tunnel_enabled"] or status["tunnel_key"]:
                message = "Import refused: tunnel is enabled or key already exists."
            else:
                try:
                    message = store_runtime_key(data.get("tunnel_key", [""])[0], base)
                except TunnelKeyError as exc:
                    message = str(exc)
        elif data.get("action") == ["check_couchdb"]:
            base = LEGACY if (LEGACY / "vault").is_dir() else DATA
            try:
                message = check_couchdb(base / "settings/livesync-operativo.json")
            except CouchCheckError as exc:
                message = str(exc)
        elif status["sync_enabled"] or status["sync_settings"]:
            message = "Import refused: LiveSync is enabled or settings already exist."
        else:
            base = LEGACY if (LEGACY / "vault").is_dir() else DATA
            try:
                message = import_settings_json(data.get("settings", [""])[0].encode("utf-8"), base)
            except SettingsImportError as exc:
                message = str(exc)
        content = render_page(collect_status(), message).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)
    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8099), Handler).serve_forever()
