# Moonraker MCP for Home Assistant

**Version 0.1.3 · AMD64 and ARM64 · Read-only MCP bridge by default**

Moonraker MCP connects an OpenAI-compatible MCP client (optionally ChatGPT through a **Secure MCP Tunnel**) to a 3D printer's **Moonraker API**. The app runs in Home Assistant OS / Supervised, but connects **directly to Moonraker**, not through Home Assistant printer entities. The initial installation builds the container locally from pinned sources.

**Language / Idioma:** [English](#english) · [Español](#español)

> English guide first, followed by the full Spanish translation. / Guía en inglés primero, seguida de la versión completa en español.

## English

### What can you do with Moonraker MCP?

Once connected to ChatGPT (or another compatible MCP client), you can ask natural-language questions about your 3D printer instead of opening separate technical screens. **Examples supported by the five default read-only tools:**

| Example question | What the MCP can check |
| --- | --- |
| **“Is my 3D printer online?”** | Whether the Moonraker API is reachable and Klippy appears ready |
| **“Is Klipper ready, or is there a connection problem?”** | Filtered Klippy and Moonraker connection/readiness states |
| **“Which Moonraker and Klipper versions are running?”** | Available software/firmware version information |
| **“What are the latest recorded nozzle and bed temperatures?”** | Available sensor history, including measured and target values |
| **“Can you review the recent temperature readings and tell me if they look stable?”** | Up to 120 stored samples per sensor series; any assessment depends on the actual data returned |
| **“What version of the Moonraker MCP server am I using?”** | MCP server version |

**Optional extended profiles** can expose additional information such as G-code file names/metadata, job history, Klipper objects, other sensors, Spoolman inventory or power-related data. Those questions **only work when the corresponding profile is enabled and its tool is actually available**.

**Not supported by the default profile:** starting/stopping prints, sending G-code, deleting files, turning the printer on/off, or directly commanding the machine. Also, **“offline” does not prove it is powered off**—it may be a network problem. The default tools do not provide reliable current print progress, a live camera image or a finished-print notification.

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

**Security model:** the seven optional profiles in this version are restricted by an explicit allowlist to **read-only tools**. They expand the information visible to your MCP client, but do not authorize starting/stopping jobs, deleting files, sending G-code or switching power. They may disclose filenames, print history, spool information, sensor values and printer configuration; enable only the profiles you actually want to share.

**Example questions with optional profiles enabled:**

| Profile | Enabled tools (when supported by the Moonraker server) | Example question |
| --- | --- | --- |
| **Job queue** | `moonraker_jobqueue_status` | “Are there any jobs waiting in the queue?” |
| **G-code files** | `moonraker_files_list`, `moonraker_files_metadata`, `moonraker_files_preview` | “List my G-code files and show the metadata of one model.” |
| **Klipper objects** | `moonraker_objects_list`, `moonraker_objects_query` | “What Klipper objects are available, and what is the current state?” |
| **History** | `moonraker_history_list`, `moonraker_history_job`, `moonraker_history_totals` | “Show recent print jobs and the available history totals.” |
| **Sensors** | `moonraker_sensors_info`, `moonraker_sensors_list`, `moonraker_sensors_measurements` | “Which additional sensors report measurements?” |
| **Spoolman** | `moonraker_spoolman_status`, `moonraker_spoolman_get_spool`, `moonraker_spoolman_inventory` (v0.1.1 candidate) | “List my filament spools and show the remaining grams of PLA.” |
| **Power status** | `moonraker_power_status` | “What is the current state of Moonraker-managed power devices?” |

**Spoolman inventory (v0.1.1):** the new `moonraker_spoolman_inventory` tool uses Moonraker's fixed, read-only Spoolman proxy to list up to 100 spools. It returns sanitized spool ID, manufacturer, material, color, archived state, and remaining/used weight when available. It does not modify filament stock or use arbitrary proxy requests. **Moonraker must have a working [spoolman] integration**; having a separate Spoolman app in Home Assistant alone is not enough. Upgrade the Home Assistant add-on to v0.1.1 to use this inventory tool.

An enabled profile **does not guarantee the tools exist** in your Moonraker server: the gateway only exposes tools implemented by the configured upstream. The power profile checks status; **it cannot turn anything on or off**.

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

### ¿Qué puedes hacer con Moonraker MCP?

Una vez conectado a ChatGPT (o a otro cliente MCP compatible), puedes hacer preguntas en lenguaje natural sobre tu impresora 3D sin consultar varias pantallas técnicas. **Ejemplos compatibles con las cinco herramientas de lectura activadas por defecto:**

| Ejemplo de pregunta | Qué puede comprobar el MCP |
| --- | --- |
| **«¿Está conectada mi impresora 3D?»** | Si la API Moonraker responde y Klippy está preparado |
| **«¿Está Klipper listo o hay algún problema de conexión?»** | Estados filtrados de conexión y disponibilidad de Klippy/Moonraker |
| **«¿Qué versiones de Moonraker y Klipper tengo instaladas?»** | Versiones de software y firmware disponibles |
| **«¿Cuáles son las últimas temperaturas registradas del extrusor y de la cama?»** | Historial disponible de sensores, valores reales y objetivos |
| **«Analiza las últimas temperaturas y dime si parecen estables»** | Hasta 120 muestras almacenadas por serie; la valoración depende de los datos reales |
| **«¿Qué versión del servidor Moonraker MCP estoy utilizando?»** | Versión del servidor MCP |

Las **funciones ampliadas opcionales** pueden dar acceso a nombres y metadatos de archivos G-code, historial de trabajos, objetos Klipper, otros sensores, inventario Spoolman o información de energía. Esas preguntas **solo funcionarán si se activa el perfil correspondiente y la herramienta está realmente disponible**.

**El perfil inicial no permite** iniciar o detener impresiones, enviar G-code, borrar archivos, encender/apagar la impresora ni ejecutar órdenes directas. Además, **que aparezca «sin conexión» no demuestra que esté apagada**: también puede fallar la red. Las herramientas básicas no ofrecen por sí solas el progreso actual de una impresión, vídeo de cámara en directo ni notificaciones de fin de impresión.

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

**Seguridad:** los siete perfiles opcionales de esta versión están limitados mediante una lista explícita a herramientas **de solo lectura**. Amplían la información que ChatGPT puede consultar, pero no permiten iniciar o detener trabajos, borrar archivos, ejecutar G-code ni activar enchufes. Pueden mostrar nombres de ficheros, historial, bobinas, sensores y datos técnicos de la impresora; activa solo los perfiles cuya información quieras compartir.

**Ejemplos de preguntas con las opciones adicionales activadas:**

| Perfil | Herramientas habilitadas (si Moonraker las ofrece) | Ejemplo de pregunta |
| --- | --- | --- |
| **Cola de impresión** | `moonraker_jobqueue_status` | «¿Tengo impresiones pendientes en la cola?» |
| **Archivos G-code** | `moonraker_files_list`, `moonraker_files_metadata`, `moonraker_files_preview` | «Enséñame los archivos G-code y los metadatos de uno de ellos» |
| **Objetos Klipper** | `moonraker_objects_list`, `moonraker_objects_query` | «¿Qué objetos Klipper hay disponibles y cuál es su estado?» |
| **Historial** | `moonraker_history_list`, `moonraker_history_job`, `moonraker_history_totals` | «Muéstrame las últimas impresiones y las estadísticas del historial» |
| **Sensores** | `moonraker_sensors_info`, `moonraker_sensors_list`, `moonraker_sensors_measurements` | «¿Qué sensores adicionales tiene la impresora?» |
| **Spoolman** | `moonraker_spoolman_status`, `moonraker_spoolman_get_spool`, `moonraker_spoolman_inventory` (candidata 0.1.1) | «¿Qué bobinas tengo y cuántos gramos de PLA me quedan?» |
| **Estado eléctrico** | `moonraker_power_status` | «¿Qué estado tienen los dispositivos de alimentación de Moonraker?» |

**Inventario Spoolman (0.1.1):** la nueva herramienta `moonraker_spoolman_inventory` usa el proxy de Spoolman de Moonraker con una operación interna **GET de solo lectura**, sin permitir llamadas arbitrarias. Consulta hasta 100 bobinas y devuelve identificador, marca, material, color, si están archivadas y gramos restantes/consumidos cuando existan. No modifica inventario ni consumo. **Moonraker debe tener configurada y funcionando su integración [spoolman]**; tener únicamente el complemento Spoolman instalado en Home Assistant no garantiza el acceso desde Moonraker. Actualiza el complemento Home Assistant a la 0.1.1 para usar esta herramienta.

Que un perfil esté activado **no garantiza que esas herramientas existan** en el servidor Moonraker: solo aparecerán las implementadas por la conexión real. El perfil eléctrico consulta el estado; **no puede encender ni apagar dispositivos**.

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


---

### New in 0.1.2 — live Snapmaker U1 status (candidate)

**English:** The development branch adds an **opt-in, read-only** `enable_u1_status` option with `moonraker_print_snapshot` and `moonraker_filament_slots`. It queries fixed Klipper objects via Moonraker (not Home Assistant entities). Print data includes state, job filename, current/total layers, active tool T0–T3, durations and **separate** UI/file progress values; no speculative ETA is returned. The filament snapshot reports sanitized material, vendor and color per T0–T3. NFC UID and other private tag fields are never returned. Moonraker's single active Spoolman spool ID is **not** assumed to correspond to four separate slot IDs.

**Español:** La rama de desarrollo incorpora la opción **de solo lectura y desactivada por defecto** `enable_u1_status`, con las herramientas `moonraker_print_snapshot` y `moonraker_filament_slots`. Consulta objetos Klipper directamente mediante Moonraker, sin depender de entidades de Home Assistant. Informa de estado, archivo, capas, cabezal T0–T3, duraciones y **dos porcentajes de progreso diferenciados**; no inventa una hora de finalización. Para cada posición T0–T3, devuelve material, fabricante y color, eliminando identificadores NFC privados. El identificador único de bobina activa de Spoolman **no equivale** a un mapa demostrado de las cuatro posiciones.

**Write permissions / Permisos de escritura:** pause/resume, start/cancel, file changes and power controls are **not implemented in this stage**. Each future action must be separately authorized and reviewed against safe printer states; all write profiles will default to off. No printing commands are used by this development work.


### New in 0.1.2 — separately controlled print actions (candidate)

**English:** Four independent opt-in flags, all **false** by default: `allow_print_pause`, `allow_print_resume`, `allow_print_cancel` and `allow_print_start`. Each exposes exactly one MCP action. All actions require explicit human approval in the client and a literal `CONFIRM_*` argument. Immediately before any write request, the gateway checks Klipper is ready and checks the live print state. Cancel also checks the exact current G-code filename; start validates the filename and refuses to start if another job is active. Only the official Moonraker print endpoints are used. No raw G-code, arbitrary URLs, file uploads, deletions, or power control are authorized. An API acceptance is **not** proof that the physical action completed; check the read-only status again. **Important:** the literal confirmation argument is a guard against accidental calls, not proof of human consent; the MCP client must explicitly ask the user for approval for each physical action. Treat write tools as experimental until tested on the target printer. These functions have **not yet been used on a real printer**.

**Español:** Cuatro permisos independientes, **desactivados por defecto**: `allow_print_pause`, `allow_print_resume`, `allow_print_cancel` y `allow_print_start`. Cada permiso habilita una sola herramienta MCP. Toda operación necesita aprobación expresa de la persona desde el cliente y el argumento `CONFIRM_*`. Antes de enviar una orden se verifica que Klipper esté preparado y que el estado actual de impresión permita esa operación. La cancelación exige que coincida exactamente el nombre del G-code en curso; el inicio comprueba el archivo y rechaza comenzar si ya se está imprimiendo. Solo se utilizan los endpoints oficiales de Moonraker; no se concede acceso a G-code arbitrario, URLs, borrado o subida de archivos ni alimentación eléctrica. Que Moonraker acepte la petición **no garantiza** que el movimiento físico haya terminado: hay que volver a consultar el estado. Estas funciones **aún no se han probado con órdenes reales sobre una impresora**.

**Release gate / Requisito de publicación:** pass CI and a dedicated security review before merging; never enable write flags in an update automatically. / Superar la CI y la revisión de seguridad antes de fusionar; no activar nunca automáticamente los permisos de escritura.


### Version 0.1.3 — master write safety switch

**English:** A new top-level `enable_write_actions` master switch defaults to **OFF**. All four physical print-control permissions remain separately OFF by default and **both** the master switch and the relevant per-action switch must be ON before the MCP gateway exposes a write tool. With the master switch OFF, even an accidentally enabled individual permission cannot expose physical controls. This is an authorization *configuration safeguard*, not proof of human approval for any operation. No changes are made to the currently installed v0.1.2 until a separate release is validated and approved.

**Español:** Se incorpora un interruptor general `enable_write_actions`, **desactivado por defecto**. Los cuatro permisos individuales de control físico siguen apagados inicialmente, y para exponer cualquier herramienta de escritura deben estar activados **tanto el permiso general como el específico**. Aunque se active accidentalmente un permiso individual, el MCP no permitirá acciones físicas mientras el interruptor general permanezca apagado. Esta barrera de configuración **no sustituye la aprobación humana expresa** antes de operar la impresora. La estable 0.1.2 instalada no se modifica hasta que se valide y apruebe una nueva versión.
