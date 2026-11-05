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
7. Revisar con el usuario la exposición de `moonraker_server_info` (metadatos), `moonraker_jobqueue_status` (nombres de trabajos, ahora opcional) y las herramientas básicas.
8. Confirmar explícitamente la autorización del usuario **antes** de instalar el complemento DEV, iniciar un contenedor conectado a la impresora o abrir un puerto.

## Plan de ensayo tras aprobación explícita

1. Instalar únicamente en Home Assistant de pruebas o con posibilidad de reversión; no activar arranque automático.
2. Mantener la interfaz MCP aislada de Internet y verificar autenticación antes de cualquier consulta.
3. Consultar solo versión, información de impresora y temperaturas; comprobar el contenido de respuesta y redactar datos sensibles en cualquier registro compartido.
4. Comprobar que las llamadas de control, reinicio, G-code y perfiles opcionales devuelven rechazo HTTP 403.
5. Validar compatibilidad con el cliente MCP de destino y diseñar HTTPS seguro **antes** de habilitar acceso remoto.
6. Detener el complemento si aparecen datos inesperados o cualquier efecto sobre la impresora.

## Ficheros de Moonraker: fases separadas

- **Fase 1 (por defecto):** cuatro consultas básicas de estado; `enable_files: false`.
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

## Cola de impresión: permiso opcional (implementado en DEV)

La herramienta `moonraker_jobqueue_status` **no está habilitada por defecto**: el perfil básico contiene cuatro herramientas y `enable_jobqueue: false`. La cola puede revelar nombres de archivos de impresión y se mantiene como permiso independiente.

Las pruebas automatizadas verifican que `tools/list` no anuncia la herramienta sin permiso, que `tools/call` la rechaza y que el perfil opcional permite consultarla. La CI también comprueba que los siete perfiles opcionales permanezcan desactivados en la configuración inicial. Activar este perfil requiere autorización expresa; no se ha probado con una impresora real.

## Matriz de compatibilidad MCP remoto (revisión estática, DEV)

| Requisito | Estado actual | Acción previa a conectar ChatGPT |
| --- | --- | --- |
| POST JSON-RPC, initialize, tools/list y tools/call | Implementado y probado en Docker | Confirmar con el cliente ChatGPT previsto |
| Sesión `Mcp-Session-Id` | Se reenvía y devuelve el encabezado del upstream | Probar ciclo completo y caducidad de sesión |
| Notificación initialized | Aceptada por POST, devuelve 202 | Probar con el cliente real |
| SSE | Acepta una respuesta upstream de un único evento; responde al cliente en JSON | Comprobar negociación y compatibilidad; no prometer streaming |
| GET del endpoint MCP | Devuelve 405 | Comprobar si el cliente admite operación sin GET streaming |
| DELETE de sesión MCP | Devuelve 405 | Comprobar si el cliente exige cierre explícito |
| Versiones MCP | El upstream utiliza `2025-03-26` o `2025-06-18`; el gateway acepta una propuesta `initialize` de `2025-11-25` y la negocia a `2025-06-18` | Confirmar mediante SDK oficial y después con ChatGPT; no equivale a implementar la versión nueva |
| Autenticación | Bearer estático en el gateway | Validar mecanismo de conexión del cliente; no confundir token estático con OAuth |
| HTTPS público | No implementado en el add-on | Diseñar TLS y controles de exposición antes de publicar una URL |

**Conclusión:** CI verde significa que el transporte limitado funciona en Docker, **no** que ChatGPT pueda registrar o utilizar el servidor MCP remoto. No instalar, mapear puertos, publicar una URL ni conectar la impresora sin autorización expresa.


## Revisión de compatibilidad y seguridad — noviembre de 2026

Fuentes oficiales consultadas:
- OpenAI, servidores MCP personalizados: https://help.openai.com/es-es/articles/12584461-connecting-custom-mcp-servers-in-chatgpt
- Especificación MCP 2025-11-25: https://modelcontextprotocol.io/specification/2025-11-25/basic/transports
- Especificación MCP draft (revisión 2026-07-28): https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/draft/basic/transports/streamable-http.mdx

