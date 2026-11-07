# Fresh Home Assistant installation acceptance / Validación de instalación limpia

**Moonraker MCP 0.1.0-dev12 · Development only · 2026-11-07**

This procedure is for a **second, independent HA OS/Supervisor aarch64 (ARM64) installation; amd64 also remains supported**, not for the production/working DEV11. It is an acceptance checklist, **not** evidence that the test has already happened. Do not transfer credentials, private `/data/tunnel` folders or backups from an existing installation.

## Español — Comprobación sin terminal

**Preparación:** utiliza otro Home Assistant con Supervisor, una impresora Moonraker accesible (puede estar apagada durante la primera prueba), y permisos propios para gestionar el túnel OpenAI. No repitas el ensayo con las credenciales de la instalación que ya funciona.

1. **Instalación desde la tienda.** En Ajustes → Aplicaciones → Tienda → ⋮ → Repositorios, añade el catálogo DEV indicado en [INSTALLATION_EN_ES.md](./INSTALLATION_EN_ES.md), actualiza y comprueba que aparece **Moonraker MCP (DEV)** versión `0.1.0-dev11`. Instala desde la interfaz, sin SSH, Docker ni creación manual de ficheros.
2. **Configuración mínima.** Indica la URL HTTP real de Moonraker (normalmente puerto 7125), API key si la exige y un **nuevo token MCP único**. Mantén los siete perfiles opcionales desactivados y el puerto 8765/tcp sin publicar. Arranca con el túnel desactivado y comprueba que el complemento queda iniciado.
3. **Credenciales exclusivas.** En OpenAI Platform crea otro túnel y otra clave restringida, distintos de los del sistema existente. Introduce sus valores únicamente en los campos protegidos de HA; activa el túnel y reinicia el complemento desde la interfaz.
4. **Túnel y ChatGPT.** Comprueba que el registro muestra `tunnel-client started` y `mcp session initialized`, sin incluir secretos. Añade un servidor MCP personalizado de ChatGPT mediante ese túnel. En el extremo privado del túnel selecciona «Sin autenticación» si la interfaz así lo indica; la clave OpenAI y el token interno siguen siendo obligatorios.
5. **Herramientas.** Comprueba que aparecen únicamente `moonraker_connection_status`, `moonraker_mcp_version`, `moonraker_printer_info`, `moonraker_server_info` y `moonraker_temperature_store`. Comprueba versiones, respuesta filtrada y máximo 120 lecturas por serie, sin rutas ni nombres internos. Debe denegarse una llamada a una herramienta de escritura no permitida.
6. **Impresora desconectada y reconexión.** Apaga o desconecta solo la impresora de pruebas; consulta `moonraker_connection_status` y comprueba `offline_or_unreachable`, sin afirmar que se conoce con certeza la causa. Reconecta y verifica `online` sin reiniciar HA o el túnel.
7. **Arranque y fallo seguro.** Reinicia el complemento desde la UI, comprueba que conserva configuración y que no publica puertos ni activa opciones de escritura. Si el túnel no está disponible, el complemento debe dar error comprensible, **sin mostrar la clave** ni abrir un acceso alternativo.
8. **Rotación segura, solo en el segundo entorno.** Sustituye la clave OpenAI por otra restringida desde la UI. Verifica la conexión, revoca la clave anterior desde OpenAI Platform y confirma que la antigua ya no permite acceso. No borres el campo esperando revocación: puede persistir el fichero anterior.
9. **Backup y recuperación.** En un entorno desechable realiza copia cifrada, verifica que no compartes archivos privados y recupera en un entorno de pruebas. Antes de reutilizarla revoca o rota credenciales; comprueba que la restauración no expone públicamente el puerto. No adjuntes copias a GitHub, Obsidian ni ChatGPT.

**Evidencia aceptable:** versión del complemento, arquitectura, estado `started`, lista de nombres de cinco herramientas, `online/offline`, presencia de logs de inicio **redactados**, estado de red sin puerto publicado, y resultado de rotación/restauración **sin secretos, nombres privados, identificadores del túnel ni copias de seguridad**.

**Criterios de rechazo:** requiere terminal para aprovisionar archivos; credenciales filtradas a logs; falta alguna herramienta predeterminada; aparecen herramientas de escritura; el gateway es accesible desde fuera; una reconexión exige reiniciar HA o reconfigurar túnel; restauración insegura. No tratar errores de la cuenta/servicio OpenAI como defectos de empaquetado sin comprobar el contexto.

## English — Clean GUI-only acceptance

Test on a **separate, disposable HA OS/Supervisor amd64 instance** using its own restricted OpenAI key, tunnel ID and unique MCP Bearer token. Install the dev add-on through the app store; configure only through the HA UI. Verify startup without manual files, outbound tunnel, five read-only names, sanitized results, 120-point temperature cap, forbidden write-tool rejection, printer offline/online transition, no exposed port, safe restart, independent key rotation, and encrypted backup/restore with fresh credentials.

Do not import the existing operator's secrets. Record only redacted evidence. Do **not** mark this checklist complete until each item has been observed on the independent host; GitHub Actions' simulated first-run test is useful but does not replace this end-to-end procedure.

**Release gate:** PR #89 remains DRAFT; main merge/stable distribution needs independent clean install, exact-SBOM human license/notice review and explicit authorization.
