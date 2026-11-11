# Moonraker MCP — Changelog / Historial de cambios

Updates are described in English first and then in Spanish.
Las actualizaciones se describen primero en inglés y después en español.

---

## 0.1.3 — 2026-11-11

### English

**Security improvement: master permission for printer write actions**

- Added `enable_write_actions`, a new **master switch** for physical print controls. It is **OFF by default**, including after upgrading from 0.1.2.
- The four existing, independent permissions (`allow_print_pause`, `allow_print_resume`, `allow_print_cancel`, `allow_print_start`) remain **OFF by default**. A write tool is exposed only if **both** the master switch and its corresponding action switch are explicitly enabled.
- With the master switch off, even if one or all individual write permissions are accidentally enabled, the MCP gateway does not expose or authorize their print-control tools.
- The add-on launcher strictly validates that the master switch is a boolean. Invalid values stop initialization instead of weakening authorization.
- Added tests exercising the actual launcher permission filter for all-individual-on/master-off, master-on/one-permission, absent master and invalid option values.
- Improved the English and Spanish option descriptions and README security instructions.

**Safety, upgrade and compatibility**

- Normal upgrades preserve existing Moonraker and OpenAI Secure MCP Tunnel settings; **no new tokens or keys** are required.
- Read-only capabilities, including Spoolman inventory, printer snapshot and T0–T3 filament information, are unaffected by the master write switch.
- Compatible with AMD64 and ARM64 Home Assistant OS/Supervised.
- No printer movement, heating, pause, resume, cancel, file modification, or other physical command is necessary for this update.
- The master gate protects against configuration mistakes but **does not prove human approval**. Always request explicit human authorization before triggering any write tool. Do not enable write actions until you are ready to test them on your specific printer.

### Español

**Mejora de seguridad: permiso general para acciones de escritura en la impresora**

- Incorporada la nueva opción `enable_write_actions`, un **interruptor general** para las operaciones físicas de impresión. Está **desactivada por defecto**, también al actualizar desde la versión 0.1.2.
- Los cuatro permisos independientes existentes (`allow_print_pause`, `allow_print_resume`, `allow_print_cancel` y `allow_print_start`) siguen **desactivados por defecto**. Una herramienta de escritura solo aparece si se activan expresamente **tanto el permiso general como el de la acción concreta**.
- Con el interruptor general apagado, incluso si se activan por error uno o todos los permisos individuales, el MCP no expone ni autoriza sus controles de impresión.
- El arranque valida estrictamente que el permiso general sea booleano. Los valores incorrectos impiden la inicialización, en vez de rebajar la protección.
- Añadidas pruebas del filtro de permisos real del complemento: todos los permisos individuales encendidos y general apagado, general encendido con un permiso específico, general ausente y valores de configuración incorrectos.
- Mejoradas las descripciones de las opciones y las instrucciones de seguridad del README en inglés y español.

**Seguridad, actualización y compatibilidad**

- Una actualización normal conserva la conexión con Moonraker y la configuración del túnel seguro de OpenAI; **no requiere nuevas claves ni tokens**.
- Las consultas de solo lectura, incluido el inventario de Spoolman, el estado de impresión y los filamentos T0–T3, no se ven afectadas por el interruptor general.
- Compatible con Home Assistant OS/Supervised en AMD64 y ARM64.
- La actualización no exige mover o calentar la impresora, pausar, reanudar, cancelar, modificar archivos ni ejecutar otras órdenes físicas.
- El interruptor general protege frente a errores de configuración, pero **no demuestra autorización humana**. Es obligatorio pedir aprobación expresa antes de cualquier herramienta de escritura. No actives estos permisos hasta que quieras probarlos de forma controlada en tu impresora.

---

## 0.1.2 — 2026-11-10

### English

**New read-only Snapmaker U1 diagnostics**

- Added the opt-in `moonraker_print_snapshot` tool for current print state, file name, active tool (T0–T3), layer counts, elapsed durations, and independently labelled display/file progress percentages.
- Added the opt-in `moonraker_filament_slots` tool to read four filament positions, their materials, manufacturers and colors directly from Klipper's `filament_detect` object, without Home Assistant entities.
- The four-slot view excludes NFC tag identifiers and secret fields. It does **not** claim a verified Spoolman spool ID per slot.
- Deliberately omits a guessed finish time because the reported progress sources can disagree.
- Both tools use the new `enable_u1_status` setting, which is **OFF by default**.

