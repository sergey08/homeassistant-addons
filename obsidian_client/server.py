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


@app.get("/livesync/setup")
def livesync_setup_page():
    """Simple local setup workflow; all credentials remain server-side."""
    if options().get("livesync_cli_enabled") is not True:
        return page("<h1>LiveSync</h1><p>Activa el cliente CLI en la configuración de la aplicación.</p>")
    return page("""<h1>LiveSync · Configuración local</h1>
<p>Esta pantalla no sincroniza ni escribe en tu bóveda remota.</p>
<p>Configura la URL, la base de datos, las credenciales y la frase de cifrado en las opciones de Home Assistant.</p>
<button id="check" type="button">Comprobar conexión (solo lectura)</button>
<button id="install" type="button">Instalar configuración local</button>
<pre id="result" role="status" aria-live="polite">Sin comprobar</pre>
<script>
const output=document.getElementById("result");
document.getElementById("check").onclick=async()=>{
 output.textContent="Comprobando conexión...";
 try {
  const r=await fetch("../api/livesync-cli/connection-check",{cache:"no-store"});
  const j=await r.json();
  output.textContent=j.status||"Respuesta inesperada";
 }catch(_){output.textContent="No se pudo comprobar la conexión"}
};
document.getElementById("install").onclick=async()=>{
 if(!confirm("¿Instalar la configuración cifrada SOLO en la base local? No sincroniza notas."))return;
 output.textContent="Instalando...";
 try {
  const r=await fetch("../api/livesync-cli/configure-local",{
   method:"POST",headers:{"X-Obsidian-Client-Action":"configure-local"}
  });
  const j=await r.json();
  output.textContent=r.ok?"Configuración local instalada. Sin sincronización.":(j.error||"Error");
 }catch(_){output.textContent="No se pudo instalar la configuración"}
};
</script>""")


@app.get("/api/livesync-cli/status")
def livesync_cli_status():
    """Report local CLI readiness without exposing credentials or writing data."""
    from livesync_cli_bridge import cli_local_status, validate_remote_configuration, CLIUnavailable
    configured = options()
    remote_readiness = validate_remote_configuration(configured)
    enabled = configured.get("livesync_cli_enabled") is True
    try:
        local_status = cli_local_status(
            "/opt/livesync-cli/dist/index.cjs", "/data/livesync-client"
        )
        installed = True
    except CLIUnavailable:
        installed = False
        local_status = {}
    return jsonify(
        enabled=enabled,
        installed=installed,
        local_database_directory_present=Path("/data/livesync-client").is_dir(),
        local_database_initialized=local_status.get("livesync_directory_present", False),
        local_settings_present=local_status.get("settings_present", False),
        remote_sync_configured=local_status.get("settings_present", False),
        remote_configuration_ready=remote_readiness["configuration_complete"],
        remote_configuration_checks=remote_readiness,
        remote_writes_enabled=False,
        status=("settings_installed_offline" if local_status.get("settings_present", False)
                else "awaiting_remote_configuration") if enabled and installed
               else "disabled" if not enabled else "cli_unavailable",
    )


@app.post("/api/livesync-cli/configure-local")
def livesync_cli_configure_local():
    """Explicitly persist E2EE settings locally. Does not connect or sync."""
    from livesync_cli_bridge import (
        CLIUnavailable, install_official_cli_settings, validate_remote_configuration,
    )
    config = options()
    if config.get("livesync_cli_enabled") is not True:
        return jsonify(error="cli_disabled"), 403
    if request.headers.get("X-Obsidian-Client-Action") != "configure-local":
        return jsonify(error="missing_action_header"), 403
    if request.headers.get("Sec-Fetch-Site") not in (None, "same-origin"):
        return jsonify(error="cross_origin_blocked"), 403
    if request.headers.get("Origin") and request.headers.get("Sec-Fetch-Site") != "same-origin":
        return jsonify(error="cross_origin_blocked"), 403
    if not validate_remote_configuration(config)["configuration_complete"]:
        return jsonify(error="remote_configuration_incomplete"), 409
    try:
        with _local_save_lock:
            result = install_official_cli_settings(config, "/data/livesync-client")
        return jsonify(result), 201
    except CLIUnavailable as exc:
        return jsonify(error=str(exc)), 409


@app.post("/api/livesync-cli/publish-test-note")
def livesync_cli_publish_test_note():
    """Fail closed: never publish to a configured real LiveSync remote.

    Isolated encrypted publication belongs in disposable integration tests,
    not in a production ingress route.
    """
    return jsonify(error="remote_writes_disabled",
                   remote_writes_enabled=False), 403


@app.post("/api/livesync-cli/remote-add-probe")
def livesync_cli_remote_add_probe():
    from livesync_cli_bridge import probe_official_remote_add, CLIUnavailable
    if options().get("livesync_cli_enabled") is not True:
        return jsonify(error="cli_disabled"), 403
    if request.headers.get("X-Obsidian-Client-Action") != "remote-add-probe":
        return jsonify(error="missing_action_header"), 403
    if request.headers.get("Sec-Fetch-Site") not in (None, "same-origin"):
        return jsonify(error="cross_origin_blocked"), 403
    if request.headers.get("Origin") and request.headers.get("Sec-Fetch-Site") != "same-origin":
        return jsonify(error="cross_origin_blocked"), 403
    try:
        with _local_save_lock:
            return jsonify(probe_official_remote_add(options()))
    except CLIUnavailable:
        return jsonify(error="remote_add_probe_failed"), 502


@app.post("/api/livesync-cli/remote-registration-probe")
def livesync_cli_remote_registration_probe():
    from livesync_cli_bridge import probe_official_remote_registration, CLIUnavailable
    if options().get("livesync_cli_enabled") is not True:
        return jsonify(error="cli_disabled"), 403
    if request.headers.get("X-Obsidian-Client-Action") != "remote-registration-probe":
        return jsonify(error="missing_action_header"), 403
    if request.headers.get("Sec-Fetch-Site") not in (None, "same-origin"):
        return jsonify(error="cross_origin_blocked"), 403
    if request.headers.get("Origin") and request.headers.get("Sec-Fetch-Site") != "same-origin":
        return jsonify(error="cross_origin_blocked"), 403
    try:
        with _local_save_lock:
            return jsonify(probe_official_remote_registration(options()))
    except CLIUnavailable:
        return jsonify(error="remote_registration_probe_failed"), 502


@app.post("/api/livesync-cli/remote-status-probe")
def livesync_cli_remote_status_probe():
    from livesync_cli_bridge import probe_remote_status, CLIUnavailable
    if options().get("livesync_cli_enabled") is not True:
        return jsonify(error="cli_disabled"), 403
    if request.headers.get("X-Obsidian-Client-Action") != "remote-status-probe":
        return jsonify(error="missing_action_header"), 403
    if request.headers.get("Sec-Fetch-Site") not in (None, "same-origin"):
        return jsonify(error="cross_origin_blocked"), 403
    if request.headers.get("Origin") and request.headers.get("Sec-Fetch-Site") != "same-origin":
        return jsonify(error="cross_origin_blocked"), 403
    try:
        with _local_save_lock:
            result = probe_remote_status(options())
        return jsonify(result)
    except CLIUnavailable:
        return jsonify(error="cli_status_probe_failed"), 502


@app.post("/api/livesync-cli/remote-preview")
def livesync_cli_remote_preview():
    """Explicit remote fetch into disposable storage, never persistent local state."""
    from livesync_cli_bridge import (
        fetch_remote_to_disposable_database, CLIUnavailable,
    )
    cfg = options()
    if cfg.get("livesync_cli_enabled") is not True:
        return jsonify(error="cli_disabled"), 403
    if request.headers.get("X-Obsidian-Client-Action") != "remote-preview":
        return jsonify(error="missing_action_header"), 403
    if request.headers.get("Sec-Fetch-Site") not in (None, "same-origin"):
        return jsonify(error="cross_origin_blocked"), 403
    if request.headers.get("Origin") and request.headers.get("Sec-Fetch-Site") != "same-origin":
        return jsonify(error="cross_origin_blocked"), 403
    if request.content_length is not None and request.content_length > 4096:
        return jsonify(error="request_too_large"), 413
    payload = request.get_json(silent=True) if request.is_json else {}
    if not isinstance(payload, dict) or set(payload) - {"path"}:
        return jsonify(error="invalid_request"), 400
    note_path = payload.get("path")
    if note_path is not None:
        from livesync_write_preflight import validate_write_request, UnsafeWrite
        try:
            validate_write_request(note_path, "", None, creating=True)
        except (UnsafeWrite, ValueError, TypeError):
            return jsonify(error="invalid_path"), 400
    try:
        with _local_save_lock:
            result = fetch_remote_to_disposable_database(cfg, note_path=note_path)
        response = jsonify(result)
        response.headers["Cache-Control"] = "no-store"
        return response
    except CLIUnavailable as exc:
        code = str(exc)
        allowed = {"cli_preview_authentication", "cli_preview_network",
                   "cli_preview_encryption", "cli_preview_remote_configuration",
                   "cli_preview_database", "cli_preview_cli_failure",
                   "cli_preview_fetch_operation", "cli_preview_local_database",
                   "cli_preview_cli_exception",
                   "cli_preview_code_econnrefused", "cli_preview_code_enotfound", "cli_preview_code_etimedout", "cli_preview_code_eai_again", "cli_preview_code_eacces", "cli_preview_code_enoent", "cli_preview_code_econnreset", "cli_preview_type_typeerror", "cli_preview_type_referenceerror", "cli_preview_type_syntaxerror", "cli_preview_type_rangeerror", "cli_preview_type_aggregateerror", "cli_preview_type_error" }
        if code == "cli_preview_note_not_found":
            return jsonify(error="note_not_found"), 404
        if code == "cli_preview_note_too_large":
            return jsonify(error="note_too_large"), 413
        # Only expose fixed diagnostic categories: no process output, paths or credentials.
        safe_preview_codes = {
            "cli_preview_read_failed", "cli_preview_invalid_restored_path",
            "cli_preview_too_many_notes", "cli_preview_symlink_not_allowed",
            "cli_preview_fetch_failed", "cli_preview_remote_locked",
            "cli_preview_version_incompatible", "cli_preview_invalid_encoding",
            "cli_preview_cli_failure", "cli_list_failed", "cli_list_invalid_format",
            "cli_preview_typeerror_null_property", "cli_preview_typeerror_not_function",
            "cli_preview_typeerror_network", "cli_preview_typeerror_encryption",
            "cli_preview_typeerror_invalid_url", "cli_preview_typeerror_other",
            "cli_preview_typeerror_undefined_value", "cli_preview_typeerror_invalid_structure",
            "cli_preview_typeerror_invalid_argument", "cli_preview_typeerror_database_closed",
            "cli_preview_typeerror_permission",
            "cli_preview_origin_rebuilder", "cli_preview_origin_replication",
            "cli_preview_origin_storage", "cli_preview_origin_crypto",
            "cli_preview_origin_settings", "cli_preview_origin_unknown",
            "cli_list_invalid_encoding", "cli_read_failed", "cli_invalid_encoding",
        }
        safe_code = code if code in allowed or code in safe_preview_codes else "remote_preview_failed"
        return jsonify(error=safe_code), 502


