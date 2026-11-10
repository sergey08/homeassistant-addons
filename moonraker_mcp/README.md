# Moonraker MCP para Home Assistant

**v0.1.0 · AMD64 / ARM64 · Servidor MCP para impresoras 3D con Moonraker**

Conecta clientes MCP —incluido ChatGPT mediante un túnel privado opcional— con una impresora 3D que utilice Moonraker. El complemento consulta la API de la impresora **directamente**, sin requerir una integración de esa impresora en Home Assistant.

## Requisitos previos

| Componente | Necesario | Detalle |
| --- | --- | --- |
| **Home Assistant OS o Supervised** | Sí | Tienda de aplicaciones y Supervisor, arquitectura **AMD64 (x86-64)** o **ARM64 (aarch64)** |
| **Impresora compatible con Moonraker** | Sí | Moonraker en funcionamiento y accesible desde Home Assistant por la red, habitualmente en el **puerto 7125** |
| **Dirección de la API** | Sí | Por ejemplo, **http://printer.local:7125**. No confundir con la interfaz Fluidd si tiene otro puerto |
| **Clave API de Moonraker** | Si se requiere | Solo si la configuración de Moonraker exige autenticación por clave |
| **Token HTTP MCP exclusivo** | Sí | Contraseña aleatoria y única; recomendamos **32 caracteres o más**, sin reutilizar otras claves |
| **Acceso a Internet durante la instalación** | Sí | Home Assistant compila la imagen desde el código y descarga fuentes y dependencias; no hay imagen GHCR precompilada propia |
| **Acceso a MCP personalizado en ChatGPT** | Solo para ChatGPT | Su disponibilidad depende del plan y de las opciones de la cuenta/espacio de trabajo |
| **Túnel OpenAI y clave restringida** | Solo para ChatGPT remoto | Identificador de túnel propio y clave API con permisos mínimos para ese túnel |

**No se necesita:** instalar Moonraker dentro de Home Assistant, instalar manualmente el cliente de túnel, abrir puertos en el router ni crear entidades de Home Assistant.

## Instalación

1. En **Ajustes → Aplicaciones → Tienda de aplicaciones → ⋮ → Repositorios**, añade **https://github.com/sergey08/homeassistant-addons** si no está registrado.
2. Actualiza la tienda y busca **Moonraker MCP** (sin «DEV»). Selecciona **Instalar**. El primer proceso puede tardar más porque el contenedor se construye localmente.
3. Abre **Configuración**, introduce los valores indicados y guarda.
4. Inicia el complemento y revisa **Registros** si aparece un error.

| Campo en Home Assistant | Configuración inicial |
| --- | --- |
| **moonraker_url** | URL de API, por ejemplo http://printer.local:7125 |
| **moonraker_api_key** | Solo si Moonraker la necesita |
| **mcp_http_token** | **Obligatorio**: token aleatorio exclusivo |
| **enable_tunnel** | **Desactivado** inicialmente |
| **tunnel_id** | Vacío, salvo que utilices ChatGPT remoto |
| **openai_tunnel_api_key** | Vacío, salvo que utilices el túnel |
| **Otras opciones enable_*** | **Desactivadas** inicialmente |

## Conexión a ChatGPT (opcional)

1. Verifica que tu cuenta pueda añadir servidores MCP personalizados y utilizar el túnel seguro.
2. En OpenAI Platform, configura tu propio túnel y su clave API restringida.
3. Introduce **tunnel_id** y **openai_tunnel_api_key** desde la interfaz de Home Assistant; activa **enable_tunnel**, guarda y reinicia.
4. En ChatGPT, añade el servidor MCP personalizado seleccionando el túnel, si está disponible para tu cuenta.

El puerto TCP **8765 no se publica por defecto**. No lo expongas a Internet ni compartas claves en capturas, incidencias o chats.

## Herramientas disponibles por defecto

| Herramienta MCP | Qué consulta |
| --- | --- |
| **moonraker_connection_status** | Conectividad de Moonraker |
| **moonraker_mcp_version** | Versión del servidor MCP |
| **moonraker_printer_info** | Estado Klippy y versión, sin datos internos innecesarios |
| **moonraker_server_info** | Estado y versiones Moonraker/Klippy |
| **moonraker_temperature_store** | Historial de temperaturas limitado y con nombres personalizados anonimizados |

Las funciones opcionales de archivos, cola, objetos, historial, sensores, Spoolman y energía permanecen **desactivadas de forma predeterminada**. El perfil inicial no ejecuta G-code, inicia impresiones ni modifica la impresora.

## Preguntas frecuentes

**¿Funciona con Snapmaker U1?** Sí, con firmware que proporcione una API Moonraker compatible.

**¿Hace falta Fluidd?** No. Fluidd es una interfaz; este complemento utiliza la API Moonraker directamente.

**¿Hace falta ChatGPT?** No. El servidor MCP puede iniciarse sin túnel. Para el acceso local de otros clientes es necesaria una conexión privada y autenticada.

**¿Puedo pasar directamente desde Moonraker MCP (DEV)?** No se garantiza una actualización directa: DEV y estable utilizan identidades Supervisor diferentes. Conserva la instalación DEV que funciona y **no utilices el mismo ID de túnel en ambas a la vez**.

**¿Cuáles son las limitaciones de la versión 0.1.0?** La restauración cifrada y la revocación real de credenciales aún no se han verificado de extremo a extremo. El complemento se distribuye como código fuente para compilación local, sin imagen GHCR propia.

## Documentación

- [Inicio rápido (ES/EN)](./QUICK_START_EN_ES.md)
- [Instalación detallada (EN/ES)](./INSTALLATION_EN_ES.md)
- [Avisos de terceros](./THIRD_PARTY_NOTICES_EN_ES.md)
- [Acceso a fuentes de terceros](./THIRD_PARTY_SOURCE_ACCESS_EN_ES.md)
- [Notas de la versión](./RELEASE_NOTES_0.1.0_EN_ES.md)

El código original del repositorio se distribuye bajo [licencia MIT](../LICENSE); los componentes de terceros conservan sus licencias correspondientes. El desarrollo DEV previo se puede consultar en el historial de GitHub.

---

## English — Requirements and quick setup

**Required:** Home Assistant OS/Supervised on AMD64 or ARM64; a reachable Moonraker API (usually port 7125); a strong, unique **mcp_http_token**; and a Moonraker API key only if the Moonraker server requires one. Internet access is needed during installation because the container builds locally from pinned sources.

**Optional ChatGPT access:** A ChatGPT account/workspace with custom MCP and tunnel access, plus your own OpenAI Platform tunnel ID and restricted API key.

**Install:** Add **https://github.com/sergey08/homeassistant-addons** to the Home Assistant app repositories. Install **Moonraker MCP** (not DEV), set **moonraker_url**, the optional **moonraker_api_key**, and mandatory **mcp_http_token**, then start with **enable_tunnel** disabled. For ChatGPT, provide **tunnel_id** and **openai_tunnel_api_key**, enable the tunnel and restart.

**Security:** Port 8765 is unpublished. Never expose it to the public Internet. Five read-only tools are enabled by default; additional profiles are off. DEV installations do not migrate automatically.

[Full bilingual installation guide](./INSTALLATION_EN_ES.md) · [Third-party notices](./THIRD_PARTY_NOTICES_EN_ES.md)
