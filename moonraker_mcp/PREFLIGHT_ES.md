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


## Diseño elegido: OpenAI Secure MCP Tunnel (confirmado por el usuario)

El usuario ha elegido expresamente reutilizar el **mismo mecanismo OpenAI Secure MCP Tunnel / tunnel-client** que emplea con sus otros MCP (Home Assistant, SSH y SAP Cloud Connector). **No utilizar Cloudflare Tunnel independiente, DuckDNS, redirección de puertos del router ni exponer Moonraker a Internet.**

### Topología prevista (aún no desplegada)

`ChatGPT -> OpenAI Secure MCP Tunnel dedicado -> tunnel-client -> gateway HTTP de solo lectura (:8765) -> mcp-raker (127.0.0.1:8766, interno) -> Moonraker U1 (LAN)`

- Crear identidad y perfil de túnel **separados**, sin cambiar los túneles de HA, SSH u otros MCP.
- El complemento Home Assistant sigue con arranque manual y el mapeo externo del puerto 8765 sin publicar (`null`) por defecto. Un cliente túnel ejecutado fuera de su espacio de red no puede acceder a un puerto no publicado: **hay que diseñar y verificar un canal interno entre ambos procesos** antes de integrar el túnel. No resolverlo publicando el puerto en el router.
- El `tunnel-client` se conectará de forma **saliente** al servicio de túneles. Su destino local debe apuntar exclusivamente al gateway filtrado; nunca al `mcp-raker` sin filtrar ni a la API Moonraker.
- No escribir en GitHub el Tunnel ID privado, claves, tokens, rutas secretas ni direcciones internas. Guardarlos únicamente en configuración local protegida.
- **Compatibilidad de autenticación pendiente:** el gateway actual exige `Authorization: Bearer <mcp_http_token>` en cada POST. Comprobar si el cliente de túnel puede añadir ese encabezado al destino local de manera segura. Si no puede, no desactivar sin más la autenticación; diseñar un adaptador local con privilegios mínimos o una identidad autenticada equivalente.
- Probar de forma independiente las solicitudes `initialize`, `notifications/initialized`, `tools/list`, `tools/call` autorizadas y denegadas a través del túnel, con un servicio de prueba **sin impresora**.
- Solo con autorización explícita: preparar el túnel, instalar el complemento, conectar Moonraker y registrar el servidor en ChatGPT; son decisiones separadas. La selección de arquitectura de túnel **no autoriza el despliegue**.

### Criterio de avance

La CI Docker con el SDK oficial MCP `mcp==1.30.0` ya ha comprobado autenticación, descubrimiento de cuatro herramientas, consulta de versión y denegación de G-code. Falta el ensayo de extremo a extremo **a través del OpenAI Secure MCP Tunnel**, y después el ensayo controlado en Home Assistant con la Snapmaker U1.