@app.get("/remote/library")
def independent_remote_library():
    """Browse CouchDB with the Client's existing read-only LiveSync E2EE decoder.

    This path does not use MCP or the official CLI fetch/rebuilder, which
    fails against the currently observed remote dataset. No remote writes.
    """
    if options().get("livesync_cli_enabled") is not True:
        return page('<h1>Biblioteca remota</h1><p>CLI LiveSync deshabilitada.</p>'), 409
    body = """<h1>Biblioteca remota / Remote library</h1>
<p>Lectura independiente de notas cifradas desde CouchDB mediante Self-hosted LiveSync.
No utiliza Obsidian MCP. Las consultas son de solo lectura; la importación modifica exclusivamente la bóveda privada del cliente, tras confirmación explícita.</p>
<p><button id="load" type="button">Consultar notas en CouchDB</button>
<span id="status" role="status" aria-live="polite"></span></p>
<ul id="notes"></ul><h2 id="selected-title"></h2><pre id="content"></pre>
<p id="edit-action" hidden><a id="edit-link" href="#">Abrir editor Markdown (copia local independiente)</a> <button id="compare-local" type="button">Comparar con copia local</button> <button id="import-private" type="button" hidden>Importar copia privada</button></p>
<p id="comparison-result" role="status" aria-live="polite"></p>
<p>El editor guarda una copia local privada. No modifica CouchDB ni sincroniza las notas.</p>
<p><a href="../">Volver / Back</a></p>
<script>
const button=document.getElementById("load");
const status=document.getElementById("status");
const list=document.getElementById("notes");
const title=document.getElementById("selected-title");
const content=document.getElementById("content");
const editAction=document.getElementById("edit-action");
const editLink=document.getElementById("edit-link");
const compareButton=document.getElementById("compare-local");
const importButton=document.getElementById("import-private");
const comparisonResult=document.getElementById("comparison-result");
let selectionVersion=0;
async function preview(path){
  const endpoint=path===undefined
    ?"../api/remote/encrypted-notes"
    :"../api/remote/note-content?path="+encodeURIComponent(path);
  const response=await fetch(endpoint,{
    method:"GET",credentials:"same-origin",cache:"no-store"
  });
  const data=await response.json();
  if(!response.ok)throw Error(data.error||data.status||"remote_read_failed");
  return data;
}
button.addEventListener("click",async()=>{
  selectionVersion++;
  button.disabled=true;list.replaceChildren();title.textContent="";content.textContent="";
  editAction.hidden=true;editLink.removeAttribute("href");importButton.hidden=true;comparisonResult.textContent="";
  status.textContent="Consultando CouchDB…";
  try{
    const data=await preview();
    for(const path of data.notes||[]){
      const item=document.createElement("li");
      const control=document.createElement("button");
      control.type="button";control.textContent=path;
      control.addEventListener("click",async()=>{
        const currentSelection=++selectionVersion;
        title.textContent=path;content.textContent="Cargando…";
        editAction.hidden=true;editLink.removeAttribute("href");importButton.hidden=true;comparisonResult.textContent="";
        try{
          const note=await preview(path);
          if(currentSelection!==selectionVersion)return;
          if(typeof note.content!=="string")throw Error("remote_content_missing");
          content.textContent=note.content;
          editLink.href="../remote/edit?path="+encodeURIComponent(path);
          compareButton.onclick=async()=>{
            comparisonResult.textContent="Comparando versiones (solo lectura)…";
            try{
              const result=await fetch("../api/remote/compare-local?path="+encodeURIComponent(path),{cache:"no-store"});
              const data=await result.json();
              if(currentSelection!==selectionVersion)return;
              if(!result.ok)throw Error(data.error||"comparison_failed");
              importButton.hidden=!(data.state==="remote_only"&&data.baseline_available===false&&data.remote_write_enabled===false);
              if(!importButton.hidden){
                importButton.onclick=async()=>{
                  if(currentSelection!==selectionVersion)return;
                  if(!confirm("¿Crear una copia Markdown privada de esta nota? No se modifica CouchDB."))return;
                  importButton.disabled=true;comparisonResult.textContent="Importando en el almacenamiento privado…";
                  try{
                    const response=await fetch("../api/remote/import-private",{method:"POST",credentials:"same-origin",
                      headers:{"Content-Type":"application/json","X-Obsidian-Client-Action":"import-private"},
                      body:JSON.stringify({path:path,expected_sha256:data.remote_sha256})});
                    const imported=await response.json();
                    if(currentSelection!==selectionVersion)return;
                    if(!response.ok)throw Error(imported.error||"private_import_failed");
                    importButton.hidden=true;
                    comparisonResult.textContent="Copia privada creada con línea base. CouchDB sin cambios.";
                  }catch(error){if(currentSelection===selectionVersion)comparisonResult.textContent="Importación no completada: "+error.message;}
                  finally{importButton.disabled=false;}
                };
              }
              const labels={no_baseline:"Sin línea base: no se puede atribuir el cambio",unchanged:"Sin cambios desde la línea base",local_changed:"Solo la copia privada ha cambiado",remote_changed:"Solo la nota remota ha cambiado",conflict_both_changed:"Conflicto: ambas versiones han cambiado de forma distinta",same_result_both_changed:"Ambas versiones convergen al mismo contenido",local_missing:"La copia local ha desaparecido"};
              const legacy={remote_only:"No hay copia local",identical:"Copia local idéntica",diverged_unknown_origin:"Las versiones difieren; requiere revisión manual"};
              const state=labels[data.sync_state]||legacy[data.state]||"Estado desconocido";
              comparisonResult.textContent=state+(data.remote_write_enabled===false?" · CouchDB: solo lectura":"");
            }catch(error){if(currentSelection===selectionVersion)comparisonResult.textContent="Error: "+error.message;}
          };
          editAction.hidden=false;
        }catch(error){if(currentSelection===selectionVersion)content.textContent="Error: "+error.message;}
      });
      item.appendChild(control);list.appendChild(item);
    }
    status.textContent=String(data.count||0)+" notas encontradas";
  }catch(error){status.textContent="Error: "+error.message;}
  finally{button.disabled=false;}
});
</script>"""
    response = page(body)
    from flask import make_response
    result = make_response(response)
    result.headers["Cache-Control"] = "no-store"
    result.headers["Content-Security-Policy"] = (
        "default-src 'none'; script-src 'unsafe-inline'; "
        "connect-src 'self'; style-src 'unsafe-inline'; base-uri 'none'")
    return result


@app.get("/api/livesync-cli/connection-check")
def livesync_cli_connection_check():
    """Read-only CouchDB database HEAD. No replication, documents or secrets."""
    import base64
    from livesync_cli_bridge import validate_remote_configuration, prepare_official_cli_settings, CLIUnavailable
    cfg = options()
    if cfg.get("livesync_cli_enabled") is not True:
        return jsonify(status="cli_disabled", remote_writes_enabled=False), 403
    if not validate_remote_configuration(cfg)["configuration_complete"]:
        return jsonify(status="configuration_incomplete", remote_writes_enabled=False), 409
    try:
        settings = prepare_official_cli_settings(cfg)
    except CLIUnavailable:
        return jsonify(status="untrusted_endpoint", remote_writes_enabled=False), 400
    target = settings["couchDB_URI"] + "/" + quote(settings["couchDB_DBNAME"], safe="")
    credential = base64.b64encode(
        (settings["couchDB_USER"] + ":" + settings["couchDB_PASSWORD"]).encode()
    ).decode()
    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    try:
        req = Request(target, headers={"Authorization": "Basic " + credential}, method="HEAD")
        with build_opener(NoRedirect()).open(req, timeout=8) as resp:
            status = resp.status
        if status != 200:
            return jsonify(status="unexpected_response", remote_writes_enabled=False), 502
    except HTTPError as exc:
        result = "authentication_failed" if exc.code in (401, 403) else "database_missing" if exc.code == 404 else "connection_failed"
        return jsonify(status=result, remote_writes_enabled=False), 502
    except (OSError, ValueError, URLError):
        return jsonify(status="connection_failed", remote_writes_enabled=False), 502
    return jsonify(status="database_reachable", encrypted_settings_present=True,
                   encryption_verified=False, remote_writes_enabled=False)


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


