# Review of server and temperature responses / Revisión de datos del servidor y temperaturas

**Date / Fecha:** 2026-11-05. **Status / Estado:** privacy assessment of DEV8, not certification or stable-release approval.

## English — Real remote ChatGPT assessment

The following tools were called **through the private OpenAI tunnel from ChatGPT** while the Snapmaker U1 was online. This report deliberately contains **only key names and value types**, not actual device identifiers, time series, local IP addresses or internal paths.

### `moonraker_server_info` (default)

The real response contains these fields:

| Field | Type | Consideration |
| --- | --- | --- |
| `api_version`, `api_version_string` | Version array/string | Normal compatibility information |
| `moonraker_version` | String | Normal diagnostic information |
| `klippy_connected`, `klippy_state` | Boolean/string | Necessary operational information |
| `failed_components`, `warnings` | Arrays | Potentially contain arbitrary upstream error text, paths or identifiers |
| `components` | Array | Can reveal installed plugins, features and integrations |
| `websocket_count` | Number | Operational detail, may reveal usage patterns |

**Decision:** this tool is read-only, but it is **not privacy-sanitized in DEV8**. For a stable public default, consider a strict allowlist of version and connection fields, with a separate explicit opt-in for complete component/error details. In particular, untrusted arbitrary messages within `warnings`/`failed_components` need limits and a redaction decision before publication.

### `moonraker_temperature_store` (default)

The real response has **six named heater/sensor entries**: four extruder entries, a heated bed and a cavity temperature sensor. Each value is an object with cached temperature histories; the payload may reveal timing and usage, even without obvious personal identifiers.

**Decision:** temperature readings are useful for printer monitoring, but any sample history can reveal printing activity or operating patterns. Preserve the useful tool in DEV until we decide whether stable defaults should limit history length, omit timestamps and map custom sensor names to pseudonyms. Never claim time-series data is anonymized without verifying its shape and meaning.

### Existing privacy mitigation

DEV8 `moonraker_printer_info` was checked by real ChatGPT invocation and now returns only printer state and validated firmware version (no hostname, CPU data or paths). That particular privacy gate passed. This does **not** imply the other two tools are safe by default.

## Español — Auditoría de las respuestas reales

Se han consultado `moonraker_server_info` y `moonraker_temperature_store` mediante **el MCP real de ChatGPT**. Para no revelar datos internos, solo se registran campos y tipos:

- **Información del servidor:** versiones de API y Moonraker, estado de Klippy, componentes instalados, advertencias, componentes fallidos y conexiones WebSocket. La lista de componentes revela integraciones; las advertencias pueden incluir rutas u otros identificadores. **DEV8 no filtra estos resultados**.
- **Temperaturas:** seis entradas de extrusores/cama/sensor de cavidad, con datos históricos. Aunque no son datos identificativos evidentes, los historiales pueden permitir inferir cuándo se utiliza la impresora.

**Recomendación antes de estable:** definir respuestas por defecto con lista cerrada de campos y límites de longitud; dejar detalles de integraciones y diagnóstico completo detrás de una opción separada, desactivada por defecto. Documentar la pérdida de campos para usuarios que dependen de ellos. No implementar recortes indiscriminados de temperatura sin revisar la forma de los datos y la utilidad de los gráficos.

## Remaining release gates / Condiciones pendientes

- [x] Enumerar los campos reales sin revelar sus valores.
- [x] Conservar las cinco herramientas de lectura y el túnel privado DEV8 funcionando.
- [ ] Definir y probar redacción estricta de `moonraker_server_info` y errores.
- [ ] Evaluar estructura de la serie de temperatura y límites de muestras conservando su utilidad.
- [ ] Instalación desde cero en otra instancia Home Assistant sin terminal; es una prueba de usuario externo no sustituible por CI.
- [ ] Revisar todas las dependencias/licencias incluidas en los binarios (no solo los dos repositorios upstream).
- [ ] Obtener autorización para fusionar y publicar estable.
