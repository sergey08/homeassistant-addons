# Moonraker MCP v0.1.0 — Quick start / Inicio rápido

**Available now in the stable Home Assistant app catalog.** This app is source-built locally by Supervisor. It is separate from the DEV installation.

## English

1. **Requirements:** Home Assistant OS/Supervised on AMD64 or ARM64 and a reachable Moonraker API (usually on port 7125). An internet connection is needed while the app builds. A unique `mcp_http_token` is always required.
2. **Moonraker key:** Retrieve your current key from `GET http://PRINTER_IP:7125/access/api_key` on a trusted/authorized client, if your Moonraker deployment requires it. **Do not POST** to that endpoint; it regenerates the key. If Moonraker trusts Home Assistant without a key, leave `moonraker_api_key` blank.
3. **Install:** Home Assistant → Settings → Apps → App Store → ⋮ → Repositories → add `https://github.com/sergey08/homeassistant-addons`. Install **Moonraker MCP** (not DEV).
4. **Configure:** Set `moonraker_url` (for example `http://printer.local:7125`), optional `moonraker_api_key`, and unique mandatory `mcp_http_token`; start with `enable_tunnel: false`.
5. **Optional ChatGPT tunnel:** Create/select a tunnel in [OpenAI Platform](https://platform.openai.com/settings/organization/tunnels) and a restricted runtime key in [API Keys](https://platform.openai.com/settings/organization/api-keys). Enter `tunnel_id`, `openai_tunnel_api_key`, enable the tunnel, save/restart and add a custom MCP server with **Tunnel** connection in ChatGPT. Creating a tunnel requires **Tunnels Read + Manage**; using one requires **Tunnels Read + Use**.
6. **Safety:** Do not expose port 8765 publicly; all seven extra `enable_*` options are off initially. Don't share a tunnel ID between the DEV and stable apps running together.

**[Full guide (all 13 options, steps and troubleshooting)](./README.md)**

## Español

1. **Requisitos:** Home Assistant OS/Supervised AMD64 o ARM64 y API Moonraker accesible (normalmente puerto 7125). Internet durante la compilación. El `mcp_http_token` exclusivo siempre es obligatorio.
2. **Clave Moonraker:** desde un equipo autorizado, consulta la clave actual con `GET http://IP_IMPRESORA:7125/access/api_key`, si se requiere. **No utilices POST**: regeneraría la clave. Si Moonraker acepta Home Assistant sin clave, deja `moonraker_api_key` vacío.
3. **Instalar:** Home Assistant → Ajustes → Aplicaciones → Tienda de aplicaciones → ⋮ → Repositorios → añade `https://github.com/sergey08/homeassistant-addons`. Instala **Moonraker MCP** (sin DEV).
4. **Configurar:** introduce `moonraker_url` (por ejemplo `http://printer.local:7125`), la clave Moonraker cuando proceda y el `mcp_http_token` obligatorio. Deja `enable_tunnel: false` al principio.
5. **Túnel ChatGPT opcional:** crea/selecciona un túnel desde [OpenAI Platform](https://platform.openai.com/settings/organization/tunnels) y una clave restringida desde [Claves API](https://platform.openai.com/settings/organization/api-keys). Introduce `tunnel_id` y `openai_tunnel_api_key`, activa el túnel, guarda/reinicia y registra un MCP por **Túnel** en ChatGPT. Crear exige **Tunnels Read + Manage**; utilizar, **Tunnels Read + Use**.
6. **Seguridad:** no abras el puerto 8765 a Internet; las siete opciones extra `enable_*` empiezan desactivadas. No compartas un mismo túnel entre DEV y estable ejecutándose a la vez.

**[Manual completo (las 13 opciones, instrucciones y problemas frecuentes)](./README.md)**

Real encrypted backup restoration and tunnel-key revocation are not fully verified; do not assume DEV-to-stable automatic migration. / La restauración cifrada real y la revocación de claves no están completamente verificadas. No se garantiza migración automática desde DEV.