def encrypted_note_paths():
    """Read-only, bounded LiveSync index; no decrypted note content fetched."""
    from livesync_crypto import decrypt_hkdf_string, UnsupportedEncryption
    import base64
    o = options()
    if not (o.get("livesync_encryption_enabled") and o.get("livesync_e2ee_passphrase")):
        return None, "encryption_not_configured"
    url = (o.get("couchdb_url") or "").rstrip("/")
    db = o.get("couchdb_database") or ""
    if url != "http://db21ed7f-obsidian-syncserver-ssl:5984" or not re.fullmatch(r"[A-Za-z0-9_.-]+", db):
        return None, "unsupported_connection"
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
    def fetch(suffix, limit=5_000_000):
        with opener.open(Request(base + suffix, headers=headers), timeout=12) as resp:
            raw = resp.read(limit + 1)
        if len(raw) > limit:
            raise ValueError("too_large")
        return json.loads(raw)
    try:
        params = fetch("/_local/obsidian_livesync_sync_parameters", 100_000)
        salt = params.get("pbkdf2salt")
        if not isinstance(salt, str) or not salt:
            return None, "sync_salt_unavailable"
        docs = fetch("/_all_docs?include_docs=true&limit=1200")
    except (OSError, ValueError, HTTPError, URLError):
        return None, "connection_failed"
    paths = set()
    content_shape = {"inline_string": 0, "inline_list": 0, "no_inline": 0, "children_present": 0, "children_nonempty": 0, "children_other": 0}
    unsupported = 0
    attachments = {"images":0,"pdf":0,"other":0,"chunked":0,"total_chunks":0}
    stats = {"candidate": 0, "decrypted": 0, "markdown": 0, "other_extension": 0, "invalid_path": 0, "deleted": 0}
    for row in docs.get("rows", []):
        doc = row.get("doc") if isinstance(row, dict) else None
        if not isinstance(doc, dict) or doc.get("type") not in ("plain", "newnote"):
            continue
        if doc.get("deleted") or doc.get("_deleted") or doc.get("_conflicts"):
            stats["deleted"] += 1
            continue
        stats["candidate"] += 1
        encrypted = doc.get("path")
        if not isinstance(encrypted, str) or not encrypted.startswith("/\\:%="):
            unsupported += 1
            continue
        try:
            path = decrypt_hkdf_string(encrypted[3:], o["livesync_e2ee_passphrase"], salt)
        except UnsupportedEncryption:
            unsupported += 1
            continue
        data = doc.get("data")
        if isinstance(data, str): content_shape["inline_string"] += 1
        elif isinstance(data, list): content_shape["inline_list"] += 1
        else: content_shape["no_inline"] += 1
        children = doc.get("children")
        if isinstance(children, list):
            content_shape["children_present"] += 1
            if children: content_shape["children_nonempty"] += 1
        else: content_shape["children_other"] += 1
        stats["decrypted"] += 1
        shape = stats.setdefault("decrypted_shape", {"prefix_f": 0, "prefix_i": 0, "prefix_slash": 0, "contains_md": 0, "contains_dot": 0, "contains_colon": 0, "length_over_128": 0})
        if path.startswith("f:"): shape["prefix_f"] += 1
        if path.startswith("i:"): shape["prefix_i"] += 1
        if path.startswith("/"): shape["prefix_slash"] += 1
        if ".md" in path.lower(): shape["contains_md"] += 1
        if "." in path: shape["contains_dot"] += 1
        if ":" in path: shape["contains_colon"] += 1
        if len(path) > 128: shape["length_over_128"] += 1
        detail = shape.setdefault("wrapping", {"json_object": 0, "json_string": 0, "json_array": 0, "md_followed_by_quote": 0, "md_followed_by_comma": 0, "md_followed_by_brace": 0, "md_followed_by_slash": 0, "md_followed_by_other": 0})
        stripped = path.lstrip()
        if stripped.startswith("{"): detail["json_object"] += 1
        elif stripped.startswith('"'): detail["json_string"] += 1
        elif stripped.startswith("["): detail["json_array"] += 1
        md_at = path.lower().find(".md")
        if md_at >= 0 and md_at + 3 < len(path):
            next_char = path[md_at + 3]
            key = ('md_followed_by_quote' if next_char in ('"', "'") else
                   'md_followed_by_comma' if next_char == ',' else
                   'md_followed_by_brace' if next_char in ('}', ']') else
                   'md_followed_by_slash' if next_char == '/' else
                   'md_followed_by_other')
            detail[key] += 1
        try:
            wrapped = json.loads(path)
            if isinstance(wrapped, dict):
                schema = stats.setdefault("decrypted_metadata", {"has_children":0,"children_nonempty":0,"has_data":0,"has_eden":0,"has_path":0,"has_type":0,"has_datatype":0,"has_size":0})
                for key in ("children","data","eden","path","type","datatype","size"):
                    if key in wrapped:
                        schema["has_" + key] += 1
                if isinstance(wrapped.get("children"), list) and wrapped["children"]:
                    schema["children_nonempty"] += 1
                candidate_path = wrapped.get("path")
                path = candidate_path if isinstance(candidate_path, str) else ""
            else:
                path = ""
        except (ValueError, TypeError):
            path = ""
        if isinstance(path,str) and not path.endswith(".md") and path and len(path)<=1024:
            extension=path.rsplit(".",1)[-1].lower() if "." in path else ""
            kind=("images" if extension in ("png","jpg","jpeg","gif","webp","svg","avif") else
                  "pdf" if extension=="pdf" else "other")
            attachments[kind]+=1
            if isinstance(wrapped,dict) and isinstance(wrapped.get("children"),list):
                attachments["chunked"]+=1
                attachments["total_chunks"]+=len(wrapped["children"])
        if (path.endswith(".md") and len(path) <= 1024 and
            not path.startswith("/") and "\\" not in path and
            all(part not in ("", ".", "..") for part in path.split("/"))):
            paths.add(path)
            stats["markdown"] += 1
        elif not path.endswith(".md"):
            stats["other_extension"] += 1
        else:
            stats["invalid_path"] += 1
    return {"notes": sorted(paths, key=str.casefold),
            "stats": stats,
            "content_shape": content_shape,
            "attachments": attachments,
            "unsupported": unsupported,
            "truncated": len(docs.get("rows", [])) >= 1200}, None


@app.get("/api/remote/chunk-preflight")
def chunk_preflight():
    """Read-only chunk structure check; returns counts only, no IDs or contents."""
    from livesync_crypto import decrypt_hkdf_string, UnsupportedEncryption
    import base64
    cfg = options()
    if not (cfg.get("livesync_encryption_enabled") and cfg.get("livesync_e2ee_passphrase")):
        return jsonify(status="encryption_not_configured"), 400
    if (cfg.get("couchdb_url") or "").rstrip("/") != "http://db21ed7f-obsidian-syncserver-ssl:5984":
        return jsonify(status="unsupported_connection"), 400
    db = cfg.get("couchdb_database") or ""
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", db):
        return jsonify(status="invalid_database"), 400
    user = cfg.get("couchdb_username") or ""
    headers = {"Accept": "application/json"}
    if user:
        headers["Authorization"] = "Basic " + base64.b64encode(
            (user + ":" + (cfg.get("couchdb_password") or "")).encode()).decode()
    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    opener = build_opener(NoRedirect())
    base = cfg["couchdb_url"].rstrip("/") + "/" + quote(db, safe="")
    def fetch(path, limit=500000):
        with opener.open(Request(base + path, headers=headers), timeout=9) as response:
            payload = response.read(limit+1)
        if len(payload) > limit:
            raise ValueError("response_too_large")
        return json.loads(payload)
    try:
        salt = fetch("/_local/obsidian_livesync_sync_parameters",100000).get("pbkdf2salt")
        if not isinstance(salt, str) or not salt:
            return jsonify(status="salt_missing", read_only=True)
        docs = fetch("/_all_docs?include_docs=true&limit=160",2000000).get("rows",[])
        candidate = None
        for row in docs:
            doc = row.get("doc") if isinstance(row, dict) else None
            if not isinstance(doc,dict) or doc.get("deleted") or doc.get("_deleted") or doc.get("_conflicts"):
                continue
            encrypted = doc.get("path")
            if doc.get("type") not in ("plain","newnote") or not isinstance(encrypted,str) or not encrypted.startswith("/\\:%="):
                continue
            try:
                meta = json.loads(decrypt_hkdf_string(encrypted[3:],cfg["livesync_e2ee_passphrase"],salt))
            except (UnsupportedEncryption, ValueError):
                continue
            if isinstance(meta,dict) and isinstance(meta.get("path"),str) and meta["path"].endswith(".md") and isinstance(meta.get("children"),list) and meta["children"]:
                candidate = meta
                break
        if candidate is None:
            return jsonify(status="no_chunked_note_in_sample",read_only=True)
        children=candidate["children"]
        if len(children)>512 or not all(isinstance(c,str) and 0<len(c)<256 for c in children):
            return jsonify(status="invalid_children",read_only=True)
        counters={"referenced":len(children),"found":0,"missing":0,"encrypted_hkdf":0,"encrypted_other":0,"plaintext":0,"other_type":0}
        for child in children[:12]:
            try:
                d=fetch("/"+quote(child,safe=""),150000)
            except HTTPError as err:
                if err.code==404:
                    counters["missing"]+=1
                    continue
                raise
            counters["found"]+=1
            if d.get("type")!="leaf":
                counters["other_type"]+=1
            elif isinstance(d.get("data"),str) and d["data"].startswith("%="):
                counters["encrypted_hkdf"]+=1
            elif d.get("e_") or (isinstance(d.get("data"),str) and d["data"].startswith("%")):
                counters["encrypted_other"]+=1
            else:
                counters["plaintext"]+=1
        complete = True
        parts = []
        for child in children:
            try:
                d = fetch("/" + quote(child, safe=""), 150000)
                if d.get("type") != "leaf" or not isinstance(d.get("data"), str) or not d["data"].startswith("%="):
                    complete = False
                    break
                parts.append(decrypt_hkdf_string(d["data"], cfg["livesync_e2ee_passphrase"], salt))
            except (HTTPError, URLError, OSError, ValueError, UnsupportedEncryption):
                complete = False
                break
        if not complete:
            return jsonify(status="reconstruction_incomplete",read_only=True,referenced=len(children),decrypted=len(parts))
        combined = "".join(parts)
        byte_length = len(combined.encode("utf-8"))
        expected = candidate.get("size")
        return jsonify(status="reconstructed",read_only=True,referenced=len(children),
                       decrypted=len(parts),utf8_bytes=byte_length,
                       expected_size=expected if isinstance(expected,int) and expected>=0 else None,
                       size_matches=(byte_length==expected) if isinstance(expected,int) and expected>=0 else None,
                       contents_returned=False)
    except (HTTPError, URLError, OSError, ValueError, TypeError):
        return jsonify(status="chunk_probe_failed",read_only=True),502


