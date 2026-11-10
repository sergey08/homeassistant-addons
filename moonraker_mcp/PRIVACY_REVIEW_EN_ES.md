# Privacy review of default Moonraker tools / Revisión de privacidad de herramientas predeterminadas

## DEV8 implementation and live verification / Implementación y validación real de DEV8 — 2026-11-05

**English:** The default `moonraker_printer_info` handler has now been changed to a bounded read-only local request to `/printer/info` and a strict response schema (`state`, plus validated `software_version` if present). CI tests verify legacy and modern MCP responses, error paths and non-disclosure of host fields. **Real remote verification through ChatGPT and the OpenAI tunnel** returned only `state: ready` and `software_version: 2.0.0-paxx12-23` from DEV8. The connection-status tool also returned `online` / `ready`. No hostname, CPU metadata or file paths were in that response.

**Español:** Ya se ha implementado el filtrado de privacidad en DEV8. La herramienta `moonraker_printer_info` realiza una petición de solo lectura y devuelve solo `state` y `software_version` validada. Las pruebas de CI están en verde y **la llamada real desde ChatGPT por el túnel** devolvió exclusivamente `state: ready` y `software_version: 2.0.0-paxx12-23`; no contiene hostname, rutas ni datos de CPU.

**Residual risk / Riesgo restante:** This does not audit all other enabled tools (`moonraker_server_info`, `moonraker_temperature_store`, optional profiles) or all error payloads and clients. Clean installation, third-party license attribution completeness and endpoint hardening remain release gates. / No se han auditado aún todos los resultados de otras herramientas ni todas las variantes de errores; instalación limpia y seguridad global siguen pendientes.

---


**Date / Fecha:** 2026-11-05. **Status:** release-blocking review; no public stable release approved.

## English

### Verified from an actual connected Snapmaker U1 (without recording field values)

A real ChatGPT call to `moonraker_printer_info` yielded these **nonempty response fields**:

| Field | Potential exposure | Proposed stable default |
| --- | --- | --- |
| `state` | Operational state | Keep |
| `state_message` | May embed error details | Keep with bounded text / inspect before release |
| `software_version` | Firmware version / build | Keep |
| `hostname` | Device identifier and network topology | Redact or move behind opt-in |
| `cpu_info` | System architecture and hardware details | Redact or move behind opt-in |
| `klipper_path` | Absolute installation path | Redact by default |
| `python_path` | Absolute executable path | Redact by default |
| `log_file` | Absolute log path | Redact by default |
| `config_file` | Absolute configuration path | Redact by default |

**No actual hostnames, paths, internal IP addresses or private identifiers have been copied into this document.** The current DEV7 gateway does **not** redact these values; therefore a valid remote tunnel user can read all fields returned by the tool. Reading alone is not equivalent to privacy protection.

The `moonraker_server_info` live result showed Moonraker version, Klippy readiness, component names, warnings and failed components. A component list may reveal installed integrations. `moonraker_temperature_store` may reveal the existence of specific sensors, timestamps and occupancy/usage patterns; do not presume its payload is anonymous without representative inspection.

### Release decision

Prefer a **safe default** that exposes only operational status, software version and necessary health fields. Make detailed host metadata an explicit, disabled-by-default option, or supply a separate opt-in diagnostic tool with stronger privacy disclosure. Do not silently change the meaning of an existing tool without versioning, tests and documentation. No credential value should appear in tool output, local logs or error details.

### Required tests before stable

- Confirm field-level filtering on both legacy and MCP 2026-07-28 responses; do not accidentally bypass filtering for `structuredContent`, JSON text contents, resource items, or errors.
- Confirm host paths/identifiers are not exposed through `tools/list` descriptions or unexpected metadata.
- Check default and opt-in profiles from ChatGPT with positive and negative tests.
- Validate oversized/malformed response behavior without leaking raw upstream bodies.
- Obtain maintainer approval for the reduced default metadata.

## Español

### Resultado de la comprobación real, sin copiar los datos privados

ChatGPT consultó la herramienta `moonraker_printer_info` a una Snapmaker U1 real. Además de estado y versión, su respuesta incluye **nombre del equipo, datos de CPU y rutas internas**: `hostname`, `cpu_info`, `klipper_path`, `python_path`, `log_file` y `config_file`. Se ha registrado únicamente la presencia de estos campos, **no sus valores**.

También es posible identificar componentes instalados mediante `moonraker_server_info` y detalles de sensores mediante `moonraker_temperature_store`. Aunque las herramientas son de lectura, los datos no se anonimizan automáticamente en DEV7.

### Decisión propuesta

Para una versión estable pública, dejar accesibles por defecto únicamente el estado operativo, la versión y la información imprescindible de salud. Las rutas, identificadores y detalles del host deberían eliminarse de la respuesta predeterminada o quedar tras una opción de diagnóstico avanzada, desactivada por defecto. Una modificación de este tipo exige pruebas, documentación y comprobación tanto del protocolo MCP clásico como del moderno.

**Publicación estable bloqueada hasta definir, implementar y validar el filtrado de privacidad.**

### Pruebas pendientes

- Evitar filtraciones en respuestas JSON, `structuredContent`, recursos y errores.
- Probar permisos y negaciones tanto desde ChatGPT como con tests automáticos.
- Comprobar que no se exponen rutas o nombres de host en descripciones ni registros.
- Revisar seguridad de la instalación limpia y rotación de credenciales.
- Obtener autorización del responsable antes de fusionar o publicar.
