# Moonraker MCP for Home Assistant

**Version 0.1.0 · AMD64 and ARM64 · Read-only MCP bridge by default**

Moonraker MCP connects an OpenAI-compatible MCP client (optionally ChatGPT through a **Secure MCP Tunnel**) to a 3D printer's **Moonraker API**. The app runs in Home Assistant OS / Supervised, but connects **directly to Moonraker**, not through Home Assistant printer entities. The initial installation builds the container locally from pinned sources.

**Language / Idioma:** [English](#english) · [Español](#español)

> English guide first, followed by the full Spanish translation. / Guía en inglés primero, seguida de la versión completa en español.

## English

### 1. Requirements

| Requirement | Mandatory? | Details |
| --- | --- | --- |
| Home Assistant OS or Supervised | Yes | Supervisor/App Store on **amd64 (x86-64)** or **aarch64 (ARM64)** |
| A Moonraker-enabled printer | Yes | Moonraker running and reachable from the Home Assistant machine over the local network |
| Moonraker API URL | Yes | Usually **http://printer.local:7125** or **http://192.168.1.25:7125**; the Fluidd website may use a different port |
| Moonraker API key | Sometimes | Required if Moonraker rejects unauthenticated requests from Home Assistant |
| Unique MCP HTTP token | Yes | A new, random, secret value (recommend **32+ characters**) used only for this add-on |
| Internet access during installation | Yes | Supervisor builds locally and retrieves pinned dependencies; there is no prebuilt GHCR image |
| ChatGPT custom MCP/tunnel support | Only for ChatGPT | Availability depends on your account, workspace, and permissions |
| OpenAI Platform tunnel and restricted key | Only for remote ChatGPT | Use your own tunnel and restricted runtime API key |

**Not required:** running Moonraker inside Home Assistant, installing Fluidd, opening a router port, downloading a tunnel client ZIP, manually editing Docker files, or setting up Home Assistant printer entities.

### 2. Find your Moonraker API URL

1. Find the printer's IP address in its network settings or your router's DHCP list.
2. If your printer uses Fluidd, its browser address can help identify the host; **do not assume Fluidd's port is Moonraker's API port**.
3. Try **http://PRINTER_IP:7125/server/info** from a trusted device on the same network. A JSON response indicates a reachable Moonraker HTTP API; an authorization error means credentials may be needed.
4. Enter the root API address, **without /server/info**, in **moonraker_url**. For example: **http://192.168.1.25:7125**.
5. Ensure the Home Assistant host, not just your laptop, can reach that host and port. Do not expose Moonraker to the public internet.

### 3. Obtain your Moonraker API key

Moonraker has its **own** API key. It is **not** the MCP HTTP token and **not** an OpenAI API key.

**Option A — browser on a trusted/authorized client:** Open **http://PRINTER_IP:7125/access/api_key** (replace the host and port with your Moonraker API URL). If Moonraker authorizes your connection, it returns JSON with the current key under **result**. Copy that value into **moonraker_api_key** in the Home Assistant app.

**Option B — your Moonraker/Fluidd configuration:** If the browser cannot read the endpoint, check your interface's Moonraker authorization settings, or ask the printer/Moonraker administrator for the current key. Some firmware provides an SSH shell; Moonraker's official installation guide describes its **fetch-apikey.sh** script. SSH is **not required** for normal add-on installation.

**Important:** Requesting **GET /access/api_key** retrieves the existing key. **Do not call POST /access/api_key just to find it**: POST generates/replaces it and can break other clients. If Moonraker allows connections from your trusted Home Assistant address without an API key, you may leave this field blank. Never paste API keys into issues or public screenshots.

Official documentation: [Moonraker authorization endpoints](https://moonraker.readthedocs.io/en/latest/external_api/authorization/) · [Moonraker installation and key retrieval](https://moonraker.readthedocs.io/en/latest/installation/).

### 4. Install the Home Assistant app

1. Open **Settings → Apps → App Store → ⋮ → Repositories**.
2. Add **https://github.com/sergey08/homeassistant-addons** unless already present.
3. Refresh the App Store, choose **Moonraker MCP** (not **Moonraker MCP (DEV)**), and click **Install**.
4. Wait for Supervisor to build the container locally, then open the **Configuration** tab.
5. Fill in the mandatory fields, save and start with **enable_tunnel = false**.
6. Review the app **Logs** for errors before configuring ChatGPT.

### 5. Every configuration option

These are the **13 options in config.yaml**. Values shown are the initial defaults; optional capabilities are off initially.

| Home Assistant option | Default | Purpose / instructions |
| --- | --- | --- |
| **moonraker_url** | http://printer.local:7125 | **Required.** Base URL of Moonraker's HTTP API, including its real port, reachable from Home Assistant |
| **moonraker_api_key** | Empty | Moonraker authentication key; set it only if the printer's API requires one |
| **mcp_http_token** | Empty | **Required before startup.** Create a unique, high-entropy secret (recommend 32+ characters). Never reuse the Moonraker or OpenAI key |
| **enable_tunnel** | false | Enables outbound OpenAI Secure MCP Tunnel. Leave off for local-only operation |
| **tunnel_id** | Empty | Your own OpenAI Platform tunnel ID (typically **tunnel_...**); required when tunnel is enabled |
| **openai_tunnel_api_key** | Empty | **Restricted OpenAI Platform API key** with tunnel runtime permissions; required when tunnel is enabled |
| **enable_jobqueue** | false | Allows the optional **job/queue** MCP profile; increases access to printer job state/queue data |
| **enable_files** | false | Enables optional **G-code file-list, preview and metadata** tools; file names and metadata may be sensitive |
| **enable_objects** | false | Enables access to additional **Klipper objects/state** information |
| **enable_history** | false | Enables additional **print-job history** data |
| **enable_sensors** | false | Enables extra **sensor/status** information beyond the five default tools |
| **enable_spoolman** | false | Enables optional **Spoolman filament/inventory-related** functionality where available |
| **enable_power** | false | Enables optional **power-related** information/capabilities; review tool permissions before enabling |

**Security model:** the first five MCP tools are read-only. Other profiles expand the tool surface and may expose additional printer data or actions; enable them only after checking the exposed tools and their permissions. The original add-on policy keeps Moonraker administration disabled. Never assume a profile is read-only solely because its name sounds informational.

**Network:** Home Assistant lists **8765/tcp**, but it is **unpublished by default**. Keep it that way unless you deliberately configure private, authenticated local access. Never forward it on your router.

**Startup:** default **manual**. Start the app from Home Assistant after saving its configuration.

### 6. Create an OpenAI Secure MCP Tunnel (optional)

The tunnel is only needed when connecting ChatGPT/OpenAI to your private Moonraker MCP server remotely. **You do not need it to start the local app.** The tunnel client executable is bundled and automatically prepared by the add-on; no ZIP or shell commands are needed.

1. Sign in to **[OpenAI Platform — Tunnels](https://platform.openai.com/settings/organization/tunnels)** under the organization you intend to use.
2. If the tunnel creation screen says access is required, ask a Platform organization owner/RBAC administrator for **Tunnels: Read + Manage** to create/edit the tunnel.
3. Create a dedicated tunnel for this MCP server (or select an existing suitable tunnel). Associate it with the **ChatGPT workspace** that will use it, when that option is offered. Save the **tunnel ID** (usually **tunnel_...**), not the endpoint's public URL.
4. Open **[OpenAI Platform — API keys](https://platform.openai.com/settings/organization/api-keys)**. Create a **new Restricted API key** for the runtime client with the minimum required **Tunnels: Read + Use** permissions. The key and the tunnel ID are different values. Use the correct organization and role; if permission choices are unavailable, contact its administrator.
5. In **Home Assistant → Moonraker MCP → Configuration**, enter **tunnel_id** and **openai_tunnel_api_key**. Turn on **enable_tunnel**, save, and restart the add-on.
6. Read the app logs to confirm that the tunnel client starts; a successful process start is not yet proof that ChatGPT can call Moonraker.
7. In **ChatGPT → Plugins → Add custom MCP server**, select **Tunnel** under the connection options, then select or paste the same tunnel ID. Configure MCP authentication as required by the interface. In the tested private-tunnel setup, the endpoint **behind the tunnel** uses **No authentication** because the tunnel itself and the local gateway use separate credentials. Do **not** interpret that as permission to expose the endpoint publicly.
8. Verify the connection by listing the available MCP tools and making a harmless read-only call, such as checking printer connection status.

**If the tunnel is missing from ChatGPT:** ensure your account can create custom MCP connections, your ChatGPT workspace is associated with the tunnel, and its user has **Tunnels: Read + Use**. Platform and ChatGPT permissions are separate. The client needs outbound HTTPS (normally port 443) to OpenAI, but **no inbound router port**.

Official reference: [OpenAI Secure MCP Tunnel guide](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels).

### 7. Default MCP tools

| Tool | What it returns |
| --- | --- |
| **moonraker_connection_status** | Reachable, unavailable/not-ready, or authentication failure |
| **moonraker_mcp_version** | MCP bridge/upstream server version |
| **moonraker_printer_info** | Filtered Klippy state and version; no private host paths |
| **moonraker_server_info** | Filtered Moonraker and Klippy version/readiness |
| **moonraker_temperature_store** | Recent bounded temperature samples, with nonstandard sensor names anonymized |

### 8. Common problems and safety

| Symptom | What to check |
| --- | --- |
| Cannot connect to printer | Moonraker API host/port, printer/network status and authorization; Fluidd's address may differ |
| Moonraker authentication error | Existing Moonraker API key or trusted-client settings; don't regenerate the key casually |
| “Configure a nonempty MCP HTTP token” | Set **mcp_http_token** to a unique strong value and save |
| Tunnel not connecting | **enable_tunnel**, **tunnel_id**, restricted API key permissions, outbound HTTPS, and logs |
| Tunnel absent from ChatGPT | Workspace association, custom MCP access, and **Tunnels: Read + Use** |
| Printer appears offline | Could be powered off **or** unreachable; these are not equivalent |
| New stable installation next to DEV | Both are separate Home Assistant Supervisor identities; don't use the same tunnel ID in both |

**Known limits:** Encrypted restore and real tunnel-key revocation/rotation were **not independently verified**. Existing DEV configurations and secrets do **not** migrate automatically. The source is distributed through the Home Assistant repository; the Docker image is built locally, not published as a maintainer GHCR image.

---

## Español

Moonraker MCP conecta un cliente MCP compatible con OpenAI (opcionalmente ChatGPT mediante un **túnel MCP seguro —Secure MCP Tunnel—**) con la **API Moonraker** de una impresora 3D. El complemento se ejecuta en Home Assistant OS o Supervised, pero se conecta **directamente a Moonraker**, sin utilizar entidades de la impresora en Home Assistant. Durante la instalación inicial, Home Assistant compila el contenedor localmente a partir de código fuente y dependencias con versiones fijadas.

### 1. Requisitos

| Requisito | ¿Obligatorio? | Detalles |
| --- | --- | --- |
| Home Assistant OS o Supervised | Sí | Supervisor/Tienda de aplicaciones en **amd64 (x86-64)** o **aarch64 (ARM64)** |
| Impresora con Moonraker | Sí | Moonraker funcionando y accesible desde Home Assistant por la red local |
| URL de la API Moonraker | Sí | Normalmente **http://printer.local:7125** o **http://192.168.1.25:7125**. Fluidd puede utilizar otro puerto |
| Clave API de Moonraker | A veces | Necesaria cuando Moonraker no permite peticiones sin autenticar desde Home Assistant |
| Token HTTP MCP exclusivo | Sí | Contraseña secreta aleatoria nueva (**32 caracteres o más** recomendados), solo para este complemento |
| Internet durante la instalación | Sí | Supervisor compila el complemento localmente con dependencias fijadas; no distribuimos una imagen GHCR propia |
| Acceso en ChatGPT a MCP y túneles | Solo para ChatGPT | Depende del plan, la cuenta y los permisos del espacio de trabajo |
| Túnel y API restringida de OpenAI | Solo para ChatGPT remoto | Identificador de túnel propio y clave de ejecución con permisos mínimos |

**No hace falta:** instalar Moonraker dentro de Home Assistant, usar Fluidd obligatoriamente, abrir puertos del router, instalar manualmente binarios ni crear entidades de la impresora en Home Assistant.

### 2. Localizar la URL de Moonraker

1. Busca la dirección IP de la impresora en su configuración de red o en el listado DHCP del router.
2. Si utilizas Fluidd, su dirección web puede indicar la IP, pero **su puerto puede ser diferente del puerto de la API Moonraker**.
3. Desde un equipo autorizado en la misma red, prueba **http://IP_IMPRESORA:7125/server/info**. Si devuelve JSON, estás llegando a Moonraker; si devuelve un error de autorización, quizá necesites la clave.
4. En el campo **moonraker_url** introduce solo la dirección base: **http://192.168.1.25:7125**, **sin /server/info**.
5. Comprueba que el equipo de Home Assistant puede acceder a esa IP y puerto. No publiques la API de Moonraker en Internet.

### 3. Cómo obtener la clave API de Moonraker

La clave de Moonraker es distinta del **mcp_http_token** y de la clave de OpenAI.

**Opción A — navegador desde un cliente autorizado:** Abre **http://IP_IMPRESORA:7125/access/api_key** (con la IP y el puerto reales). Si Moonraker reconoce la conexión, devolverá un objeto JSON con la clave actual dentro de **result**. Copia ese valor al campo **moonraker_api_key** del complemento.

**Opción B — configuración Moonraker/Fluidd:** si el navegador no está autorizado, revisa la configuración de autorización de Moonraker, o pide la clave al administrador de la impresora. Algunas instalaciones permiten consultar la clave por SSH mediante el script oficial **fetch-apikey.sh**. No hace falta SSH para la instalación normal del complemento.

**Cuidado:** **GET /access/api_key** consulta la clave existente. **No utilices POST /access/api_key para consultarla**, ya que genera una nueva y puede invalidar clientes configurados. Si Home Assistant se considera un cliente de confianza y Moonraker no exige clave, puedes dejarla vacía.

Documentación: [autenticación de Moonraker](https://moonraker.readthedocs.io/en/latest/external_api/authorization/) · [cómo recuperar la clave](https://moonraker.readthedocs.io/en/latest/installation/).

### 4. Instalación en Home Assistant

1. Abre **Ajustes → Aplicaciones → Tienda de aplicaciones → ⋮ → Repositorios**.
2. Añade **https://github.com/sergey08/homeassistant-addons** si todavía no está incluido.
3. Actualiza la tienda, selecciona **Moonraker MCP** (**sin DEV**) y pulsa **Instalar**.
4. Home Assistant construirá el contenedor localmente; abre después **Configuración**.
5. Introduce los campos obligatorios, guarda e inicia con **enable_tunnel = false**.
6. Revisa **Registros** antes de configurar la conexión con ChatGPT.

### 5. Explicación de todas las opciones de configuración

Estas son las **13 opciones reales de config.yaml**:

| Opción de Home Assistant | Valor inicial | Explicación |
| --- | --- | --- |
| **moonraker_url** | http://printer.local:7125 | **Obligatoria**: URL base de la API Moonraker, con su puerto real y accesible desde Home Assistant |
| **moonraker_api_key** | Vacío | Clave API de Moonraker, únicamente si la impresora la exige |
| **mcp_http_token** | Vacío | **Obligatorio antes de arrancar**: genera una contraseña/token aleatorio único (32+ caracteres recomendados). No reutilices otras claves |
| **enable_tunnel** | false | Activa la conexión privada saliente con OpenAI. Déjalo desactivado si no usas ChatGPT |
| **tunnel_id** | Vacío | Identificador de tu túnel de OpenAI Platform (normalmente **tunnel_...**); requerido al activar el túnel |
| **openai_tunnel_api_key** | Vacío | **API key Restricted de OpenAI Platform** con permisos de ejecución del túnel; requerida con el túnel |
| **enable_jobqueue** | false | Habilita el perfil opcional de **trabajos y cola** de impresión, con mayor acceso a los estados de trabajos |
| **enable_files** | false | Habilita funciones de **listado, vista previa y metadatos de archivos G-code**. Pueden revelar nombres y detalles |
| **enable_objects** | false | Permite consultar información adicional de **objetos y estados de Klipper** |
| **enable_history** | false | Habilita datos adicionales del **historial de impresión** |
| **enable_sensors** | false | Permite consultar **sensores y estados** adicionales a los cinco métodos básicos |
| **enable_spoolman** | false | Habilita la funcionalidad opcional de **bobinas, filamentos e inventario Spoolman**, cuando está disponible |
| **enable_power** | false | Habilita el perfil opcional relativo a **energía/alimentación**; comprueba los permisos concretos antes de activarlo |

**Seguridad:** las cinco herramientas predeterminadas son de lectura. Las opciones adicionales amplían el acceso a datos y posiblemente a operaciones: comprueba qué herramientas se exponen y sus permisos antes de activarlas. La administración Moonraker está deshabilitada por defecto.

**Red:** el puerto **8765/tcp** figura en el complemento, pero **no se publica inicialmente**. No lo abras al exterior ni lo redirijas en el router.

**Arranque:** el complemento viene con arranque **manual**. Inícialo tras guardar la configuración.

### 6. Crear el túnel seguro de OpenAI paso a paso (opcional)

El túnel sirve para que ChatGPT acceda al MCP privado sin exponer tu red. **No es necesario para utilizar el complemento localmente**. El cliente de túnel ya está incluido y se prepara automáticamente; no hay que descargar ZIP ni utilizar el terminal.

1. Entra con tu cuenta en **[OpenAI Platform — Túneles](https://platform.openai.com/settings/organization/tunnels)** y elige la organización adecuada.
2. Para crear o modificar un túnel necesitas los permisos **Tunnels: Read + Manage**. Si no aparecen, debe concederlos el propietario/administrador de la organización.
3. Crea un túnel dedicado a la impresora o selecciona uno ya disponible. Cuando proceda, **asócialo al espacio de trabajo de ChatGPT** desde el que quieras usarlo.
4. Copia su identificador **tunnel_...**. Este ID **no es** la contraseña de OpenAI ni la URL pública.
5. Abre **[OpenAI Platform — Claves API](https://platform.openai.com/settings/organization/api-keys)** y crea una clave nueva **Restricted** con los permisos mínimos **Tunnels: Read + Use** para ejecutar el cliente. La clave y el identificador del túnel son valores independientes.
6. En **Home Assistant → Moonraker MCP → Configuración**, introduce los valores en **tunnel_id** y **openai_tunnel_api_key**, activa **enable_tunnel**, guarda y reinicia.
7. Comprueba en **Registros** que se inicia el cliente del túnel. Que arranque no garantiza por sí solo que ChatGPT pueda consultar la impresora.
8. En **ChatGPT → Complementos → Añadir servidor MCP personalizado**, selecciona **Túnel**, elige o introduce el mismo ID y configura la autenticación que solicite la interfaz. En la configuración de túnel privado probada, el endpoint **detrás del túnel** utiliza **Sin autenticación**, porque el túnel y el gateway local tienen credenciales independientes. Esto **no significa** que debas publicar el puerto MCP.
9. Confirma que ChatGPT encuentra las herramientas y ejecuta una consulta inocua, por ejemplo comprobar la conexión de la impresora.

**Si no aparece el túnel en ChatGPT:** revisa la disponibilidad de MCP personalizados en tu cuenta, que el túnel esté asociado al espacio de trabajo correspondiente y los permisos **Tunnels: Read + Use**. Los permisos de OpenAI Platform y los del espacio de ChatGPT son independientes. Solo necesita tráfico **HTTPS saliente por 443**; no necesita abrir puertos entrantes en el router.

Documentación oficial: [OpenAI Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels).

### 7. Las cinco herramientas incluidas

| Herramienta | Qué hace |
| --- | --- |
| **moonraker_connection_status** | Estado de conexión, no disponible/no preparado o error de autenticación |
| **moonraker_mcp_version** | Versión del servidor MCP |
| **moonraker_printer_info** | Estado y versión de Klippy con filtrado de datos internos |
| **moonraker_server_info** | Estado y versiones de Moonraker/Klippy, filtrados |
| **moonraker_temperature_store** | Muestras recientes y limitadas de temperaturas, con nombres personalizados anonimizados |

### 8. Solución de problemas y límites

| Síntoma | Qué comprobar |
| --- | --- |
| No conecta con la impresora | Dirección y puerto de Moonraker, red, estado de la impresora y autorización |
| Error de autenticación Moonraker | Clave actual y clientes de confianza; no generes otra clave sin necesidad |
| «Configure a nonempty MCP HTTP token» | Introduce y guarda un valor exclusivo en **mcp_http_token** |
| El túnel no conecta | **enable_tunnel**, **tunnel_id**, permisos de la API restringida, HTTPS saliente y registros |
| El túnel no aparece en ChatGPT | Asociación del espacio de trabajo, acceso a MCP y permisos **Tunnels: Read + Use** |
| La impresora está «offline» | Podría estar apagada o inaccesible por red; no se puede distinguir sin más información |
| Estable y DEV instalados | Son identidades Supervisor distintas: no reutilices el mismo ID de túnel simultáneamente |

**Limitaciones conocidas:** todavía no se han verificado de extremo a extremo la restauración de copias cifradas y la revocación/rotación de credenciales. La configuración y los secretos de DEV **no migran automáticamente** a estable. Se distribuye código fuente y Home Assistant compila localmente su contenedor.

---

## Project documentation / Documentación del proyecto

- [Quick start / Inicio rápido](./QUICK_START_EN_ES.md)
- [Installation details / Instalación detallada](./INSTALLATION_EN_ES.md)
- [Third-party notices / Avisos de terceros](./THIRD_PARTY_NOTICES_EN_ES.md)
- [Source access / Acceso a código fuente](./THIRD_PARTY_SOURCE_ACCESS_EN_ES.md)
- [v0.1.0 release notes / Notas de versión](./RELEASE_NOTES_0.1.0_EN_ES.md)

The repository's original code is MIT-licensed; third-party components retain their own licenses. / El código original del repositorio es MIT; los componentes externos conservan sus licencias.