def read_encrypted_note(requested, *, verify_revision=False):
    """One LiveSync note, complete authenticated chunks, strictly read-only."""
    from livesync_crypto import decrypt_hkdf_string, UnsupportedEncryption
    import base64
    cfg = options()
    if not isinstance(requested,str) or len(requested)>1024 or not requested.endswith(".md") or requested.startswith("/") or "\\" in requested or any(x in ("",".","..") for x in requested.split("/")):
        return None,"invalid_path"
    if not cfg.get("livesync_encryption_enabled") or not cfg.get("livesync_e2ee_passphrase"):
        return None,"encryption_not_configured"
    url=(cfg.get("couchdb_url") or "").rstrip("/")
    db=cfg.get("couchdb_database") or ""
    if url!="http://db21ed7f-obsidian-syncserver-ssl:5984" or not re.fullmatch(r"[A-Za-z0-9_.-]+",db):
        return None,"unsupported_connection"
    headers={"Accept":"application/json"}
    user=cfg.get("couchdb_username") or ""
    if user:
        headers["Authorization"]="Basic "+base64.b64encode((user+":"+(cfg.get("couchdb_password") or "")).encode()).decode()
    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    opener=build_opener(NoRedirect())
    base=url+"/"+quote(db,safe="")
    def fetch(suffix,limit):
        with opener.open(Request(base+suffix,headers=headers),timeout=12) as resp:
            raw=resp.read(limit+1)
        if len(raw)>limit: raise ValueError("oversized")
        return json.loads(raw)
    try:
        salt=fetch("/_local/obsidian_livesync_sync_parameters",100000).get("pbkdf2salt")
        if not isinstance(salt,str) or not salt: return None,"salt_missing"
        rows=fetch("/_all_docs?include_docs=true&limit=1200",5000000).get("rows",[])
        candidate=None
        selected_parent=None
        match_count=0
        for row in rows:
            doc=row.get("doc") if isinstance(row,dict) else None
            if not isinstance(doc,dict) or doc.get("type") not in ("plain","newnote") or doc.get("deleted") or doc.get("_deleted") or doc.get("_conflicts"): continue
            ciphertext=doc.get("path")
            if not isinstance(ciphertext,str) or not ciphertext.startswith("/\\:%="): continue
            try: meta=json.loads(decrypt_hkdf_string(ciphertext[3:],cfg["livesync_e2ee_passphrase"],salt))
            except (UnsupportedEncryption,ValueError): continue
            if isinstance(meta,dict) and meta.get("path")==requested:
                match_count+=1
                if match_count>1 and verify_revision:
                    return None,"ambiguous_parent"
                candidate=meta
                selected_parent=doc
                if not verify_revision:
                    break
        if candidate is None: return None,"not_found"
        if verify_revision:
            from livesync_encrypted_parent_snapshot import validate_encrypted_parent_snapshot
            from livesync_write_preflight import UnsafeWrite
            try:
                validate_encrypted_parent_snapshot(selected_parent,candidate,requested,
                                                   selected_parent.get("_rev"))
            except UnsafeWrite:
                return None,"invalid_parent_snapshot"
        from livesync_metadata import validate_encrypted_parent, UnsupportedMetadata
        try:
            children = validate_encrypted_parent(candidate, requested)
        except UnsupportedMetadata:
            return None, "unsupported_metadata"
        parts=[]
        for child in children:
            leaf=fetch("/"+quote(child,safe=""),150000)
            if leaf.get("type")!="leaf" or not isinstance(leaf.get("data"),str) or not leaf["data"].startswith("%=") or leaf.get("_deleted") or leaf.get("_conflicts"): return None,"unsupported_chunk"
            parts.append(decrypt_hkdf_string(leaf["data"],cfg["livesync_e2ee_passphrase"],salt))
        content="".join(parts)
        if len(content.encode("utf-8"))>2000000: return None,"too_large"
        expected=candidate.get("size")
        if type(expected) is int and len(content.encode("utf-8"))!=expected: return None,"size_mismatch"
        if verify_revision:
            # Check the same parent's revision again after reading its chunks.
            # An actual write must still perform CouchDB conditional CAS.
            fresh=fetch("/"+quote(selected_parent["_id"],safe=""),500000)
            if (not isinstance(fresh,dict)
                    or fresh.get("_id")!=selected_parent["_id"]
                    or fresh.get("_rev")!=selected_parent["_rev"]
                    or fresh.get("path")!=selected_parent["path"]
                    or fresh.get("_deleted") or fresh.get("_conflicts")):
                return None,"remote_revision_changed"
        return content,None
    except (HTTPError,URLError,OSError,ValueError,TypeError,UnsupportedEncryption):
        return None,"read_failed"


def render_wikilinks(content, current_path, known_notes):
    """Render only resolvable wiki-links. Never trust or inject target HTML."""
    known=set(known_notes)
    by_basename={}
    for note in known:
        by_basename.setdefault(note.rsplit("/",1)[-1].casefold(),[]).append(note)
    token_pattern=re.compile(r"\\[\\[([^\\[\\]\\n]{1,300})\\]\\]")
    replacements={}
    def replace(match):
        raw=match.group(1)
        link,_,alias=raw.partition("|")
        target=link.split("#",1)[0].strip()
        if not target: return match.group(0)
        if not target.lower().endswith(".md"): target+=".md"
        candidates=[target,(current_path.rsplit("/",1)[0]+"/"+target) if "/" in current_path else target]
        resolved=next((p for p in candidates if p in known),None)
        if not resolved:
            alternatives=by_basename.get(target.rsplit("/",1)[-1].casefold(),[])
            if len(alternatives)==1: resolved=alternatives[0]
        if not resolved: return match.group(0)
        label=(alias.strip() or link.strip())[:300]
        token="OBSIDIANWIKILINKTOKEN"+str(len(replacements))+"END"
        replacements[token]='<a href="?path='+quote(resolved,safe="")+'">'+html.escape(label)+'</a>'
        return token
    processed=token_pattern.sub(replace,content)
    safe=html.escape(processed)
    for token,link in replacements.items():
        safe=safe.replace(token,link)
    return safe