**Hallazgo de producto:** ChatGPT ofrece conexión a MCP remoto mediante URL HTTPS o Secure MCP Tunnel, sujeto a disponibilidad/permisos de cuenta y espacio de trabajo. No se debe abrir el puerto de Moonraker. Priorizar la evaluación del túnel seguro antes de cualquier exposición pública del gateway.

**Hallazgo de protocolo:** existe una revisión MCP 2026-07-28 con un transporte diferente, sin sesiones de protocolo ni endpoint GET de stream. **El gateway actual NO implementa esa revisión**. Admite las revisiones 2025-03-26 y 2025-06-18 con el upstream y permite que un cliente proponga 2025-11-25 en `initialize`, respondiendo con una revisión anterior negociada; esto no implica soporte íntegro de 2025-11-25. No ampliar versiones nominalmente sin implementar y probar su esquema de mensajes; verificar cuál exige el cliente real.

**Seguridad de origen:** la especificación 2025-11-25 exige comprobar Origin y rechazar valores no válidos. En DEV, el gateway rechaza todas las solicitudes POST que incluyan Origin (403), adecuado como política restrictiva para pruebas servidor-a-servidor; confirmar si el cliente/túnel envía una cabecera Origin antes de declarar compatibilidad.

**Próxima decisión técnica:** determinar el mecanismo de autenticación ofrecido por la conexión personalizada (sin autenticación, bearer o OAuth), el transporte/versiones negociados y disponibilidad del túnel en la cuenta; después decidir si se necesita un adaptador. No desplegar ni conectar la impresora durante la revisión.


## Acceso a MCP personalizado confirmado por el usuario

**Confirmación del usuario (noviembre de 2026):** en su cuenta aparece la opción de añadir servidores MCP personalizados y ya ha utilizado otros MCP creados anteriormente. Por tanto, **la disponibilidad de la opción de alta no bloquea este proyecto**. No inferir por ello qué transportes, versiones, autenticación o características del túnel admite exactamente esta conexión: deben comprobarse por separado.

**Siguientes comprobaciones, sin instalar el add-on ni conectar Moonraker:**

1. Revisar la configuración de conexión de un MCP propio existente (sin copiar tokens, URLs privadas ni secretos a GitHub): tipo de endpoint, HTTPS/túnel y autenticación.
2. Verificar con cliente simulado la negociación MCP y el uso de sesiones que implementa el gateway.
3. Confirmar qué versión MCP exige ChatGPT al añadir un servidor nuevo y si su flujo permite una conexión solo de lectura con el gateway.
4. Preparar un ensayo controlado, sujeto a autorización explícita, antes de instalar el complemento o permitir acceso a la Snapmaker U1.

La opción de alta está confirmada, **pero la compatibilidad funcional de este gateway aún no está demostrada**. Mantener puerto 8765 sin publicar, sin abrir puertos externos y sin instalar hasta autorización expresa.


## Diseño elegido: túnel local en Home Assistant (como Obsidian MCP)

**Corrección de arquitectura (2026-11-04):** la implementación de referencia es **Obsidian MCP en el mismo Lenovo con Home Assistant OS**, no los túneles empresariales de DCL. Se descarta por completo el host Debian DCL, sus direcciones, rutas, proxies, WireGuard y comprobaciones de conectividad: no intervienen en este proyecto.

### Referencia real ya utilizada: Obsidian

- El servidor `obsidian-mcp` funciona como complemento/contenedor en el Lenovo Home Assistant.
- El cliente `tunnel-client` versión `0.0.10` se ejecuta en el propio host/entorno HA, originalmente en el contenedor `obsidian-tunnel` (Alpine 3.22), con túnel HTTPS **saliente** a OpenAI, sin abrir puertos del router.
- En la versión de complemento, el destino interno del canal era `http://c3543d2f-obsidian-mcp:8765/mcp`, en la red Docker `hassio`. El binario y la clave de ejecución permanecen en `/app_configs/obsidian_bridge/tunnel/` del entorno local, nunca en GitHub.
- El acceso desde ChatGPT mediante ese túnel y la lectura de notas de Obsidian ya se probaron. **No reutilizar la identidad del túnel Obsidian ni revelar sus credenciales.**

