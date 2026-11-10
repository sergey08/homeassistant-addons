# Moonraker MCP v0.1.0 — Inicio rápido / Quick start

**Disponible en el catálogo estable de Home Assistant / Available in the stable Home Assistant catalog.** La versión 0.1.0 se distribuye como código fuente y Home Assistant construye su contenedor localmente. No modifica automáticamente ninguna instalación DEV existente.

## Requisitos / Requirements

- **Obligatorio:** Home Assistant OS o Supervised (AMD64/ARM64), una API Moonraker accesible desde Home Assistant (habitualmente puerto 7125) y un token exclusivo en **mcp_http_token** (recomendados 32+ caracteres).
- **Según la configuración de Moonraker:** su API key, si la exige.
- **Durante la instalación:** Internet para compilar localmente y descargar fuentes/dependencias.
- **Solo para ChatGPT:** acceso a MCP personalizado/túnel según la cuenta, identificador de túnel propio y clave restringida de OpenAI Platform.
- **No hace falta:** Fluidd, abrir el puerto 8765 al exterior, instalar manualmente el cliente de túnel ni utilizar la instalación DEV.

**EN:** Requires HA OS/Supervised on AMD64/ARM64, reachable Moonraker API (usually port 7125), a unique strong MCP HTTP token, a Moonraker API key only if required, and internet access for the local build. ChatGPT/tunnel access and restricted OpenAI credentials are optional. Do not expose port 8765 publicly.

## Español

1. Añade el catálogo `https://github.com/sergey08/homeassistant-addons` en **Ajustes → Aplicaciones → Tienda de aplicaciones → ⋮ → Repositorios**. Instala **Moonraker MCP**. La app 0.1.0 ya aparece en el catálogo estable.
2. Abre **Configuración** del complemento: indica la URL de la API Moonraker (habitualmente `http://impresora:7125`), la clave Moonraker solo si tu servidor la requiere y un token MCP exclusivo en `mcp_http_token`. No compartas ninguna clave en incidencias.
3. Deja `enable_tunnel: false` si solo necesitas acceso MCP local. Para conectar ChatGPT, utiliza **tu propio** identificador de túnel y clave restringida de OpenAI en los campos `tunnel_id` y `openai_tunnel_api_key`, y activa `enable_tunnel`. La disponibilidad del túnel depende de la cuenta y del espacio de trabajo; no es necesario instalar clientes binarios manualmente.
4. Inicia la aplicación y consulta sus registros si hay un problema. El puerto TCP `8765` queda sin publicar por defecto. No publiques este puerto en Internet; los cinco métodos predeterminados son de lectura. Mantén desactivadas las opciones `enable_*` que no necesites.

**Usuarios DEV:** NO desinstalar ni sustituir la instalación funcional automáticamente. La identidad Supervisor del catálogo DEV puede ser diferente de la estable y no se garantiza migración directa, copia de opciones ni secretos. Planificar una migración antes de tocar el servicio existente; no reutilizar simultáneamente un mismo identificador de túnel en dos aplicaciones.

**Limitaciones conocidas:** pruebas de recuperación cifrada y revocación/rotación real de la clave del túnel **NO VERIFICADAS**. Tampoco se debe interpretar el estado del candidato como revisión completa de redistribución de terceros.

## English

1. Add `https://github.com/sergey08/homeassistant-addons` in **Settings → Apps → App Store → ⋮ → Repositories** and install **Moonraker MCP**. Version 0.1.0 is already available in the stable catalog.
2. In the add-on **Configuration** panel, specify your Moonraker API URL (typically `http://printer:7125`), Moonraker API key if needed, and a unique MCP bearer token under `mcp_http_token`.
3. Leave `enable_tunnel: false` for local-only use. To connect ChatGPT, enter your own OpenAI tunnel ID and restricted OpenAI tunnel API key, then enable `enable_tunnel`. No manual binary installation is required.
4. Start the app and inspect logs if needed. TCP `8765` is unpublished by default. Never expose it directly to the Internet. The five default MCP tools are read-only; leave optional `enable_*` profiles off unless required.

**Existing DEV users:** keep the working instance intact. The DEV and stable catalogs may have different Supervisor identities; automatic migration and secret restoration are not guaranteed. Do not run two copies with the same tunnel ID.

**Not verified:** real encrypted backup restoration and tunnel token revocation/rotation. Third-party redistribution obligations require separate release review.

For technical details / Para más detalles: [INSTALLATION_EN_ES.md](./INSTALLATION_EN_ES.md). For release controls / Controles de publicación: [STABLE_RELEASE_MINIMUM_ES.md](./STABLE_RELEASE_MINIMUM_ES.md).
