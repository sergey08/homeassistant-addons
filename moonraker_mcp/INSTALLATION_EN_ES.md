# Moonraker MCP v0.1.0 — Installation and configuration / Instalación y configuración

**The complete, maintained setup guide is the [main README](./README.md). It is written first in English, then in Spanish.** It covers all 13 Home Assistant options, the Moonraker API key, the OpenAI Secure MCP Tunnel, permissions, security, tests and troubleshooting.

## English — Installation overview

1. **Requirements:** Home Assistant OS/Supervised on AMD64/ARM64, local access to a Moonraker API (usually port 7125), a unique MCP HTTP token and internet access for the local image build. ChatGPT and a tunnel are optional.
2. **Moonraker URL:** Find your printer's LAN address and test its Moonraker HTTP API, e.g. `http://printer.local:7125/server/info`. Enter the base URL without the path in `moonraker_url`.
3. **Moonraker key:** From an authorized client, `GET http://PRINTER_IP:7125/access/api_key` retrieves the *existing* key when permitted. Do not `POST` to this endpoint merely to retrieve it: that regenerates the key. Enter the result in `moonraker_api_key` if required.
4. **Install:** Add `https://github.com/sergey08/homeassistant-addons` in Home Assistant **Settings → Apps → App Store → ⋮ → Repositories**. Install **Moonraker MCP** (not DEV). Complete `moonraker_url`, optional `moonraker_api_key`, and mandatory `mcp_http_token`; leave `enable_tunnel` off initially.
5. **Optional tunnel:** From [OpenAI Platform Tunnels](https://platform.openai.com/settings/organization/tunnels), create/select your tunnel (creation requires **Tunnels Read + Manage**). From [API Keys](https://platform.openai.com/settings/organization/api-keys), create a **Restricted** runtime key with **Tunnels Read + Use**. In Home Assistant fill `tunnel_id` and `openai_tunnel_api_key`, enable the tunnel and restart. Associate the tunnel with your ChatGPT workspace and select **Tunnel** when adding the custom MCP server in ChatGPT.
6. **Safety:** TCP 8765 is unpublished by default. Do not port-forward. Review the seven optional `enable_*` flags before enabling them. Do not run stable and DEV with the same tunnel ID.

Full option-by-option explanations: **[README → Every configuration option](./README.md#5-every-configuration-option)**.

Official sources: [Moonraker authorization](https://moonraker.readthedocs.io/en/latest/external_api/authorization/) · [OpenAI Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels).

## Español — Resumen de instalación

1. **Requisitos:** Home Assistant OS/Supervised en AMD64/ARM64, acceso a una API Moonraker local (normalmente puerto 7125), token HTTP MCP exclusivo e Internet durante la compilación. ChatGPT y el túnel son opcionales.
2. **URL Moonraker:** localiza la IP y prueba `http://IP_IMPRESORA:7125/server/info`; introduce la URL base sin esa ruta en `moonraker_url`.
3. **Clave Moonraker:** desde un cliente autorizado, `GET http://IP_IMPRESORA:7125/access/api_key` permite obtener la clave **actual**, cuando Moonraker lo autoriza. No utilices `POST` para consultarla: la regeneraría. Rellena `moonraker_api_key` solo si hace falta.
4. **Instalación:** añade `https://github.com/sergey08/homeassistant-addons` en **Ajustes → Aplicaciones → Tienda de aplicaciones → ⋮ → Repositorios**. Instala **Moonraker MCP** (sin DEV). Configura `moonraker_url`, `moonraker_api_key` si procede y el `mcp_http_token` obligatorio; deja inicialmente `enable_tunnel` desactivado.
5. **Túnel opcional:** en [Túneles de OpenAI Platform](https://platform.openai.com/settings/organization/tunnels) crea o selecciona un túnel (crear exige **Tunnels Read + Manage**); en [Claves API](https://platform.openai.com/settings/organization/api-keys) genera una clave **Restricted** con **Tunnels Read + Use**. Introduce `tunnel_id` y `openai_tunnel_api_key` en Home Assistant, activa el túnel y reinicia. Asócialo al espacio de ChatGPT y elige la conexión por **Túnel** al añadir el MCP.
6. **Seguridad:** el puerto TCP 8765 no se publica por defecto. No abras puertos del router. Revisa las siete opciones `enable_*` antes de activarlas. No compartas el mismo túnel entre DEV y estable en paralelo.

Explicación exhaustiva de los 13 campos: **[README → Todas las opciones](./README.md#5-explicación-de-todas-las-opciones-de-configuración)**.

Fuentes oficiales: [autenticación Moonraker](https://moonraker.readthedocs.io/en/latest/external_api/authorization/) · [túneles MCP de OpenAI](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels).

### Important limitations / Limitaciones

Encrypted backup restore and real tunnel-key revocation were not fully tested. Existing DEV installations are not automatically migrated. / No se han probado completamente la restauración de copias cifradas ni la revocación real de claves; DEV no migra automáticamente a estable.
