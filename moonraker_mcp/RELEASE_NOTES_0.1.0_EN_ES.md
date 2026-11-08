# Moonraker MCP v0.1.0 — Notas de publicación (borrador)

> **CANDIDATO SIN PUBLICAR.** No crear el tag ni GitHub Release hasta resolver el requisito de redistribución y obtener autorización expresa del mantenedor.

## English

**First stable release candidate** of Moonraker MCP for Home Assistant OS, supporting both **amd64** and **aarch64 (ARM64)**.

- Read-only MCP access to Moonraker-based 3D printers, with **five enabled tools** by default. Seven additional capability groups are disabled unless opted in.
- Optional **outbound OpenAI Secure MCP Tunnel** to connect ChatGPT without forwarding a public router port. Disabled by default.
- Home Assistant configuration panel for Moonraker URL, Moonraker API key (when required), dedicated MCP bearer token and optional OpenAI tunnel ID / restricted API key.
- Strict MCP tool allowlist, protected credentials and privacy filtering of printer/server metadata and temperature histories.
- Multi-architecture container build from pinned upstream source revisions. The included OpenAI tunnel client is **source-built**, not an unmodified upstream release ZIP.
- Default TCP port 8765 is **not published**.

**Important:** Existing users of **Moonraker MCP (DEV)** should not uninstall or switch automatically. A separate Home Assistant add-on catalog can have a different Supervisor identity; migration and credential restoration are not guaranteed. Do not run DEV and stable with the same tunnel ID.

**Prerequisites:** Home Assistant OS on supported architecture, reachable Moonraker, and a unique MCP token. Connecting ChatGPT also requires account/workspace access to custom MCP tunnels and each user's own OpenAI tunnel credentials.

**Documentation:** [Quick start (EN/ES)](./QUICK_START_EN_ES.md) · [Full installation guide](./INSTALLATION_EN_ES.md) · [Third-party notices](./THIRD_PARTY_NOTICES_EN_ES.md) · [Source references](./THIRD_PARTY_SOURCE_ACCESS_EN_ES.md).

## Español

**Primer candidato estable** del complemento Moonraker MCP para Home Assistant OS, compatible con **AMD64 y ARM64**.

- Consulta directa a impresoras compatibles con Moonraker mediante MCP. **Cinco herramientas de solo lectura** activadas inicialmente; siete grupos adicionales desactivados.
- **Túnel privado saliente de OpenAI** opcional para conectar ChatGPT sin abrir puertos del router. Desactivado por defecto.
- Configuración desde la interfaz Home Assistant: URL de Moonraker, API key cuando proceda, token MCP independiente e identificador/clave restringida del túnel opcional.
- Lista cerrada de herramientas, protección de credenciales y filtros de privacidad para datos del equipo y temperaturas.
- Imagen compilada para las dos arquitecturas desde fuentes upstream fijadas; el cliente de túnel se compila desde código, **no** se distribuye como ZIP oficial inalterado.
- El puerto TCP 8765 permanece **sin publicar** por defecto.

**Importante para usuarios DEV:** no desinstalar ni migrar automáticamente la instalación existente. El catálogo de desarrollo puede tener una identidad Supervisor distinta y no se garantiza conservar las opciones ni los secretos. No ejecutar dos instalaciones con el mismo identificador de túnel.

**Requisitos:** Home Assistant OS en una arquitectura compatible, Moonraker accesible y token MCP propio. Para conectar ChatGPT se requiere acceso a la funcionalidad de túneles y credenciales OpenAI propias.

**Documentos:** [Inicio rápido ES/EN](./QUICK_START_EN_ES.md) · [Instalación detallada](./INSTALLATION_EN_ES.md) · [Avisos de terceros](./THIRD_PARTY_NOTICES_EN_ES.md) · [Referencias de fuentes](./THIRD_PARTY_SOURCE_ACCESS_EN_ES.md).

## Estado de preparación / Release readiness

- **Última CI verificada antes de estas notas:** [run 42519501224](https://github.com/sergey08/homeassistant-addons/actions/runs/42519501224), SHA `bdd428e5fcd674d136c0287cbfc7d1bfaa2292d3`. Trabajos de validación, ARM64 e integridad local: **SUCCESS**. Auditorías de fuentes externas opt-in: **SKIPPED**.
- La CI comprueba que los avisos se encuentran dentro de la imagen y bloquea vulnerabilidades HIGH/CRITICAL. El control formal de documentación de licencias **sigue cerrado** hasta completar las revisiones requeridas: **no** equivale a una aprobación jurídica.
- **Pendiente de revisión final:** obligaciones aplicables de aviso y código fuente correspondiente para Alpine/Go, cuando corresponda, y decisión expresa del mantenedor para fusionar PR #125, crear `moonraker-mcp-v0.1.0` y publicar.
- Restauración cifrada y revocación/rotación real del túnel **NO VERIFICADAS**. No se ha solicitado crear nuevos tokens ni alterar el sistema de producción.