@app.get("/api/remote/parent-revision")
def remote_parent_revision(_requested_path=None):
    """Read-only revision lookup for encrypted parent metadata.

    Never expose remote document IDs, revisions, ciphertext or credentials to
    the browser. A future write requires a fresh server-side snapshot.
    """
    from livesync_encrypted_parent_snapshot import validate_encrypted_parent_snapshot
    from livesync_crypto import decrypt_hkdf_string, UnsupportedEncryption
    from livesync_write_preflight import validate_write_request, UnsafeWrite
    import base64
    requested=_requested_path if _requested_path is not None else request.args.get("path","")
    try:
        validate_write_request(requested,"",None,creating=True)
    except (UnsafeWrite,ValueError):
        return jsonify(error="invalid_path"),400
    cfg=options()
    if not cfg.get("livesync_encryption_enabled") or not cfg.get("livesync_e2ee_passphrase"):
        return jsonify(error="encryption_not_configured"),409
    endpoint=(cfg.get("couchdb_url") or "").rstrip("/")
    database=cfg.get("couchdb_database") or ""
    if endpoint!="http://db21ed7f-obsidian-syncserver-ssl:5984" or not re.fullmatch(r"[A-Za-z0-9_.-]+",database):
        return jsonify(error="unsupported_connection"),403
    user=cfg.get("couchdb_username") or ""
    headers={"Accept":"application/json"}
    if user:
        headers["Authorization"]="Basic "+base64.b64encode(
            (user+":"+(cfg.get("couchdb_password") or "")).encode()).decode()
    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self,req,fp,code,msg,headers,newurl):
            return None
    opener=build_opener(NoRedirect())
    base=endpoint+"/"+quote(database,safe="")
    def fetch(suffix,limit):
        with opener.open(Request(base+suffix,headers=headers),timeout=12) as response:
            raw=response.read(limit+1)
        if len(raw)>limit:
            raise ValueError("oversized")
        return json.loads(raw)
    try:
        salt=fetch("/_local/obsidian_livesync_sync_parameters",100000).get("pbkdf2salt")
        if not isinstance(salt,str) or not salt:
            raise ValueError("missing_salt")
        rows=fetch("/_all_docs?include_docs=true&limit=1200",5000000).get("rows",[])
        matches=[]
        for row in rows:
            stored=row.get("doc") if isinstance(row,dict) else None
            if not isinstance(stored,dict) or stored.get("type") not in ("plain","newnote"):
                continue
            ciphertext=stored.get("path")
            if not isinstance(ciphertext,str) or not ciphertext.startswith("/\\:%="):
                continue
            try:
                decoded=json.loads(decrypt_hkdf_string(
                    ciphertext[3:],cfg["livesync_e2ee_passphrase"],salt))
            except (UnsupportedEncryption,ValueError,TypeError):
                continue
            if isinstance(decoded,dict) and decoded.get("path")==requested:
                matches.append((stored,decoded))
        if len(matches)!=1:
            return jsonify(error="missing_or_ambiguous_parent",write_supported=False),409
        stored,decoded=matches[0]
        result=validate_encrypted_parent_snapshot(
            stored,decoded,requested,stored.get("_rev"))
        response=jsonify(status="verified_read_only",path=requested,
                         revision_available=bool(result["_rev"]),
                         encrypted_parent=True,write_supported=False,
                         child_count=len(result["children"]))
        response.headers["Cache-Control"]="no-store"
        return response
    except (HTTPError,URLError,OSError,ValueError,TypeError,UnsafeWrite,UnsupportedEncryption):
        return jsonify(error="revision_inspection_failed",write_supported=False),409


@app.get("/api/remote/note-content")
def remote_note_content():
    """Read-only plaintext for an editor; no CouchDB writes until LiveSync encoding is validated."""
    requested = request.args.get("path", "")
    if not requested or len(requested) > 1024 or not requested.lower().endswith(".md"):
        return jsonify(error="invalid_path"), 400
    content, error = read_encrypted_note(requested)
    if error:
        return jsonify(error=error), 404 if error == "not_found" else 422
    response = jsonify(path=requested, content=content, read_only=True,
                       saving_supported=False, source="livesync_e2ee")
    response.headers["Cache-Control"] = "no-store"
    return response


from threading import Lock
_local_save_lock = Lock()

# The existing editor endpoints now persist Markdown in a private /data vault.
# No real /share files, configured remote, or LiveSync CLI database is modified.
_PRIVATE_VAULT = "/data/obsidian-client-markdown"
_PRIVATE_BACKUPS = "/data/obsidian-client-backups"
_PRIVATE_BASELINES = "/data/obsidian-client-sync-baselines"

# Opt-in only: the MCP's already-provisioned LiveSync Markdown vault.
# No second synchronizer is started. The legacy shared MCP path must exist.
_MCP_SHARED_VAULT = "/share/obsidian-shared-vault"


def editor_markdown_vault():
    """Resolve the Client's own Markdown vault or explicit compatibility mode."""
    from private_markdown_vault import LocalVaultError
    from storage_selection import select_storage, StorageSelectionError
    try:
        return select_storage(options(), private_vault=_PRIVATE_VAULT,
                              shared_vault=_MCP_SHARED_VAULT)["vault"]
    except StorageSelectionError as exc:
        raise LocalVaultError(str(exc)) from exc


@app.get("/api/livesync-cli/independent-preflight")
def independent_livesync_preflight():
    """Read-only diagnostics for a future independent Client sync engine."""
    from client_sync_engine import preflight
    result = jsonify(preflight(options()))
    result.headers["Cache-Control"] = "no-store"
    return result


@app.get("/api/remote/compare-local")
def compare_local_and_remote():
    """Read-only compare; never infer a direction without a sync baseline."""
    from private_markdown_vault import LocalVaultError, read_note
    from client_note_comparison import compare_note_contents
    from storage_selection import select_storage, StorageSelectionError
    path = request.args.get("path", "")
    try:
        selected = select_storage(options(), private_vault=_PRIVATE_VAULT,
                                  shared_vault=_MCP_SHARED_VAULT)
    except StorageSelectionError:
        return jsonify(error="storage_not_ready", read_only=True), 409
    if not selected["independent_of_mcp"] or selected["mode"] != "local":
        return jsonify(error="independent_local_mode_required", read_only=True), 409
    # Use the strict local vault path validator before any remote request.
    try:
        from private_markdown_vault import _path
        _path(editor_markdown_vault(), path)
    except LocalVaultError:
        return jsonify(error="invalid_note_path", read_only=True), 400
    remote, error = read_encrypted_note(path, verify_revision=True)
    if error:
        return jsonify(error="remote_snapshot_not_verified", read_only=True), 409
    try:
        with _local_save_lock:
            local = read_note(editor_markdown_vault(), path)["content"]
    except LocalVaultError as exc:
        if exc.code == "note_not_found":
            local = None
        else:
            return jsonify(error="local_read_failed", read_only=True), 409
    from client_sync_baseline import load_baseline, classify, BaselineError
    try:
        baseline = load_baseline(_PRIVATE_BASELINES, path)
        lineage = classify(baseline, remote, local)
    except BaselineError:
        return jsonify(error="baseline_unavailable", read_only=True), 409
    result = compare_note_contents(remote, local)
    response = jsonify(path=path, **result, **lineage, read_only=True,
                       remote_write_enabled=False)
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/api/remote/diff-local")
def readonly_remote_local_diff():
    """Show bounded private-vs-remote differences, no writes or merge actions."""
    from private_markdown_vault import LocalVaultError, read_note, _path
    from client_note_diff import compare_lines, DiffUnavailable
    from client_sync_baseline import BaselineError, load_baseline, classify
    from storage_selection import select_storage, StorageSelectionError
    path = request.args.get("path", "")
    try:
        selected = select_storage(options(), private_vault=_PRIVATE_VAULT,
                                  shared_vault=_MCP_SHARED_VAULT)
        if not selected["independent_of_mcp"] or selected["mode"] != "local":
            return jsonify(error="independent_local_mode_required", read_only=True), 409
        _path(editor_markdown_vault(), path)
    except (LocalVaultError, StorageSelectionError):
        return jsonify(error="invalid_storage_or_path", read_only=True), 409
    remote, error = read_encrypted_note(path, verify_revision=True)
    if error or not isinstance(remote, str):
        return jsonify(error="remote_snapshot_not_verified", read_only=True), 409
    try:
        with _local_save_lock:
            local = read_note(editor_markdown_vault(), path)["content"]
        baseline = load_baseline(_PRIVATE_BASELINES, path)
        result = compare_lines(remote, local)
        lineage = classify(baseline, remote, local)
    except LocalVaultError as exc:
        return jsonify(error="local_copy_required" if exc.code == "note_not_found"
                       else "local_read_failed", read_only=True), 409
    except (BaselineError, DiffUnavailable) as exc:
        return jsonify(error=str(exc), read_only=True), 409
    response = jsonify(path=path, **result, **lineage,
                       read_only=True, remote_write_enabled=False,
                       merge_enabled=False)
    response.headers["Cache-Control"] = "no-store"
    return response


@app.post("/api/remote/establish-baseline")
def establish_verified_baseline():
    """Explicit enrollment only when private/local and verified remote copies match."""
    from private_markdown_vault import LocalVaultError, read_note, _path
    from client_sync_baseline import establish_baseline, BaselineError, digest
    from storage_selection import select_storage, StorageSelectionError
    if request.headers.get("X-Obsidian-Client-Action") != "establish-baseline":
        return jsonify(error="missing_action_header"), 403
    if request.headers.get("Sec-Fetch-Site") not in (None, "same-origin"):
        return jsonify(error="cross_origin_blocked"), 403
    if request.headers.get("Origin") and request.headers.get("Sec-Fetch-Site") != "same-origin":
        return jsonify(error="cross_origin_blocked"), 403
    if request.mimetype != "application/json" or request.content_length is None or request.content_length > 2048:
        return jsonify(error="invalid_request"), 400
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or set(payload) != {"path", "expected_sha256"}:
        return jsonify(error="invalid_request"), 400
    path = payload.get("path")
    expected = payload.get("expected_sha256")
    try:
        selected = select_storage(options(), private_vault=_PRIVATE_VAULT,
                                  shared_vault=_MCP_SHARED_VAULT)
        if not selected["independent_of_mcp"] or selected["mode"] != "local":
            return jsonify(error="independent_local_mode_required"), 409
        _path(editor_markdown_vault(), path)
        if not isinstance(expected, str) or len(expected) != 64:
            return jsonify(error="invalid_expected_hash"), 400
    except (StorageSelectionError, LocalVaultError):
        return jsonify(error="invalid_storage_or_path"), 409
    remote, error = read_encrypted_note(path, verify_revision=True)
    if error:
        return jsonify(error="remote_snapshot_not_verified"), 409
    if digest(remote) != expected:
        return jsonify(error="remote_content_changed"), 409
    try:
        with _local_save_lock:
            local = read_note(editor_markdown_vault(), path)["content"]
            if digest(local) != expected:
                return jsonify(error="local_content_changed"), 409
            baseline = establish_baseline(_PRIVATE_BASELINES,
                                          path, remote, local)
    except LocalVaultError:
        return jsonify(error="local_copy_unavailable"), 409
    except BaselineError:
        return jsonify(error="baseline_conflict"), 409
    return jsonify(status="baseline_established", created=baseline["created"],
                   sha256=baseline["sha256"], remote_write_enabled=False,
                   sync_enabled=False), 201 if baseline["created"] else 200


