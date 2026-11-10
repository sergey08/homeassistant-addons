# Moonraker MCP — Changelog / Historial de cambios

Updates are described in English first and then in Spanish.
Las actualizaciones se describen primero en inglés y después en español.

---

## 0.1.1 — 2026-11-10

### English

**New: Spoolman inventory from ChatGPT**

- Added the optional `moonraker_spoolman_inventory` MCP tool to list up to 100 Spoolman spools.
- Returns a filtered inventory with spool ID, archived state, filament name/material, manufacturer, color, and available remaining/used/initial weight in grams.
- Uses the existing Moonraker connection and its configured Spoolman integration. The request goes through Moonraker's Spoolman proxy with an internally fixed **GET /v1/spool** request; clients cannot choose another URL, method, or request body.
- Only available when **Extra access: Spoolman filament** (`enable_spoolman`) is enabled. The tool remains unavailable when that option is off.
- Added validation and automated tests for explicit permission, invalid responses, size limits, bounded records, sensitive-field filtering, and redirect protection.
- Updated the English and Spanish configuration descriptions and README examples.

**Security and compatibility**

- The new inventory tool is **read-only**. It cannot edit spools, register filament consumption, delete files, execute G-code, or control printer power.
- Requires a working **Spoolman integration in Moonraker**; having Spoolman installed separately in Home Assistant is not sufficient.
- Upgrading from 0.1.0 preserves your existing configuration and tunnel credentials. No new keys are required.
- Compatible with Home Assistant on **AMD64** and **ARM64**.
- Your ChatGPT MCP connection may need its tool catalog refreshed, followed by a new conversation, before the new tool becomes available.

### Español

**Novedad: inventario de Spoolman desde ChatGPT**

- Incorporada la herramienta MCP opcional `moonraker_spoolman_inventory`, que permite consultar hasta **100 bobinas** de Spoolman.
- Devuelve un inventario filtrado con identificador, estado de archivo, nombre y material del filamento, fabricante, color y pesos disponibles (restante, consumido e inicial) en gramos.
- Aprovecha la conexión actual a Moonraker y su integración Spoolman. Utiliza el proxy de Moonraker con una solicitud interna fija **GET /v1/spool**; el cliente no puede cambiar la ruta, el método ni el contenido de la petición.
- Solo aparece si está activada la opción **Acceso adicional: filamentos Spoolman** (`enable_spoolman`).
- Añadidas pruebas automáticas sobre permisos, respuestas incorrectas, límites de tamaño, número máximo de bobinas, filtrado de información y protección frente a redirecciones.
- Actualizadas las explicaciones de configuración y los ejemplos del README en inglés y español.

**Seguridad y compatibilidad**

- El inventario funciona **exclusivamente en modo lectura**. No modifica bobinas ni registra consumos; tampoco borra archivos, ejecuta G-code ni controla la alimentación.
- Requiere tener **Spoolman conectado a Moonraker**. Tener únicamente Spoolman instalado como aplicación de Home Assistant no es suficiente.
- La actualización desde la 0.1.0 conserva las opciones configuradas y las credenciales del túnel. No es necesario generar nuevas claves.
- Compatible con Home Assistant **AMD64** y **ARM64**.
- Puede ser necesario actualizar las herramientas del MCP en ChatGPT y abrir una nueva conversación para descubrir la función.

---

## 0.1.0 — 2026-11-10

### English

**First stable Home Assistant app release**

- Published Moonraker MCP as a Home Assistant app for AMD64 and ARM64, with local source-based container builds.
- Connects compatible MCP clients, including ChatGPT through the optional **OpenAI Secure MCP Tunnel**, directly to the Moonraker API.
- Provides five default **read-only** tools for MCP version, printer information, Moonraker server information, recent temperatures, and connectivity.
- Seven optional read-only access profiles: job queue, G-code files, Klipper objects, print history, sensors, Spoolman status/spool lookup, and power-device status.
- English and Spanish configuration labels and descriptions for all 13 options; comprehensive bilingual README, application icon, and logo.
- Safeguards include an explicit tool allowlist, authenticated MCP access, restricted information in default responses, and no public host-port mapping by default.
- Optional profiles do **not** grant printing, G-code execution, file deletion, Spoolman modifications, or power switching.

### Español

**Primera versión estable para Home Assistant**

- Publicado Moonraker MCP como aplicación de Home Assistant para AMD64 y ARM64, con compilación local del contenedor desde el código fuente.
- Conecta clientes MCP compatibles, incluido ChatGPT mediante el **túnel seguro opcional de OpenAI**, directamente con la API de Moonraker.
- Incluye cinco herramientas básicas **de solo lectura**: versión MCP, información de la impresora, información del servidor, historial reciente de temperaturas y conectividad.
- Siete perfiles opcionales de consulta: cola de trabajos, archivos G-code, objetos Klipper, historial de impresión, sensores, estado/bobina de Spoolman y estado de alimentación.
- Nombres y explicaciones de las 13 opciones en inglés y español, README bilingüe completo, icono y logotipo.
- Protección mediante lista explícita de herramientas autorizadas, autenticación MCP, filtrado de datos técnicos y puerto público sin publicar por defecto.
- Los perfiles adicionales **no autorizan** iniciar impresiones, ejecutar G-code, borrar archivos, modificar Spoolman ni activar o desactivar alimentación.

---

**Support / Soporte:** https://github.com/sergey08/homeassistant-addons/issues
