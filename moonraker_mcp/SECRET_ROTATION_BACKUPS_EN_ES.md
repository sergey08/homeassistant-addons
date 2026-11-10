# Operación segura del túnel: credenciales, recuperación y copias / Secure tunnel operations

**DEV12 · 2026-11-07.** Procedimiento de explotación y pruebas sintéticas aisladas; no es un informe de rotación o restauración real del Supervisor. No contiene credenciales reales.

## Español

### Secretos independientes

La instalación utiliza tres elementos diferentes: la API key de Moonraker (si el servidor la necesita), el token Bearer HTTP interno (`mcp_http_token`) y la API key restringida de OpenAI para el túnel (`openai_tunnel_api_key`). El identificador `tunnel_id` no es por sí solo un secreto autenticador.

- No reutilizar claves entre estos componentes y no publicar capturas donde aparezcan.
- Dejar el puerto `8765/tcp` **sin publicar** y no crear redirecciones de router.
- El campo `openai_tunnel_api_key` se aprovisiona a `/data/tunnel/api-key` con propietario UID 65534 y permisos 0600. El ejecutable privado tiene permisos 0700.
- Una contraseña vacía en las opciones puede conservar una clave privada anterior por compatibilidad con versiones DEV previas. **Vaciar el campo no revoca ni borra la credencial ya aprovisionada**.

### Rotación controlada de la clave OpenAI

1. Crear una **clave restringida independiente** con los permisos mínimos del túnel en OpenAI Platform. No revocar la antigua todavía.
2. Introducir la nueva clave en el campo protegido de Home Assistant, guardar y reiniciar el complemento DEV. No introducirla en una terminal ni incluirla en mensajes.
3. Verificar en el registro `tunnel-client started` y `mcp session initialized`; consultar `moonraker_connection_status` desde ChatGPT.
4. Solo cuando la nueva clave funcione, **revocar la antigua** en OpenAI Platform.
5. Revisar la exposición de la clave anterior en copias de seguridad, volcados de diagnóstico o archivos exportados. Las copias antiguas pueden contenerla incluso después de la rotación. Aplicar la política de retención y eliminación de copias del operador.

La revocación se hace en el proveedor de credenciales: cambiar el fichero local **no invalida automáticamente** una clave aún activa en OpenAI. Si se pierde la clave nueva, recuperar acceso con una clave nueva restringida, no restablecer una copia que contenga otra clave activa sin evaluar el riesgo.

### Copias de Home Assistant

El complemento almacena información privada en `/data` (incluyendo `options.json` y el directorio del túnel). Una copia que incluya los datos de aplicaciones puede **contener secretos** aunque los campos se muestren ocultos en la interfaz. Proteger las copias con cifrado y controles de acceso adecuados. No publicar archivos `options.json`, `api-key`, volúmenes completos de aplicaciones ni registros de diagnóstico sin redactar.

Al migrar a otro Home Assistant, la recomendación para una instalación limpia es crear nuevas claves y un túnel separado; no copiar las credenciales personales existentes ni sobrescribir una aplicación en producción.

### Emergencias

Si se sospecha filtración: revocar la clave OpenAI afectada, reemplazar el token MCP y, si procede, la API key de Moonraker. Detener el túnel durante la investigación si se pierde control sobre el acceso, comprobar los registros sin publicarlos y volver a crear claves privadas. **Revocar y reiniciar no garantiza eliminar copias antiguas del secreto**.

## English

Three independent credentials are involved: the printer API key, an internal MCP Bearer token, and a restricted OpenAI tunnel key. Never reuse them. Keep port 8765 unpublished.

To rotate the OpenAI key, create a new restricted key, place it in the Home Assistant protected field, restart, verify the authenticated tunnel and a read-only tool call, then revoke the old key at the provider. Clearing the protected field alone does not delete an already provisioned legacy key. Provider-side revocation is required.

Home Assistant add-on backups may include `options.json` and private tunnel assets. Treat any backups and diagnostic exports as potentially secret-bearing, protect access/encryption, and follow the operator's retention policy. For independent fresh installs use a new tunnel and new credentials rather than restoring another user's private data.

**Validated in isolated unit tests:** synthetic private-data backup/restore demonstrates that restoring an old tunnel directory can resurrect an old key, that an empty password option does not revoke it, and that setting a new password safely replaces it. **Not yet validated:** actual Home Assistant Supervisor encrypted backup restoration, OpenAI provider-side key revocation, and real tunnel reconnection in a disposable independent installation. Do not run these tests against the working DEV12 Lenovo instance without explicit authorization.

### Pruebas sintéticas DEV12 y límites de su evidencia (07/11/2026)

Los tests `test_synthetic_backup_restore_requires_key_rotation_again` y `test_synthetic_restore_with_empty_key_keeps_stale_credential` usan exclusivamente claves ficticias y directorios temporales. Simulan copiar/restaurar `/data/tunnel`, detectan que restaurar datos antiguos recupera también una clave anterior y verifican que `openai_tunnel_api_key` con una clave **nueva y explícita** la sustituye conservando permisos `0600` y `0700`.

**Estas pruebas NO son un respaldo/restore del Supervisor real, no cifran un archivo HA y NO revocan ninguna clave en OpenAI**. La restauración real en un Home Assistant independiente desechable, el tratamiento de copias antiguas y la revocación efectiva siguen siendo requisitos de publicación estable. Nunca probar con las credenciales del Lenovo.
