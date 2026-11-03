# Moonraker MCP for Home Assistant (DEV)

Experimental Home Assistant OS add-on wrapping [lexfrei/mcp-raker](https://github.com/lexfrei/mcp-raker), BSD-3-Clause.

## Packaging
The upstream `Containerfile` uses a **scratch** final stage, with the binary at `/mcp-raker` and **no shell or jq**. This add-on therefore copies that binary into an Alpine runtime with shell, jq and CA certificates. The runtime script reads Home Assistant options from `/data/options.json`.

**Not yet tested or ready to install.** Upstream image is pinned to digest `sha256:cdfbb9b4ead2b3f8a253eb55c1996a69cfdbc17088cc111b7d265d8b71f7090e` (identified in successful CI run #8). Revalidate the pinned image in CI after this change. The Home Assistant build and runtime still require testing.

## Security
- Configure a strong `mcp_http_token` before starting; the add-on refuses to start without it.
- `MOONRAKER_ENABLE_ADMIN=false` blocks upstream's *admin* tool group only.
- **Core tools still include start/cancel prints, G-code execution, firmware restart and emergency stop. This is NOT a read-only server.**
- Do not publish port 8765 to the internet; it is unbound on the host by default (`null` port mapping).
- For ChatGPT remote access, design a separate HTTPS authenticated gateway with explicit tool allowlisting, or fork upstream to implement server-side read-only controls. No such gateway exists yet.
- Do not put API keys or MCP tokens in GitHub.

## Roadmap / Próximos pasos
1. Pin upstream release/digest and verify license notices.
2. Build the Docker image in CI and check startup with a mock Moonraker endpoint.
3. Confirm Supervisor compatibility on amd64.
4. Implement genuine server-side read-only mode before exposing to AI.
5. Validate remote ChatGPT MCP compatibility and secure HTTPS access.
6. Add ES/EN installation docs and release only after testing.

## Español
Complemento experimental que reutiliza el MCP original de Moonraker. La imagen original no contiene shell, por lo que empaquetamos su ejecutable en Alpine. **No instalar ni publicar todavía:** falta compilar y verificar el arranque y la seguridad. Desactivar las herramientas administrativas no impide ejecutar G-code u otras acciones de impresión.
