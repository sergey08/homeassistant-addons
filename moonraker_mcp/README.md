# Moonraker MCP for Home Assistant — DEV

Experimental Home Assistant add-on wrapping [lexfrei/mcp-raker](https://github.com/lexfrei/mcp-raker) (upstream BSD-3-Clause).

## Current architecture / Arquitectura actual

- Upstream `mcp-raker` runs on **127.0.0.1:8766 inside the container**, never on the published interface.
- A Python HTTP gateway listens on port **8765** and checks a bearer token.
- `tools/list` is filtered using `read_only_allowlist.json` (4 minimal status tools by default).
- `tools/call` is independently checked against the same explicit allowlist; unknown tools and unsupported MCP methods fail closed.
- The upstream image is pinned to `sha256:cdfbb9b4ead2b3f8a253eb55c1996a69cfdbc17088cc111b7d265d8b71f7090e`.
- The Alpine runtime contains Python, jq, CA certificates and the upstream Go executable. The launcher starts as root to read Supervisor-protected options, then starts the long-lived gateway and upstream services as UID 65534.

## Security / Seguridad

**DEV ONLY — already installed and locally tested on Home Assistant; do not expose remotely or publish a stable release yet.**

The HTTP gateway is a prototype. Docker CI validates MCP initialization, tool listing, authentication and denied operations without connecting to a real printer. **A successful test does not by itself certify that all four default read-only tools are safe against every printer firmware version.** Review each tool's implementation and parameters before deployment.

The gateway supports a restricted subset of MCP Streamable HTTP: authenticated POST requests, JSON or single-event SSE upstream responses, and filtered `tools/list` pagination using cursors. It does **not** support GET event streams, DELETE session termination, streaming/multiple SSE events or full session lifecycle management. Pagination support is not equivalent to full Streamable HTTP compliance. Test compatibility with the intended ChatGPT client before deployment.

A strong `mcp_http_token` is required. Home Assistant's add-on port mapping defaults to `null`. Never place credentials in GitHub. Do not use the raw upstream MCP endpoint from outside the container.

## ChatGPT connection requirements / Requisitos de conexión con ChatGPT

**No direct ChatGPT connection has been tested.** A green CI run validates the local gateway and pinned upstream in Docker, not external MCP registration or access through the Internet. The Home Assistant add-on is only a host for this service; it does not route queries through Home Assistant entities.

Before any remote connection, confirm the intended ChatGPT client accepts this limited MCP HTTP implementation, design an HTTPS endpoint with valid TLS, keep bearer authentication, and restrict network exposure. Do not forward the raw upstream port 8766 or publish port 8765 by default. Session lifecycle, long-running SSE streams, and other unsupported transport features may require implementation changes. Local DEV installation and read-only printer connectivity were already approved and validated. Remote exposure and any printer-control operation require separate authorization.

**Español:** No se ha probado la conexión directa desde ChatGPT. El complemento DEV2 ya se instaló y se probó localmente con consultas de solo lectura a la Snapmaker U1. La conexión externa requiere verificar la identidad independiente del túnel, autenticación y restricciones de acceso; no está autorizada aún.

## Comprobación de compatibilidad sin impresora / Printer-free compatibility check

The DEV GitHub Actions workflow starts the real add-on container with a placeholder Moonraker URL and a local-only port mapping (`127.0.0.1:18765`). It sends a JSON-RPC `initialize` using MCP `2025-06-18`, validates the server advertises **only** `{"tools":{}}`, and requests `tools/list`. It compares the returned tools with the explicit default allowlist and checks that printer-control and privacy-disabled tool calls are rejected. The check exercises the pinned upstream binary but does **not** use a real printer or verify connection from ChatGPT.

**Español:** GitHub Actions inicia el contenedor real con una URL Moonraker de prueba y un puerto accesible únicamente desde el propio runner. Comprueba la negociación MCP, las capacidades anunciadas y las herramientas disponibles. Ninguna de estas comprobaciones requiere acceder a la Snapmaker U1. La compatibilidad real desde ChatGPT sigue pendiente, igual que cualquier instalación en Home Assistant.

## Optional OpenAI tunnel inside HA / Túnel opcional dentro de Home Assistant

The optional tunnel integration follows the **existing Obsidian Suite add-on** pattern in this repository: the `tunnel-client` process is launched **inside the same HA add-on container** as the MCP gateway, not on any DCL business host. All internet traffic is initiated outbound by the tunnel client; the gateway stays on the internal container network. The upstream `mcp-raker` listener remains bound to `127.0.0.1:8766`.

- Defaults: `enable_tunnel: false`, `tunnel_id: ""`; the existing gateway bearer token remains required.
- When enabled, `tunnel_runtime.py` starts a loopback-only (`127.0.0.1:8767`) bridge that forwards requests exclusively to `127.0.0.1:8765/mcp` and inserts the configured bearer header. This token is never passed on the tunnel command line.
- The tunnel process uses exactly the working Obsidian-style CLI arguments (`--control-plane.tunnel-id`, `--control-plane.api-key file:`, `--mcp.server-url channel=main,url=http://127.0.0.1:8767/mcp`). It needs an **independent** tunnel identity, the verified official `tunnel-client` executable at `/data/tunnel/bin/tunnel-client`, and its private `/data/tunnel/api-key` (file mode 0600, readable by the container UID 65534). These files are provisioned locally by the operator, **not included in the repository**.
- The loopback bridge rejects browser `Origin` headers and unexpected HTTP `Host` values; it does not provide a public unauthenticated port. Keep `8765/tcp` unmapped in the add-on network settings. Do not route external traffic directly to `8767` or `8766`.
- **DEV ONLY**. Check the tunnel-client binary's compatibility with the Alpine runtime and complete an isolated tunnel end-to-end test before enabling it in Home Assistant. Never reuse Obsidian's tunnel ID or key.

**Español:** siguiendo Obsidian, el cliente de túnel y el gateway se ejecutan dentro del **mismo complemento de Home Assistant**. La opción de túnel queda desactivada por defecto. El proxy de `127.0.0.1:8767` añade el token al gateway filtrado de `127.0.0.1:8765/mcp`; el túnel abre solo una conexión saliente. La identidad y la clave deben ser nuevas y privadas. El complemento DEV2 ya está instalado y validado localmente con la Snapmaker U1, pero el túnel aún no está probado con ChatGPT.

## Official SDK interoperability / Interoperabilidad con SDK oficial

**Validated in isolated Docker CI (2026-11-04):** the official Python MCP SDK `mcp==1.30.0`, using Streamable HTTP, can establish an authenticated connection to the actual pinned upstream behind the gateway, negotiate an older supported protocol revision, receive the tools-only capabilities, discover the four default tools, and successfully invoke `moonraker_mcp_version`. A second SDK session attempts `moonraker_gcode_script` and verifies rejection with HTTP 403. These checks passed in both GitHub Actions workflows at commit `6e2e06c`.

**Español:** el SDK oficial MCP para Python conecta con el contenedor real, negocia el protocolo, descubre las cuatro herramientas predeterminadas y ejecuta la consulta de versión. Una llamada de ejecución de G-code se bloquea con 403. Todo ello se comprueba sin conectar ninguna impresora.

**What remains unverified / Pendiente:** ChatGPT's actual remote registration, credential/tunnel configuration, HTTPS or secure tunnel access, real Home Assistant add-on installation, live Moonraker responses and private-data redaction. The gateway remains a limited Streamable HTTP implementation and is **not** certified production-ready. Never put a token or private endpoint in this repository; secure exposure and printer access require separate authorization.

## Live validation / Validación real (2026-11-04)

On Snapmaker U1 with Moonraker 2.0.0 and firmware `2.0.0-paxx12-23`, authenticated MCP initialization, initialized notification, `tools/list` (four default tools), and read-only `moonraker_printer_info` were verified successfully against the real printer. This does **not** verify operation while the printer is powered off, recovery after power-on, or remote ChatGPT connectivity. A previous Supervisor rebuild reused an older `0.1.0-dev1` image tag; the package version has therefore been incremented to `0.1.0-dev2`. CI checks image launcher identity. Never expose ports by default.

**Español:** validado el funcionamiento real de las cuatro herramientas visibles y la llamada de consulta `moonraker_printer_info` en una Snapmaker U1 encendida. Pendiente comprobar desconexión y reconexión, reconstrucción por Supervisor con la nueva versión y conexión externa segura. Rotar las credenciales usadas en pruebas antes de cualquier exposición.

## Next / Próximos pasos

1. **Completed in isolated Docker CI:** authenticated MCP initialization, tool listing, forbidden calls, four-tool default, and explicit history/objects profiles. No printer connection was used.
2. **Source reviewed:** all sixteen permitted upstream handlers are GET-only or local; OCI revision is checked in CI. This is not a binary provenance attestation.
3. **Pending:** inspect representative responses for sensitive information, especially server metadata, queued filenames, and optional object queries.
4. **Completed locally on 2026-11-05:** Home Assistant Supervisor installation on amd64 and real Moonraker connectivity through safe status queries.
5. **Pending:** intended ChatGPT client compatibility, secure HTTPS access, and release documentation before publishing.

## Español

El complemento usa el servidor original `mcp-raker` aislado en el puerto local 8766 y un intermediario HTTP con autenticación y lista explícita de 4 herramientas básicas en el puerto 8765. Las órdenes no permitidas se rechazan antes de llegar al servidor original. **DEV2 ya está instalado y probado localmente:** sigue pendiente la revisión de privacidad, la activación segura del túnel y la validación remota con ChatGPT.


### Default privacy profile (DEV)

Only four tools are enabled by default: MCP version, server info, printer info and temperature store. Job queue status requires `enable_jobqueue: true` because queued filenames may be sensitive. Print history, device power, sensors and Spoolman tools remain disabled pending a separate privacy review. This is a conservative development default, not a finished user-selectable permissions system.

**Español:** El perfil inicial permite cuatro consultas básicas. La cola de impresión requiere `enable_jobqueue: true` porque puede revelar nombres de archivos. Historial de impresiones, dispositivos eléctricos, sensores y Spoolman permanecen deshabilitados hasta revisar los datos expuestos. No publicar ni conectar remotamente todavía.

### Klipper object access / Acceso a objetos Klipper

`enable_objects` defaults to `false`. Enabling it adds `moonraker_objects_list` and `moonraker_objects_query`, which can reveal internal object names and fields. Enable only after reviewing privacy implications. / `enable_objects` está desactivado por defecto y debe habilitarse expresamente.


### File access / Acceso a ficheros (DEV)

The optional `enable_files: true` profile adds three **read-only** MCP tools:

| Tool | Moonraker endpoint | Restrictions |
| --- | --- | --- |
| `moonraker_files_list` | `GET /server/files/list?root=gcodes` | G-code root only |
| `moonraker_files_metadata` | `GET /server/files/metadata?filename=...` | Relative filename, no traversal |
| `moonraker_files_preview` | `GET /server/files/gcodes/<filename>` | Only `.gcode`/`.gco`; maximum 16 KiB; no redirects |

**Disabled by default.** The profile does not expose arbitrary Moonraker roots, full file downloads, uploads, deletion, G-code execution, or configuration-file reading. The gateway rejects unknown tools on both discovery and invocation. The HTTP helper rejects embedded credentials, URL paths, redirects and excessive responses. G-code contents can still contain private information (file names, paths, slicer metadata, comments); review before granting remote access.

**Español:** `enable_files` habilita listado, metadatos y vista previa de G-code (máximo 16 KiB). No permite leer `printer.cfg`, descargar ficheros completos ni modificarlos. Los archivos de configuración requieren un perfil independiente y una estrategia de ocultación de secretos antes de incorporarse.

#### Instalación experimental: criterios previos

1. GitHub Actions must pass unit tests and mock-Moonraker Docker tests on the exact candidate commit.
2. Review actual add-on Supervisor compatibility on amd64; do not install on the production HA instance until explicitly authorized.
3. Test MCP compatibility with the intended ChatGPT client; the current gateway only supports limited Streamable HTTP.
4. Confirm Moonraker endpoint, authentication and permissions **without committing IPs, keys or tokens to GitHub**.
5. Keep port 8765 unmapped until a secure access design (HTTPS, authentication, access restrictions) has been validated.
6. Review representative responses for private data. No printing commands, file changes or real-printer tests without user approval.

## GitHub-first DEV2 verification / Verificación de DEV2 en GitHub

- Source branch / Rama: [`dev/moonraker-mcp-dev2`](https://github.com/sergey08/homeassistant-addons/tree/dev/moonraker-mcp-dev2).
- Draft PR / PR borrador: [#89](https://github.com/sergey08/homeassistant-addons/pull/89).
- Isolated CI / Pruebas aisladas: [Moonraker MCP DEV2 CI](https://github.com/sergey08/homeassistant-addons/actions/workflows/moonraker-mcp-dev2.yml) (successful run #8 at commit `93c48a7`).
- The CI pipeline validates Python tests, shell and YAML syntax, Docker build, unauthenticated HTTP rejection and a non-root gateway startup. This **does not** establish tunnel interoperability or printer safety.
- Local Home Assistant results: 111 Python tests passed and read-only MCP calls to version, printer info and server info succeeded. No printer-control commands were tested.

**Tunnel key access / Acceso a la clave del túnel:** The add-on starts the tunnel bridge and client as UID 65534, so an API-key file with permissions `0600` **must be owned by UID 65534** (or supplied securely through a separately audited privilege handoff). A root-owned `0600` key is intentionally unreadable to this process. Do not weaken permissions to `0644`, paste keys into logs or commit credentials to GitHub. The path `/data/tunnel/api-key` must remain private; `/data/tunnel/bin/tunnel-client` must be a separately verified official executable. The Obsidian tunnel ID and key must never be reused.

**Español:** CI verifica el arranque del contenedor y su autenticación local, pero no la conexión externa con ChatGPT. El cliente de túnel se ejecuta con UID 65534; un archivo de clave `0600` debe pertenecer a ese UID. Nunca hagas pública la clave ni reutilices la identidad de Obsidian. Rotar las credenciales de pruebas anteriores antes de habilitar el acceso externo.

### Runtime failure supervision / Supervisión de fallos del túnel

**English:** When `enable_tunnel: true`, the launcher supervises the upstream MCP process, HTTP gateway, keepalive and optional tunnel process. If any required process exits—even if the tunnel client exits with status zero—the add-on stops with an error instead of silently appearing connected. Container-local CI simulates an unexpectedly terminating tunnel client and checks the fail-closed behavior without contacting Moonraker or OpenAI. The check does **not** demonstrate that the official tunnel client successfully registers with OpenAI.

**Español:** Cuando `enable_tunnel: true`, el iniciador vigila el MCP original, el gateway HTTP, el proceso de mantenimiento y el túnel. Si cualquiera termina, aunque el túnel devuelva código cero, el complemento se detiene con error. La CI prueba este comportamiento con un cliente ficticio, sin acceder a la impresora ni a OpenAI. Esta prueba **no confirma** todavía que el túnel oficial pueda registrarse desde ChatGPT.

## Offline tunnel-client provisioning (DEV, operator action only)

**English:** The add-on image includes `/opt/moonraker-mcp/tunnel_provision.py`, a separate, offline provisioning utility adapted from the Obsidian Suite installer. It **does not download** a binary, register an OpenAI tunnel, or enable remote access automatically.

1. Obtain the official `tunnel-client-…linux-amd64.zip` release package and its matching `SHA256SUMS.txt` from a separately verified official distribution channel. Confirm the publisher/provenance independently; a checksum published beside an untrusted binary is not sufficient proof of authenticity. **Do not use an unverified archive.**
2. With the add-on container running a newer DEV build that includes this script, a trusted operator can run `python3 /opt/moonraker-mcp/tunnel_provision.py --base /data install --archive /path/to/verified.zip --manifest /path/to/SHA256SUMS.txt` **inside that container**. The archive and manifest must first be made available to the container. This procedure requires root only for staging private files; it does not change the default disabled tunnel state.
3. Provision a **new, independent** OpenAI tunnel API key, never Obsidian's key, using `python3 /opt/moonraker-mcp/tunnel_provision.py --base /data key` in an **interactive container terminal**. The prompt hides the key and confirms it; do not pass a secret as a CLI argument, write it into chat, capture terminal output, or put it in a repository.
4. The provisioning utility creates `/data/tunnel/bin/tunnel-client` as executable mode `0700` and `/data/tunnel/api-key` as private mode `0600`, both owned by UID 65534. It refuses to overwrite existing keys/binaries. Key storage is local to the Moonraker add-on, not shared with Obsidian.
5. Only after verifying the specific official binary is compatible with the Alpine image and obtaining an independent tunnel ID should an operator consider `enable_tunnel: true`. Rotate previously exposed Moonraker and MCP tokens before any external test. Keep mapped port 8765 disabled. The remote ChatGPT end-to-end handshake is **not yet verified**.

**Español:** La imagen incluye `tunnel_provision.py`, un instalador local que verifica el SHA-256 de un ZIP oficial y exige verificar **por separado su procedencia**. No descarga nada, no registra el túnel ni abre el acceso remoto. El operador aporta el ZIP y el manifiesto oficiales y ejecuta el comando `install` dentro del contenedor. Con el comando interactivo `key` introduce dos veces una **clave nueva y exclusiva de Moonraker**, sin mostrarla por pantalla ni incluirla en argumentos. El binario queda con permisos `0700` y la clave con `0600`, bajo UID 65534. La activación externa y la prueba real de ChatGPT siguen pendientes y requieren rotar las credenciales anteriores. No reutilizar la identidad de Obsidian ni abrir el puerto 8765.

### Official source and tunnel registration / Fuente oficial y alta del túnel

- Official client releases / Versiones oficiales: https://github.com/openai/tunnel-client/releases
- Official Secure MCP Tunnel documentation: https://developers.openai.com/api/docs/guides/secure-mcp-tunnels
- Official account setup and key scopes: https://github.com/openai/tunnel-client/blob/master/docs/onboarding.md
- The runtime API key must have **Tunnels Read + Use** for its **own** Moonraker tunnel. An admin key is not required for the long-running client. Registration with ChatGPT is a separate, user-authorized step in ChatGPT Plugins → Add custom MCP server → Tunnel.
- **Distribution limit:** Secure MCP Tunnel is for private MCP connections, not public plugin submission; a public plugin would require a stable public HTTPS MCP endpoint. This repository distributes a Home Assistant add-on, not an automatically registered public ChatGPT plugin.

**Español:** el cliente oficial se distribuye en `openai/tunnel-client` con archivos de verificación. La clave de ejecución necesita únicamente los permisos **Tunnels Read + Use** sobre el túnel privado de Moonraker, y nunca debe ser una clave de administrador. La incorporación posterior a ChatGPT se realiza desde Plugins → Añadir servidor MCP personalizado → Túnel. No confundas la publicación de este complemento Home Assistant con la publicación pública de un plugin de ChatGPT.

### Pinned official client compatibility check / Comprobación del cliente oficial

**English:** The DEV CI additionally downloads the exact official `tunnel-client-v0.0.19-linux-amd64.zip` and its `SHA256SUMS.txt` from [OpenAI's v0.0.19 release](https://github.com/openai/tunnel-client/releases/tag/v0.0.19). The ZIP's expected SHA-256 is `9ee9448592345a9dd1517fb79791ab54d24f051142eb92bcbe8cd355effc9142`. CI verifies the digest, runs the offline provisioning utility inside the actual Alpine add-on container and invokes `tunnel-client --version` as UID 65534, with `--network none`. This verifies executable compatibility only; it does not register the tunnel or contact ChatGPT.

**Español:** La CI descarga el ZIP oficial `v0.0.19` y su manifiesto, comprueba el hash SHA-256 anterior, instala el binario en el contenedor Alpine de pruebas y ejecuta `--version` con UID 65534, sin conexión de red. Comprueba la **compatibilidad del ejecutable**, no el funcionamiento del túnel contra el servicio OpenAI ni su autorización desde ChatGPT.