**New individually authorized print actions**

- Four separate, initially **OFF**, settings: `allow_print_pause`, `allow_print_resume`, `allow_print_cancel`, and `allow_print_start`.
- Each exposes only its matching tool. Print operations are checked against the current Klipper ready state and print state before being sent to fixed Moonraker endpoints.
- Cancel requires the exact currently printing G-code filename. Start validates the G-code filename and checks that a nonempty file exists before requesting a print.
- Every write tool requires an action-specific confirmation argument; the ChatGPT client must also obtain **explicit human approval** for the operation. A confirmation string alone does not prove consent.
- No arbitrary G-code, file modification/deletion, Spoolman changes, or power switching is enabled.
- Added simulated tests for safe/unsafe states, unexpected arguments, confirmation, missing G-code files, privacy filtering and independent permissions. No physical printer operations were used in automated tests.

**Requirements and compatibility**

- Home Assistant OS/Supervised, AMD64 or ARM64, with Moonraker and Klippy accessible.
- Existing configuration and tunnel credentials should be retained during a normal add-on update; new permissions remain off unless deliberately enabled.
- MCP clients may need a refreshed tool catalog and a new conversation to discover new tools.
- Physical print-control behavior must be reviewed on the specific printer before enabling write permissions; HTTP acceptance does not guarantee completion.

### Español

**Nuevas consultas de diagnóstico para Snapmaker U1**

- Incorporada la herramienta opcional `moonraker_print_snapshot` para consultar estado, archivo, cabezal activo (T0–T3), capas, tiempos transcurridos y porcentajes de progreso diferenciados de la pantalla y del archivo.
- Incorporada `moonraker_filament_slots` para consultar directamente los cuatro filamentos, materiales, fabricantes y colores mediante el objeto Klipper `filament_detect`, sin depender de entidades de Home Assistant.
- La vista de filamentos no muestra identificadores NFC ni campos privados. **No atribuye** un ID de bobina Spoolman a cada posición sin haber verificado esa asociación.
- No inventa una hora de finalización, porque las distintas fuentes de progreso pueden discrepar.
- Ambas consultas se habilitan con la nueva opción `enable_u1_status`, **desactivada por defecto**.

**Nuevos controles de impresión con permisos individuales**

- Cuatro ajustes separados, inicialmente **desactivados**: `allow_print_pause`, `allow_print_resume`, `allow_print_cancel` y `allow_print_start`.
- Cada ajuste habilita exclusivamente su herramienta correspondiente. Antes de ordenar una operación se comprueban el estado actual de Klipper y de la impresión y solo se utilizan endpoints fijos de Moonraker.
- Cancelar exige el nombre exacto del G-code que se está imprimiendo. Iniciar verifica el nombre y la existencia de un archivo G-code no vacío antes de solicitar la impresión.
- Las operaciones de escritura requieren un argumento de confirmación específico; además, el cliente ChatGPT debe obtener **aprobación humana explícita**. Un texto de confirmación no demuestra por sí solo que exista consentimiento.
- No se habilitan G-code arbitrario, edición o borrado de archivos, modificaciones de Spoolman ni conmutación eléctrica.
- Incorporadas pruebas simuladas de estados permitidos y rechazados, parámetros imprevistos, confirmaciones, archivos inexistentes, privacidad y separación de permisos. Las pruebas automáticas no han enviado órdenes físicas a la impresora.

**Requisitos y compatibilidad**

- Home Assistant OS/Supervised en AMD64 o ARM64, con Moonraker y Klippy accesibles.
- La actualización normal debería conservar la configuración y las credenciales del túnel; los permisos nuevos permanecerán apagados hasta activarlos expresamente.
- Puede ser necesario actualizar el catálogo de herramientas MCP en ChatGPT y abrir otra conversación para descubrirlas.
- Debe comprobarse el comportamiento de los controles sobre cada impresora antes de habilitar escritura; una respuesta HTTP aceptada no garantiza la finalización de una acción física.

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