### Objetivo equivalente para Moonraker

`ChatGPT -> nuevo túnel saliente OpenAI -> tunnel-client en Lenovo/HA -> http://<hostname-del-addon-moonraker>:8765/mcp (red interna hassio) -> gateway filtrado -> upstream mcp-raker (127.0.0.1:8766 dentro del addon) -> Moonraker Snapmaker U1 en la LAN`

1. Crear un **perfil/túnel exclusivamente de Moonraker**, dejando Obsidian y HA-MCP existentes intactos.
2. Ejecutar `tunnel-client` **en Home Assistant**, junto al complemento Moonraker MCP, utilizando conectividad por nombre interno de complemento en `hassio` (como con Obsidian). El valor del hostname definitivo debe comprobarse al instalar; `<hostname-del-addon-moonraker>` es un marcador, no un DNS confirmado.
3. El gateway actual ya exige `Authorization: Bearer <mcp_http_token>` en cada petición HTTP. Configurar un encabezado de autenticación desde un fichero privado en el cliente del túnel **si la versión ejecutada lo admite**, o reutilizar el mismo mecanismo local de autenticación que se verificó con Obsidian. No retirar autenticación, no usar claves compartidas en el repositorio.
4. El puerto 8765 debe ser alcanzable **solo desde la red interna Docker de HA**; no se necesita publicar el puerto en el router, ni realizar conexiones al Debian DCL. Validar la conectividad interna y que únicamente se exponga el gateway filtrado, nunca el `mcp-raker` sin filtrar.
5. Secuencia de pruebas sin impresora: `initialize`, `tools/list`, ejecución de la herramienta de versión y denegación de comandos G-code mediante el túnel. Después, con autorización explícita, instalación y conexión a la Snapmaker U1.

### Estado de desarrollo

La CI Docker sin impresora, con SDK oficial MCP `mcp==1.30.0`, ha confirmado la conexión, el descubrimiento de cuatro herramientas de lectura, la ejecución de `moonraker_mcp_version` y el bloqueo con HTTP 403 de `moonraker_gcode_script`. **Todavía no se ha desplegado el túnel de Moonraker ni instalado el complemento en el HA del usuario.** No confundir la prueba del SDK aislado con una conexión ChatGPT real.


## Actualización de estado — 05/11/2026, DEV3 (prevalece sobre referencias antiguas)

- Desarrollo activo: rama `dev/moonraker-mcp-dev2`, PR #89, versión del complemento `0.1.0-dev3`. Las referencias anteriores a PR #48 y a una instalación todavía no realizada son históricas.
- La versión DEV2 **sí se instaló y se validó localmente** en Home Assistant con la Snapmaker U1 mediante consultas de solo lectura. La DEV3 **no se ha instalado** ni validado con la impresora.
- La CI #46 concluyó correctamente para el commit `87cc0419e038665fb752feb71fc91891cbd99b9a`: pruebas Python, construcción Docker, autenticación, cliente OpenAI oficial v0.0.19 aislado y fallos seguros del túnel. La integración real de OpenAI con DEV3 sigue sin probarse.
- El usuario creó un túnel independiente para Moonraker y una clave restringida, guardada fuera de GitHub. **No escribir ni registrar la clave** en la documentación, código o chat.
- Distribución elegida: **un solo repositorio de complementos** `sergey08/homeassistant-addons`. Para aparecer en el catálogo, el contenido revisado debe integrarse en `main`; no se distribuye desde la PR. El directorio local `/addons/local/moonraker_mcp` (slug `local_moonraker_mcp`) se conserva como DEV2 hasta migración explícita.
- Las verificaciones de CI **no sustituyen** la validación de Home Assistant ni autorizan activar el túnel, abrir puertos o ejecutar comandos de control de impresora. Mantener `enable_tunnel: false` y puerto externo sin asignar hasta pruebas y aprobación.
