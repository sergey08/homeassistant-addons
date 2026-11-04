# Preparación de prueba controlada — Snapmaker U1 / Home Assistant

**Estado: planificación exclusivamente. No instalar, conectar ni publicar sin autorización expresa.**

## Entorno previsto

- Home Assistant OS en equipo Lenovo, arquitectura `amd64`.
- Impresora Snapmaker U1 con Moonraker/Klipper y Fluidd.
- Complemento experimental `moonraker_mcp` en rama `dev/moonraker-mcp-addon`, PR #48.
- La imagen del servidor original está fijada por digest y la revisión OCI se verifica en CI. Las etiquetas OCI no constituyen una atestación criptográfica de compilación.

## Comprobaciones previas sin modificar la impresora

1. Confirmar con el usuario la URL interna de Moonraker y el método de autenticación, **sin copiar claves a GitHub, documentación o chat**.
2. Comprobar si la URL interna utiliza HTTP o HTTPS y si requiere API key. Evitar exponer Moonraker a Internet.
3. Revisar el acceso de red desde el contenedor de Home Assistant a Moonraker; la prueba Docker actual no demuestra esa conectividad.
4. Verificar que el puerto externo 8765 permanece **sin publicar** en la configuración inicial del complemento.
5. Preparar un token MCP aleatorio, único y suficientemente largo, almacenado solo en la configuración privada del complemento.
6. Mantener `enable_objects`, `enable_history`, `enable_sensors`, `enable_spoolman` y `enable_power` en `false`.
7. Revisar con el usuario la exposición de `moonraker_server_info` (metadatos), `moonraker_jobqueue_status` (nombres de trabajos) y el resto de herramientas básicas.
8. Confirmar explícitamente la autorización del usuario **antes** de instalar el complemento DEV, iniciar un contenedor conectado a la impresora o abrir un puerto.

## Plan de ensayo tras aprobación explícita

1. Instalar únicamente en Home Assistant de pruebas o con posibilidad de reversión; no activar arranque automático.
2. Mantener la interfaz MCP aislada de Internet y verificar autenticación antes de cualquier consulta.
3. Consultar solo versión, información de impresora y temperaturas; comprobar el contenido de respuesta y redactar datos sensibles en cualquier registro compartido.
4. Comprobar que las llamadas de control, reinicio, G-code y perfiles opcionales devuelven rechazo HTTP 403.
5. Validar compatibilidad con el cliente MCP de destino y diseñar HTTPS seguro **antes** de habilitar acceso remoto.
6. Detener el complemento si aparecen datos inesperados o cualquier efecto sobre la impresora.

## Ficheros de Moonraker: fases separadas

- **Fase 1 (por defecto):** cinco consultas básicas de estado; `enable_files: false`.
- **Fase 2 (requiere nueva aprobación):** activar `enable_files` para listar G-code, consultar metadatos y obtener una vista previa de 16 KiB como máximo.
- **Fuera del alcance actual:** lectura de `printer.cfg`, archivos de configuración, registros, descarga completa, escritura, subida, borrado y ejecución de G-code. Cualquier ampliación necesitará una revisión de permisos independiente.
- Antes de activar la fase 2, inspeccionar las respuestas de prueba para evitar divulgar nombres de trabajos, rutas y comentarios sensibles.
- **No confundir:** Home Assistant aloja la aplicación, pero las consultas de este MCP se realizan directamente a Moonraker, no mediante entidades de Home Assistant.

## Condiciones de salida

- Pruebas de CI completas en verde para el commit final.
- Permisos mínimos confirmados y respuestas revisadas.
- Sin credenciales en repositorios, logs ni documentación.
- Conexión remota deshabilitada hasta contar con HTTPS y autenticación probadas.
- Instalación y publicación requieren decisiones independientes del usuario.

## Decisión pendiente: cola de impresión por defecto

La herramienta `moonraker_jobqueue_status` está habilitada actualmente entre las cinco herramientas básicas. Su respuesta puede contener nombres de archivos de impresión y, por tanto, información privada. **Propuesta para la siguiente revisión de código:** retirarla del perfil predeterminado y añadir una opción booleana `enable_jobqueue: false`, independiente del historial. Esta propuesta aún **no está implementada**; no debe afirmarse que la cola esté desactivada por defecto.

La modificación deberá actualizar de forma coordinada `read_only_allowlist.json`, `tool_policy.py`, `config.yaml`, `run.sh`, documentación y pruebas de CI (incluida la prueba Docker que actualmente espera cinco herramientas). Verificar expresamente que `tools/list` oculta la herramienta y `tools/call` devuelve 403 sin permiso, y que el perfil activado solo permite la consulta GET correspondiente. No activar el perfil ni conectar una impresora durante estas pruebas.