@app.post("/api/remote/import-private")
def import_verified_remote_note():
    """Explicit one-way import to the Client's private Markdown vault only.

    A new note is created exclusively when absent locally and when the
    authenticated remote snapshot matches the exact hash confirmed by the
    caller. A failed baseline registration never triggers a remote write.
    """
    from private_markdown_vault import LocalVaultError, read_note, save_note, _path
    from client_sync_baseline import BaselineError, digest, load_baseline, establish_baseline, SHA
    from storage_selection import select_storage, StorageSelectionError
    if request.headers.get("X-Obsidian-Client-Action") != "import-private":
        return jsonify(error="missing_action_header"), 403
    if request.headers.get("Sec-Fetch-Site") not in (None, "same-origin"):
        return jsonify(error="cross_origin_blocked"), 403
    if request.headers.get("Origin") and request.headers.get("Sec-Fetch-Site") != "same-origin":
        return jsonify(error="cross_origin_blocked"), 403
    if (request.mimetype != "application/json" or request.content_length is None
            or request.content_length > 2048):
        return jsonify(error="invalid_request"), 400
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or set(payload) != {"path", "expected_sha256"}:
        return jsonify(error="invalid_request"), 400
    path, expected = payload["path"], payload["expected_sha256"]
    if not isinstance(expected, str) or not SHA.fullmatch(expected):
        return jsonify(error="invalid_expected_hash"), 400
    try:
        selected = select_storage(options(), private_vault=_PRIVATE_VAULT,
                                  shared_vault=_MCP_SHARED_VAULT)
        if not selected["independent_of_mcp"] or selected["mode"] != "local":
            return jsonify(error="independent_local_mode_required"), 409
        _path(editor_markdown_vault(), path)
        if load_baseline(_PRIVATE_BASELINES, path) is not None:
            return jsonify(error="baseline_already_exists"), 409
    except (LocalVaultError, StorageSelectionError, BaselineError, OSError):
        return jsonify(error="invalid_storage_path_or_baseline"), 409
    remote, error = read_encrypted_note(path, verify_revision=True)
    if error or not isinstance(remote, str):
        return jsonify(error="remote_snapshot_not_verified"), 409
    if digest(remote) != expected:
        return jsonify(error="remote_content_changed"), 409
    try:
        with _local_save_lock:
            if load_baseline(_PRIVATE_BASELINES, path) is not None:
                return jsonify(error="baseline_already_exists"), 409
            try:
                read_note(editor_markdown_vault(), path)
            except LocalVaultError as exc:
                if exc.code != "note_not_found":
                    return jsonify(error="local_read_failed"), 409
            else:
                return jsonify(error="local_note_exists"), 409
            # Reuses the vault's write lock and atomic create-only semantics.
            saved = save_note(editor_markdown_vault(), _PRIVATE_BACKUPS,
                              path, remote, "create")
            try:
                baseline = establish_baseline(_PRIVATE_BASELINES,
                                              path, remote, remote)
            except (BaselineError, OSError):
                # The newly created Markdown stays intact: never delete an
                # imported note to compensate for a metadata error.
                return jsonify(error="baseline_registration_failed",
                               local_created=True, remote_write_enabled=False,
                               recovery="establish_baseline_after_verification"), 409
    except (LocalVaultError, BaselineError, OSError):
        return jsonify(error="private_import_failed", remote_write_enabled=False), 409
    response = jsonify(status="imported_private", path=path,
                       sha256=saved["sha256"], baseline_created=baseline["created"],
                       remote_write_enabled=False, remote_synced=False)
    response.headers["Cache-Control"] = "no-store"
    return response, 201


@app.get("/api/editor/storage-status")
def editor_storage_status():
    """Read-only state; never claim CouchDB synchronization before it exists."""
    from storage_selection import select_storage, StorageSelectionError
    try:
        selected = select_storage(options(), private_vault=_PRIVATE_VAULT,
                                  shared_vault=_MCP_SHARED_VAULT)
    except StorageSelectionError as exc:
        return jsonify(error=str(exc), ready=False), 409
    # Do not expose user files or credentials; this only reports configured mode.
    return jsonify(**selected, ready=selected["sync_engine"] != "not_implemented")





@app.get("/api/livesync-cli/local-note")
def livesync_cli_local_note():
    """Read local Markdown from the private experimental vault."""
    from private_markdown_vault import LocalVaultError, read_note
    name = request.args.get("path", "")
    try:
        with _local_save_lock:
            note = read_note(editor_markdown_vault(), name)
        return jsonify(**note, remote_synced=False)
    except LocalVaultError as exc:
        code = 404 if exc.code == "note_not_found" else 409 if exc.code in ("mcp_shared_vault_unavailable", "livesync_not_ready") else 400
        return jsonify(error=exc.code), code


@app.post("/api/livesync-cli/local-save")
def livesync_cli_local_save():
    """Save private Markdown atomically; remote synchronization is disabled."""
    from private_markdown_vault import LocalVaultError, read_note, save_note
    if options().get("editor_storage_mode") == "livesync":
        return jsonify(error="livesync_not_ready", remote_synced=False), 409
    if request.headers.get("X-Obsidian-Client-Action") != "local-save":
        return jsonify(error="missing_action_header"), 403
    if request.headers.get("Sec-Fetch-Site") not in (None, "same-origin"):
        return jsonify(error="cross_origin_blocked"), 403
    if request.headers.get("Origin") and request.headers.get("Sec-Fetch-Site") != "same-origin":
        return jsonify(error="cross_origin_blocked"), 403
    if request.mimetype != "application/json" or request.content_length is None or request.content_length > 2_100_000:
        return jsonify(error="invalid_request"), 400
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or set(payload) - {"path", "content", "mode", "expected_content"}:
        return jsonify(error="invalid_request"), 400
    name, content, mode = payload.get("path"), payload.get("content"), payload.get("mode")
    try:
        with _local_save_lock:
            if mode == "update":
                expected = payload.get("expected_content")
                if not isinstance(expected, str):
                    return jsonify(error="expected_content_required"), 409
                from hashlib import sha256
                revision = sha256(expected.encode("utf-8")).hexdigest()
            else:
                revision = None
            result = save_note(editor_markdown_vault(), _PRIVATE_BACKUPS, name, content, mode,
                               expected_sha256=revision)
        return jsonify(**result)
    except LocalVaultError as exc:
        code = (409 if exc.code in ("note_exists", "revision_conflict",
                                   "expected_revision_required", "note_not_found")
                else 413 if exc.code == "note_too_large" else 409 if exc.code in ("mcp_shared_vault_unavailable", "livesync_not_ready") else 400)
        return jsonify(error=exc.code), code


@app.get("/private-drafts")
def private_drafts():
    """Browse isolated local drafts, never the configured remote vault."""
    from private_markdown_vault import LocalVaultError, list_notes
    try:
        with _local_save_lock:
            notes = list_notes(editor_markdown_vault())
    except LocalVaultError:
        return page("<h1>Borradores locales</h1><p>No se pudo abrir el almacén local.</p>"), 409
    rows = "".join(
        '<li><a href="remote/new?path=' + quote(name, safe="") + '">' +
        html.escape(name) + "</a></li>" for name in notes)
    return page('<h1>Notas Markdown / Markdown notes</h1>'
                '<p>Las notas compartidas se sincronizan mediante el MCP; los borradores privados no. Modo LiveSync independiente: en desarrollo.</p>'
                '<p><a href="remote/new?path=Nuevo.md">Crear nota / New note</a></p>'
                '<ul>' + rows + '</ul>'
                '<p><a href="./">Volver / Back</a></p>')


