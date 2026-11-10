# Moonraker MCP v0.1.0 — Inicio rápido / Quick start

**CANDIDATO SIN PUBLICAR / UNPUBLISHED RELEASE CANDIDATE.** No está todavía disponible en el catálogo estable de Home Assistant. Este documento describe el proceso previsto tras la publicación y **no pide modificar el complemento DEV ya instalado**.

## Español

1. Tras anunciarse la publicación, añade el catálogo `https://github.com/sergey08/homeassistant-addons` en **Ajustes → Aplicaciones → Tienda de aplicaciones → ⋮ → Repositorios**. Instala **Moonraker MCP**. Antes de publicar, la app no aparecerá en la tienda estable.
2. Abre **Configuración** del complemento: indica la URL de la API Moonraker (habitualmente `http://impresora:7125`), la clave Moonraker solo si tu servidor la requiere y un token MCP exclusivo en `mcp_http_token`. No compartas ninguna clave en incidencias.
3. Deja `enable_tunnel: false` si solo necesitas acceso MCP local. Para conectar ChatGPT, utiliza **tu propio** identificador de túnel y clave restringida de OpenAI en los campos `tunnel_id` y `openai_tunnel_api_key`, y activa `enable_tunnel`. La disponibilidad del túnel depende de la cuenta y del espacio de trabajo; no es necesario instalar clientes binarios manualmente.
4. Inicia la aplicación y consulta sus registros si hay un problema. El puerto TCP `8765` queda sin publicar por defecto. No publiques este puerto en Internet; los cinco métodos predeterminados son de lectura. Mantén desactivadas las opciones `enable_*` que no necesites.

**Usuarios DEV:** NO desinstalar ni sustituir la instalación funcional automáticamente. La identidad Supervisor del catálogo DEV puede ser diferente de la estable y no se garantiza migración directa, copia de opciones ni secretos. Planificar una migración antes de tocar el servicio existente; no reutilizar simultáneamente un mismo identificador de túnel en dos aplicaciones.

**Limitaciones conocidas:** pruebas de recuperación cifrada y revocación/rotación real de la clave del túnel **NO VERIFICADAS**. Tampoco se debe interpretar el estado del candidato como revisión completa de redistribución de terceros.

## English

1. Once stable publication is announced, add `https://github.com/sergey08/homeassistant-addons` in **Settings → Apps → App Store → ⋮ → Repositories** and install **Moonraker MCP**. It is not yet available in the stable catalog.
2. In the add-on **Configuration** panel, specify your Moonraker API URL (typically `http://printer:7125`), Moonraker API key if needed, and a unique MCP bearer token under `mcp_http_token`.
3. Leave `enable_tunnel: false` for local-only use. To connect ChatGPT, enter your own OpenAI tunnel ID and restricted OpenAI tunnel API key, then enable `enable_tunnel`. No manual binary installation is required.
4. Start the app and inspect logs if needed. TCP `8765` is unpublished by default. Never expose it directly to the Internet. The five default MCP tools are read-only; leave optional `enable_*` profiles off unless required.

**Existing DEV users:** keep the working instance intact. The DEV and stable catalogs may have different Supervisor identities; automatic migration and secret restoration are not guaranteed. Do not run two copies with the same tunnel ID.

**Not verified:** real encrypted backup restoration and tunnel token revocation/rotation. Third-party redistribution obligations require separate release review.

For technical details / Para más detalles: [INSTALLATION_EN_ES.md](./INSTALLATION_EN_ES.md). For release controls / Controles de publicación: [STABLE_RELEASE_MINIMUM_ES.md](./STABLE_RELEASE_MINIMUM_ES.md).
