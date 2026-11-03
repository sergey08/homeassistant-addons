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

The gateway currently supports a subset of MCP Streamable HTTP (POST requests and JSON/SSE single-response conversion). It does not support GET event streams, DELETE session termination, streaming/multiple SSE events or paginated tool lists. Test compatibility with the intended ChatGPT client before deployment.

A strong `mcp_http_token` is required. Home Assistant's add-on port mapping defaults to `null`. Never place credentials in GitHub. Do not use the raw upstream MCP endpoint from outside the container.

## Next / Próximos pasos

1. Pass end-to-end Docker HTTP rejection tests.
2. Audit each allowed tool for side effects and sensitive data disclosure.
3. Test Home Assistant Supervisor installation on amd64 and actual Moonraker connectivity, using only safe status queries.
4. Verify client protocol compatibility and secure HTTPS access.
5. Document installation and release notes in Spanish and English before publishing.

## Español

El complemento usa el servidor original `mcp-raker` aislado en el puerto local 8766 y un intermediario HTTP con autenticación y lista explícita de 5 herramientas básicas en el puerto 8765. Las órdenes no permitidas se rechazan antes de llegar al servidor original. **Aún no debe instalarse:** faltan la auditoría funcional de las herramientas autorizadas y las pruebas reales con Home Assistant y la Snapmaker U1.


### Default privacy profile (DEV)

Only five tools are enabled by default: MCP version, server info, printer info, temperature store and job queue status. Print history, device power, sensors and Spoolman tools remain disabled pending a separate privacy review. This is a conservative development default, not a finished user-selectable permissions system.

**Español:** El perfil inicial permite cinco consultas básicas. Historial de impresiones, dispositivos eléctricos, sensores y Spoolman permanecen deshabilitados hasta revisar los datos expuestos. No instalar todavía.

### Klipper object access / Acceso a objetos Klipper

`enable_objects` defaults to `false`. Enabling it adds `moonraker_objects_list` and `moonraker_objects_query`, which can reveal internal object names and fields. Enable only after reviewing privacy implications. / `enable_objects` está desactivado por defecto y debe habilitarse expresamente.