@app.get("/remote/new")
def remote_new_draft():
    """Create an offline Markdown draft; never write to CouchDB."""
    from livesync_write_preflight import validate_write_request, UnsafeWrite
    requested = request.args.get("path", "")
    try:
        validate_write_request(requested, "", None, creating=True)
    except UnsafeWrite:
        return page("<h2>Ruta de nota no válida</h2>"), 400
    path_json = json.dumps(requested, ensure_ascii=True).replace("<", "\\u003c")
    return page(
        '<p><a href="../">← Volver</a></p><h2>Nueva nota (borrador)</h2>'
        '<p class="muted">Se guarda como archivo Markdown. En modo compartido, el MCP se encarga de sincronizar mediante LiveSync.</p>'
        '<h3>' + html.escape(requested) + '</h3>'
        '<textarea id="editor" style="width:100%;height:50vh;font:14px monospace"></textarea>'
        '<p><button id="saveLocal" type="button">Guardar Markdown</button> '
        '<button id="export" type="button">Exportar .md</button></p>'
        '<p id="saveStatus" role="status"></p>'
        '<pre id="preview" style="white-space:pre-wrap"></pre>'
        '<script>const path=' + path_json + ';'
        'const editor=document.getElementById("editor");'
        'let savedContent=null;let loadingLocal=true;let dirty=false;let saving=false;'
        'const key="obsidian-new-draft:"+path;'
        'try{editor.value=sessionStorage.getItem(key)||""}catch(_){}'
        'const refresh=()=>{document.getElementById("preview").textContent=editor.value;'
        'try{sessionStorage.setItem(key,editor.value)}catch(_){}};'
        'editor.addEventListener("input",()=>{dirty=true;refresh()});'
        'fetch("../api/livesync-cli/local-note?path="+encodeURIComponent(path))'
        '.then(r=>r.ok?r.json():null).then(data=>{if(data){'
        'savedContent=data.content;'
        'const draft=editor.value;editor.value=data.content;'
        'if((dirty||draft)&&draft!==data.content&&confirm("Recuperar borrador anterior?"))editor.value=draft;'
        'else try{sessionStorage.removeItem(key)}catch(_){}'
        'document.getElementById("preview").textContent=editor.value;'
        'document.getElementById("saveStatus").textContent="Nota Markdown local cargada";'
        '}}).catch(()=>{}).finally(()=>{loadingLocal=false});'
        'document.getElementById("saveLocal").onclick=async()=>{'
        'if(loadingLocal||saving){document.getElementById("saveStatus").textContent="Espera a finalizar la operación anterior";return;}'
        'saving=true;document.getElementById("saveLocal").disabled=true;'
        'const submitted=editor.value;'
        'const status=document.getElementById("saveStatus");status.textContent="Guardando...";'
        'try{const r=await fetch("../api/livesync-cli/local-save",{method:"POST",'
        'headers:{"Content-Type":"application/json","X-Obsidian-Client-Action":"local-save"},'
        'body:JSON.stringify({mode:savedContent===null?"create":"update",path:path,'
        'expected_content:savedContent,content:submitted})});'
        'const data=await r.json();if(!r.ok)throw Error(data.error||"save_failed");'
        'savedContent=submitted;dirty=editor.value!==submitted;'
        'status.textContent="Archivo Markdown guardado. LiveSync gestiona la sincronización solo en modo compartido.";'
        'try{if(!dirty)sessionStorage.removeItem(key);else refresh()}catch(_){}'
        '}catch(e){status.textContent="No guardado: "+e.message}'
        'finally{saving=false;document.getElementById("saveLocal").disabled=false}};'
        'document.getElementById("export").onclick=()=>{'
        'const url=URL.createObjectURL(new Blob([editor.value],{type:"text/markdown;charset=utf-8"}));'
        'const a=document.createElement("a");a.href=url;a.download=path.split("/").pop();'
        'a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};'
        'window.addEventListener("beforeunload",event=>{if(editor.value!==(savedContent===null?"":savedContent)){'
        'event.preventDefault();event.returnValue="";}});'
        'document.getElementById("preview").textContent=editor.value;</script>'
    )


@app.post("/api/remote/write-preview")
def remote_write_preview():
    """Read-only preview of an intended edit. NEVER submits a CouchDB write.

    An actual remote save still requires independently verified _rev and
    document identity, and is intentionally not implemented in this endpoint.
    """
    import hashlib
    from livesync_write_preflight import validate_write_request, UnsafeWrite
    if request.headers.get("X-Obsidian-Client-Action") != "write-preview":
        return jsonify(error="missing_action_header"), 403
    if request.headers.get("Sec-Fetch-Site") not in (None, "same-origin"):
        return jsonify(error="cross_origin_blocked"), 403
    if request.headers.get("Origin") and request.headers.get("Sec-Fetch-Site") != "same-origin":
        return jsonify(error="cross_origin_blocked"), 403
    if request.mimetype != "application/json" or request.content_length is None or request.content_length > 2_100_000:
        return jsonify(error="invalid_request"), 400
    payload=request.get_json(silent=True)
    if not isinstance(payload,dict) or set(payload)!={"path","content","expected_content"}:
        return jsonify(error="invalid_request"), 400
    path,content,expected=payload["path"],payload["content"],payload["expected_content"]
    if not isinstance(expected,str):
        return jsonify(error="expected_content_required"), 400
    try:
        expected_bytes=expected.encode("utf-8")
    except UnicodeError:
        return jsonify(error="invalid_expected_content_encoding"), 400
    try:
        result=validate_write_request(path,content,None,creating=True)
    except (UnsafeWrite,ValueError,UnicodeError):
        return jsonify(error="invalid_note"), 400
    # Verify plaintext against a parent whose revision is re-read after chunks.
    current,error=read_encrypted_note(path,verify_revision=True)
    if error:
        return jsonify(error="remote_snapshot_not_verified",
                       remote_write_enabled=False,save_supported=False),409
    try:
        current_bytes=current.encode("utf-8")
    except (AttributeError, UnicodeError):
        return jsonify(error="remote_snapshot_not_verified",
                       remote_write_enabled=False,save_supported=False),409
    if hashlib.sha256(current_bytes).digest()!=hashlib.sha256(expected_bytes).digest():
        return jsonify(error="remote_content_conflict",
                       remote_write_enabled=False,save_supported=False),409
    response=jsonify(path=path, bytes=result["bytes"], operation="update",
                   content_changed=content!=current,
                   status="preview_only", remote_write_enabled=False,
                   revision_verified=True, save_supported=False)
    response.headers["Cache-Control"]="no-store"
    return response


