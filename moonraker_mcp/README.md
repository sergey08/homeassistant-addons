# Moonraker MCP for Home Assistant — DEV

Experimental Home Assistant add-on wrapping [lexfrei/mcp-raker](https://github.com/lexfrei/mcp-raker) (upstream BSD-3-Clause).

## Current architecture / Arquitectura actual

- Upstream `mcp-raker` runs on **127.0.0.1:8766 inside the container**, never on the published interface.
- A Python HTTP gateway listens on port **8765** and checks a bearer token.
- `tools/list` is filtered using `read_only_allowlist.json` (5 minimal status tools by default).
- `tools/call` is independently checked against the same explicit allowlist; unknown tools and unsupported MCP methods fail closed.
- The upstream image is pinned to `sha256:cdfbb9b4ead2b3f8a253eb55c1996a69cfdbc17088cc111b7d265d8b71f7090e`.
- The Alpine runtime contains Python, jq, CA certificates and the upstream Go executable. It runs as UID 65534.

## Security / Seguridad

**DEV ONLY — DO NOT INSTALL OR EXPOSE TO THE INTERNET YET.**

The HTTP gateway is a prototype. Docker CI validates MCP initialization, tool listing, authentication and denied operations without connecting to a real printer. **A successful test does not certify that all 5 default allowed operations are side-effect free.** Review each tool's implementation and parameters before deployment.

The gateway supports a restricted subset of MCP Streamable HTTP: authenticated POST requests, JSON or single-event SSE upstream responses, and filtered `tools/list` pagination using cursors. It does **not** support GET event streams, DELETE session termination, streaming/multiple SSE events or full session lifecycle management. Pagination support is not equivalent to full Streamable HTTP compliance. Test compatibility with the intended ChatGPT client before deployment. Test compatibility with the intended ChatGPT client before deployment.

A strong `mcp_http_token` is required. Home Assistant's add-on port mapping defaults to `null`. Never place credentials in GitHub. Do not use the raw upstream MCP endpoint from outside the container.

## Next / Próximos pasos

1. **Completed in isolated Docker CI:** authenticated MCP initialization, tool listing, forbidden calls, five-tool default, and explicit history/objects profiles. No printer connection was used.
2. **Source reviewed:** all sixteen permitted upstream handlers are GET-only or local; OCI revision is checked in CI. This is not a binary provenance attestation.
3. **Pending:** inspect representative responses for sensitive information, especially server metadata, queued filenames, and optional object queries.
4. **Pending user approval:** Home Assistant Supervisor installation on amd64 and actual Moonraker connectivity using only safe status queries.
5. **Pending:** intended ChatGPT client compatibility, secure HTTPS access, and release documentation before publishing.

## Español

El complemento usa el servidor original `mcp-raker` aislado en el puerto local 8766 y un intermediario HTTP con autenticación y lista explícita de 5 herramientas básicas en el puerto 8765. Las órdenes no permitidas se rechazan antes de llegar al servidor original. **Aún no debe instalarse:** faltan la auditoría funcional de las herramientas autorizadas y las pruebas reales con Home Assistant y la Snapmaker U1.


### Default privacy profile (DEV)

Only five tools are enabled by default: MCP version, server info, printer info, temperature store and job queue status. Print history, device power, sensors and Spoolman tools remain disabled pending a separate privacy review. This is a conservative development default, not a finished user-selectable permissions system.

**Español:** El perfil inicial permite cinco consultas básicas. Historial de impresiones, dispositivos eléctricos, sensores y Spoolman permanecen deshabilitados hasta revisar los datos expuestos. No instalar todavía.

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
