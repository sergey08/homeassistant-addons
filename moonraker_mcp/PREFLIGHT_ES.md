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

## Condiciones de salida

- Pruebas de CI completas en verde para el commit final.
- Permisos mínimos confirmados y respuestas revisadas.
- Sin credenciales en repositorios, logs ni documentación.
- Conexión remota deshabilitada hasta contar con HTTPS y autenticación probadas.
- Instalación y publicación requieren decisiones independientes del usuario.
