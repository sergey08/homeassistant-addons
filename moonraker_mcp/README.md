# Moonraker MCP for Home Assistant — DEV

Experimental Home Assistant add-on wrapping [lexfrei/mcp-raker](https://github.com/lexfrei/mcp-raker) (upstream BSD-3-Clause).

## Current architecture / Arquitectura actual

- Upstream `mcp-raker` runs on **127.0.0.1:8766 inside the container**, never on the published interface.
- A Python HTTP gateway listens on port **8765** and checks a bearer token.
- `tools/list` is filtered using `read_only_allowlist.json` (4 minimal status tools by default).
- `tools/call` is independently checked against the same explicit allowlist; unknown tools and unsupported MCP methods fail closed.
- The upstream image is pinned to `sha256:cdfbb9b4ead2b3f8a253eb55c1996a69cfdbc17088cc111b7d265d8b71f7090e`.
- The Alpine runtime contains Python, jq, CA certificates and the upstream Go executable. It runs as UID 65534.

## Security / Seguridad

**DEV ONLY — DO NOT INSTALL OR EXPOSE TO THE INTERNET YET.**

The HTTP gateway is a prototype. Docker CI validates MCP initialization, tool listing, authentication and denied operations without connecting to a real printer. **A successful test does not by itself certify that all four default read-only tools are safe against every printer firmware version.** Review each tool's implementation and parameters before deployment.

The gateway supports a restricted subset of MCP Streamable HTTP: authenticated POST requests, JSON or single-event SSE upstream responses, and filtered `tools/list` pagination using cursors. It does **not** support GET event streams, DELETE session termination, streaming/multiple SSE events or full session lifecycle management. Pagination support is not equivalent to full Streamable HTTP compliance. Test compatibility with the intended ChatGPT client before deployment.

A strong `mcp_http_token` is required. Home Assistant's add-on port mapping defaults to `null`. Never place credentials in GitHub. Do not use the raw upstream MCP endpoint from outside the container.

## ChatGPT connection requirements / Requisitos de conexión con ChatGPT

**No direct ChatGPT connection has been tested.** A green CI run validates the local gateway and pinned upstream in Docker, not external MCP registration or access through the Internet. The Home Assistant add-on is only a host for this service; it does not route queries through Home Assistant entities.

Before any remote connection, confirm the intended ChatGPT client accepts this limited MCP HTTP implementation, design an HTTPS endpoint with valid TLS, keep bearer authentication, and restrict network exposure. Do not forward the raw upstream port 8766 or publish port 8765 by default. Session lifecycle, long-running SSE streams, and other unsupported transport features may require implementation changes. Obtain explicit approval separately for installation, printer connectivity, and remote exposure.

**Español:** No se ha probado la conexión directa desde ChatGPT. CI valida el gateway y el servidor original en Docker, no el registro remoto del MCP. Antes de conectarlo hay que comprobar compatibilidad real, HTTPS, autenticación y restricciones de acceso. Instalar, conectar la impresora y abrir acceso remoto requieren autorizaciones independientes.

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

**Español:** siguiendo Obsidian, el cliente de túnel y el gateway se ejecutan dentro del **mismo complemento de Home Assistant**. La opción de túnel queda desactivada por defecto. El proxy de `127.0.0.1:8767` añade el token al gateway filtrado de `127.0.0.1:8765/mcp`; el túnel abre solo una conexión saliente. La identidad y la clave deben ser nuevas y privadas. Esta implementación aún no está instalada ni probada con ChatGPT o la Snapmaker U1.

## Official SDK interoperability / Interoperabilidad con SDK oficial

**Validated in isolated Docker CI (2026-11-04):** the official Python MCP SDK `mcp==1.30.0`, using Streamable HTTP, can establish an authenticated connection to the actual pinned upstream behind the gateway, negotiate an older supported protocol revision, receive the tools-only capabilities, discover the four default tools, and successfully invoke `moonraker_mcp_version`. A second SDK session attempts `moonraker_gcode_script` and verifies rejection with HTTP 403. These checks passed in both GitHub Actions workflows at commit `6e2e06c`.

**Español:** el SDK oficial MCP para Python conecta con el contenedor real, negocia el protocolo, descubre las cuatro herramientas predeterminadas y ejecuta la consulta de versión. Una llamada de ejecución de G-code se bloquea con 403. Todo ello se comprueba sin conectar ninguna impresora.

**What remains unverified / Pendiente:** ChatGPT's actual remote registration, credential/tunnel configuration, HTTPS or secure tunnel access, real Home Assistant add-on installation, live Moonraker responses and private-data redaction. The gateway remains a limited Streamable HTTP implementation and is **not** certified production-ready. Never put a token or private endpoint in this repository; secure exposure and printer access require separate authorization.

## Next / Próximos pasos

1. **Completed in isolated Docker CI:** authenticated MCP initialization, tool listing, forbidden calls, four-tool default, and explicit history/objects profiles. No printer connection was used.
2. **Source reviewed:** all sixteen permitted upstream handlers are GET-only or local; OCI revision is checked in CI. This is not a binary provenance attestation.
3. **Pending:** inspect representative responses for sensitive information, especially server metadata, queued filenames, and optional object queries.
4. **Pending user approval:** Home Assistant Supervisor installation on amd64 and actual Moonraker connectivity using only safe status queries.
5. **Pending:** intended ChatGPT client compatibility, secure HTTPS access, and release documentation before publishing.

## Español

El complemento usa el servidor original `mcp-raker` aislado en el puerto local 8766 y un intermediario HTTP con autenticación y lista explícita de 4 herramientas básicas en el puerto 8765. Las órdenes no permitidas se rechazan antes de llegar al servidor original. **Aún no debe instalarse:** faltan la auditoría funcional de las herramientas autorizadas y las pruebas reales con Home Assistant y la Snapmaker U1.


### Default privacy profile (DEV)

Only four tools are enabled by default: MCP version, server info, printer info and temperature store. Job queue status requires `enable_jobqueue: true` because queued filenames may be sensitive. Print history, device power, sensors and Spoolman tools remain disabled pending a separate privacy review. This is a conservative development default, not a finished user-selectable permissions system.

**Español:** El perfil inicial permite cuatro consultas básicas. La cola de impresión requiere `enable_jobqueue: true` porque puede revelar nombres de archivos. Historial de impresiones, dispositivos eléctricos, sensores y Spoolman permanecen deshabilitados hasta revisar los datos expuestos. No instalar todavía.

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