@app.get("/remote/edit")
def remote_edit_draft():
    """Edit a temporary browser draft without writing to LiveSync."""
    requested = request.args.get("path", "")
    from livesync_write_preflight import validate_write_request, UnsafeWrite
    try:
        validate_write_request(requested, "", None, creating=True)
    except (UnsafeWrite, ValueError, TypeError):
        return page("<h2>Ruta de nota no válida</h2>"), 400
    content, error = read_encrypted_note(requested)
    cli_fallback = bool(error and options().get("livesync_cli_enabled") is True)
    if error and not cli_fallback:
        return page("<h2>No se puede abrir la nota</h2><p>" + html.escape(error) + "</p>"), 404
    if cli_fallback:
        content = ""
    # JSON encoding protects JS string boundaries; escape HTML script terminators.
    script_data = json.dumps({"path": requested, "content": content, "needs_remote_load": cli_fallback}, ensure_ascii=True).replace("<", "\\u003c")
    body = (
        '<p><a href="../">← Volver</a></p><h2>Borrador Markdown</h2>'
        '<p class="muted">El guardado escribe Markdown local; en modo compartido LiveSync sincroniza mediante el MCP.</p>'
        '<h3>' + html.escape(requested) + '</h3>'
        '<textarea id="editor" style="width:100%;height:50vh;font:14px monospace"></textarea>'
        '<p><button type="button" id="copyDraft">Copiar Markdown</button> '
        '<button type="button" id="discardDraft">Descartar borrador</button> '
        '<button type="button" id="exportDraft">Exportar .md</button> '
        '<button id="saveLocal" type="button">Guardar localmente (sin sincronizar)</button> '
        '<button id="loadRemote" type="button">Recargar desde CouchDB (solo lectura)</button> '
        '<button id="previewRemote" type="button">Comprobar guardado remoto (sin escribir)</button></p>'
        '<p id="saveStatus" role="status"></p>'
        '<h3>Vista previa de texto</h3><pre id="preview" style="white-space:pre-wrap"></pre>'
        '<script>const note=' + script_data + ';'
        'const e=document.getElementById("editor");e.value=note.content;'
        'let remoteLoaded=!note.needs_remote_load;'
        'let original=note.content;let remoteSnapshot=note.content;let saving=false;let localReady=false;let localLoading=true;let dirty=false;'
        'const key="obsidian-draft:"+location.pathname+":"+note.path;'
        'try{const saved=sessionStorage.getItem(key);if(saved!==null&&saved!==original){'
        'if(confirm("Se encontró un borrador. ¿Recuperarlo?"))e.value=saved;'
        'else sessionStorage.removeItem(key);}}catch(_){}'
        'const update=()=>{document.getElementById("preview").textContent=e.value;'
        'try{if(e.value===original)sessionStorage.removeItem(key);'
        'else sessionStorage.setItem(key,e.value)}catch(_){}};'
        'e.addEventListener("input",()=>{dirty=true;update()});'
        'fetch("../api/livesync-cli/local-note?path="+encodeURIComponent(note.path))'
        '.then(r=>r.ok?r.json():null).then(data=>{if(data){'
        'localReady=true;const draft=e.value;const local=data.content;'
        'const useLocal=draft!==local&&confirm("Existe una copia local distinta de la nota abierta. ¿Cargar la copia local?");'
        'if(useLocal)e.value=local;original=useLocal?local:note.content;'
        'document.getElementById("saveStatus").textContent=useLocal?"Copia local cargada, sin sincronizar":"Nota abierta conservada; copia local sin aplicar";'
        'update();}}).catch(()=>{}).finally(()=>{localLoading=false});'
        'document.getElementById("loadRemote").onclick=async()=>{'
        'if(saving||localLoading)return;'
        'const button=document.getElementById("loadRemote");button.disabled=true;'
        'const status=document.getElementById("saveStatus");'
        'status.textContent="Leyendo nota cifrada desde CouchDB (solo lectura)...";'
        'try{const r=await fetch("../api/remote/note-content?path="+encodeURIComponent(note.path),'
        '{cache:"no-store"});'
        'const data=await r.json();if(!r.ok)throw Error(data.error||"remote_read_failed");'
        'if(typeof data.content!=="string")throw Error("remote_content_missing");'
        'if(e.value!==data.content&&!confirm("¿Reemplazar el texto del editor por la copia de LiveSync? '
        'Se perderán los cambios no guardados que no hayas exportado."))'
        '{status.textContent="Lectura completada. Borrador conservado.";return;}'
        'e.value=data.content;remoteLoaded=true;remoteSnapshot=data.content;original=data.content;dirty=false;update();'
        'status.textContent="Nota remota recargada correctamente (solo lectura). '
        'Sin cambios pendientes en el editor; guardar localmente no sincroniza con CouchDB.";'
        '}catch(err){status.textContent="Lectura fallida: "+err.message}'
        'finally{button.disabled=false}};'
        'document.getElementById("previewRemote").onclick=async()=>{'
        'const status=document.getElementById("saveStatus");'
        'if(!remoteLoaded){status.textContent="Carga primero la nota remota.";return;}'
        'const button=document.getElementById("previewRemote");button.disabled=true;'
        'status.textContent="Comprobando cambios (sin escribir)...";'
        'try{const res=await fetch("../api/remote/write-preview",{method:"POST",'
        'headers:{"Content-Type":"application/json","X-Obsidian-Client-Action":"write-preview"},'
        'body:JSON.stringify({path:note.path,content:e.value,expected_content:remoteSnapshot})});'
        'const data=await res.json();if(!res.ok)throw Error(data.error||"preview_failed");'
        'if(data.revision_verified!==true||data.save_supported!==false)'
        'throw Error("revision_not_verified");'
        'status.textContent=(data.content_changed?"Cambios detectados. ":"Sin cambios pendientes. ")+'
        '"Revisión cifrada comprobada (solo lectura). Guardado remoto desactivado.";'
        '}catch(err){status.textContent="Comprobación fallida: "+err.message}'
        'finally{button.disabled=false}};'
        'document.getElementById("copyDraft").onclick=()=>navigator.clipboard.writeText(e.value);'
        'document.getElementById("exportDraft").onclick=()=>{'
        'const blob=new Blob([e.value],{type:"text/markdown;charset=utf-8"});'
        'const url=URL.createObjectURL(blob);const link=document.createElement("a");'
        'link.href=url;link.download=note.path.split("/").pop();'
        'document.body.appendChild(link);link.click();link.remove();'
        'setTimeout(()=>URL.revokeObjectURL(url),1000);};'
        'document.getElementById("saveLocal").onclick=async()=>{'
        'if(saving||localLoading)return;'
        'if(!remoteLoaded){document.getElementById("saveStatus").textContent='
        '"Primero carga la nota desde LiveSync.";return;}'
        'saving=true;document.getElementById("saveLocal").disabled=true;'
        'const submitted=e.value;'
        'const status=document.getElementById("saveStatus");status.textContent="Guardando...";'
        'try{const r=await fetch("../api/livesync-cli/local-save",{method:"POST",'
        'headers:{"Content-Type":"application/json","X-Obsidian-Client-Action":"local-save"},'
        'body:JSON.stringify({mode:localReady?"update":"create",path:note.path,'
        'expected_content:localReady?original:null,content:submitted})});'
        'const data=await r.json();if(!r.ok)throw Error(data.error||"save_failed");'
        'original=submitted;localReady=true;dirty=e.value!==submitted;'
        'status.textContent="Guardado localmente. Aún NO sincronizado con Obsidian.";'
        'try{if(e.value===original)sessionStorage.removeItem(key);else update()}catch(_){}'
        '}catch(err){status.textContent="No guardado: "+err.message}'
        'finally{saving=false;document.getElementById("saveLocal").disabled=false}};'
        'document.getElementById("discardDraft").onclick=()=>{if(confirm("¿Descartar cambios?")){'
        'e.value=original;update();}};'
        'window.addEventListener("beforeunload",event=>{if(e.value!==original){'
        'event.preventDefault();event.returnValue="";}});'
        'update();</script>'
    )
    return page(body)


@app.get("/remote/note")
def remote_note_view():
    requested=request.args.get("path","")
    content,error=read_encrypted_note(requested)
    if error:
        return page("<p><a href='../'>← Volver al listado / Back to notes</a></p><h2>No se pudo abrir la nota</h2><p>"+html.escape(error)+"</p>"),404
    # Escape all HTML in Obsidian markdown. External images/scripts are not loaded.
    index, index_error = encrypted_note_paths()
    available = index["notes"] if not index_error and index else []
    by_name = {}
    for candidate in available:
        by_name.setdefault(candidate.rsplit("/", 1)[-1].removesuffix(".md").casefold(), []).append(candidate)
    source_dir = requested.rpartition("/")[0]
    links = []
    def wiki_replace(match):
        raw = match.group(1)
        link_target = raw.split("|", 1)[0].strip()
        target, separator, heading = link_target.partition("#")
        target = target.strip()
        label = raw.split("|", 1)[1].strip() if "|" in raw else target
        normalized = target.removesuffix(".md")
        same_folder = (source_dir + "/" if source_dir else "") + normalized + ".md"
        exact = normalized + ".md"
        hits = by_name.get(normalized.rsplit("/", 1)[-1].casefold(), [])
        resolved = same_folder if same_folder in available else exact if exact in available else hits[0] if len(hits) == 1 else None
        token = "OBSIDIANWIKILINKTOKEN" + str(len(links)) + "END"
        if resolved:
            fragment = ("#" + quote(heading.strip().lower().replace(" ", "-"), safe="-")) if separator and heading.strip() else ""
            links.append('<a href="?path=' + quote(resolved, safe="") + fragment + '">' + html.escape(label) + '</a>')
        else:
            links.append('<span title="Nota no encontrada / Note not found">' + html.escape(label) + '</span>')
        return token
    prepared = re.sub(r"(?<!!)\[\[([^\]\n]{1,300})\]\]", wiki_replace, content)
    rendered = markdown.markdown(html.escape(prepared), extensions=["tables", "fenced_code", "toc"])
    for i, link in enumerate(links):
        rendered = rendered.replace("OBSIDIANWIKILINKTOKEN" + str(i) + "END", link)
    return page("<p><a href='../'>← Volver al listado / Back to notes</a></p><p><a href='../remote/edit?path="+quote(requested,safe="")+"'>Editar borrador</a></p><h2>"+html.escape(requested)+"</h2><article>"+rendered+"</article><p class='muted'>Solo lectura / Read only</p>")


@app.get("/api/remote/encrypted-notes")
def encrypted_notes():
    data, error = encrypted_note_paths()
    if error:
        return jsonify(status=error, read_only=True), 502
    term = request.args.get("q", "").casefold().strip()
    if len(term) > 200:
        return jsonify(status="query_too_long"), 400
    notes = [p for p in data["notes"] if term in p.casefold()]
    return jsonify(status="ok", read_only=True, notes=notes, count=len(notes),
                   unsupported=data["unsupported"], stats=data["stats"], content_shape=data["content_shape"], attachments=data["attachments"], truncated=data["truncated"])


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
              '<a href="api/connection">CouchDB diagnostics / Diagnóstico CouchDB (JSON)</a> · '
              '<a href="livesync/setup">Configuración LiveSync</a> · '
              '<a href="remote/library">Biblioteca CouchDB / Remote library</a> · '
              '<a href="private-drafts">Borradores locales / Private drafts</a></p>')
    if not root.is_dir():
        cfg = options()
        if cfg.get("livesync_encryption_enabled"):
            index, error = encrypted_note_paths()
            if error:
                return page("<h1>Obsidian Client</h1><p>LiveSync: " + html.escape(error) +
                            "</p>" + status)
            term = request.args.get("q", "").strip().casefold()[:200]
            visible = [p for p in index["notes"] if term in p.casefold()][:500]
            tree = {}
            for note in visible:
                node = tree
                parts = note.split("/")
                for folder in parts[:-1]:
                    node = node.setdefault(folder, {})
                node.setdefault("__notes__", []).append((parts[-1], note))
            def render_tree(node):
                items = []
                for folder in sorted((k for k in node if k != "__notes__"), key=str.casefold):
                    items.append("<li><details" + (" open" if term else "") + "><summary>📁 " + html.escape(folder) +
                                 "</summary><ul>" + render_tree(node[folder]) + "</ul></details></li>")
                for name, full in sorted(node.get("__notes__", []), key=lambda n: n[0].casefold()):
                    items.append('<li>📄 <a href="remote/note?path=' + quote(full,safe="") +
                                 '">' + html.escape(name) + "</a></li>")
                return "".join(items)
            rows = render_tree(tree)
            return page("<h1>Obsidian Client</h1><h2>LiveSync · Notas / Notes</h2>" +
                        "<p>Solo lectura · " + str(len(index["notes"])) +
                        " notas Markdown descifradas</p>" +
                        '<form><input name="q" placeholder="Buscar notas / Search notes" value="' +
                        html.escape(request.args.get("q", "")[:200], quote=True) +
                        '"></form><ul>' + rows + "</ul>" +
                        "<p class='muted'>Selecciona una nota para leerla. / "
                        "Select a note to read its contents.</p>" + status)
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
