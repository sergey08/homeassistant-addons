# Nod for Home Assistant

## English

### Development status

This branch evaluates a native Home Assistant OS app for Nod on amd64. There is no installable beta yet.

### Upstream architecture

The [Nod server distribution](https://nod.n8n.io/docs/deploy/self-host/) uses separate containers for the server, PostgreSQL, browser, workspace, workspace firewall, and runtime proxy. The reviewed [Compose file](https://github.com/n8n-io/nod/blob/main/deployment/self-host/compose.yaml) has blob SHA `bddc4fb6f0bb42cd314589f8cd900a61648f1bb6`. The runtime proxy mounts the host Docker socket. The workspace uses the firewall container's network namespace. Both are part of the operational design.

### Prototype scope

First evaluate running the upstream stack behind an isolated container engine on a disposable HA OS amd64 system. Verify whether this can start with Supervisor protection enabled, without host Docker access or access to HA files. Preserve Nod's service and network boundaries. If the isolation test fails, keep the upstream stack in a separate Linux guest and treat integration with HA as a separate design decision.

Test direct private HTTPS first. [Home Assistant Ingress](https://contributors.home-assistant.io/apps/guides/ingress/) serves a prefixed URL and [Nod requires an HTTPS origin without a path](https://nod.n8n.io/docs/deploy/configuration/) for remote access. Verify assets, session and callback behavior before enabling Ingress.

### Model connection: ChatGPT subscription

The primary beta acceptance target is the upstream OpenAI / ChatGPT sign-in using an existing ChatGPT Plus account, not an API key. Follow [upstream model setup](https://nod.n8n.io/docs/connect/models/). Do not collect or log OAuth tokens, passwords or callback URLs containing credentials. The owner completes sign-in in the official browser flow. Test model availability, a harmless chat, restart persistence and scheduled execution within the subscription limits. Do not claim access or zero additional charges until the actual connection has been verified. Use the documented private access mechanism before attempting Ingress.

The next engineering gate is the VM disk probe on actual HA, followed by guest networking with no host Docker socket, host filesystem mounts or inbound public exposure. Upstream recommends two cores, 8 GB RAM and 50 GB disk as a starting point; measure available resources before provisioning the full guest.

### Beta acceptance

1. Install and start from the app repository on an HA OS amd64 test instance. Check startup without host Docker or HA file mounts.
2. Complete onboarding with a test model connection, open a public test page from Nod, and verify the workspace cannot connect to a test HTTP listener on the private network.
3. Restart the app and verify history and configuration persist. Verify backup and restore, including the original credential encryption key.
4. Measure memory and CPU during a browser task before testing alongside Frigate on the Lenovo. Obtain real HA validation before preparing a stable release.

## Español

### Estado del desarrollo

Esta rama estudia una aplicación nativa de Nod para Home Assistant OS en amd64. La beta instalable está pendiente.

### Arquitectura original

La [distribución de servidor de Nod](https://nod.n8n.io/docs/deploy/self-host/) separa el servidor, PostgreSQL, navegador, entorno de trabajo, cortafuegos y proxy de ejecución en contenedores. Se revisó el [Compose original](https://github.com/n8n-io/nod/blob/main/deployment/self-host/compose.yaml), con SHA de blob `bddc4fb6f0bb42cd314589f8cd900a61648f1bb6`. El proxy de ejecución monta el socket de Docker del host. El entorno de trabajo comparte el espacio de red del cortafuegos. Ambos forman parte del diseño operativo.

### Alcance del prototipo

Evaluar primero si el conjunto original puede arrancar con un motor de contenedores aislado dentro de un HA OS amd64 desechable. Comprobar si funciona con la protección del Supervisor activa, sin acceso al Docker del host ni a los archivos de HA. Conservar la separación entre servicios y redes de Nod. Si la prueba de aislamiento falla, mantener el conjunto original en una máquina virtual Linux separada y decidir aparte cómo integrarlo con HA.

Probar primero el acceso privado por HTTPS. [Ingress de Home Assistant](https://contributors.home-assistant.io/apps/guides/ingress/) sirve la aplicación bajo una ruta, y [Nod exige un origen HTTPS sin ruta](https://nod.n8n.io/docs/deploy/configuration/) para el acceso remoto. Verificar carga de recursos, sesión y retornos de autenticación antes de activar Ingress.

### Conexión del modelo: suscripción ChatGPT

El objetivo prioritario de la beta es iniciar sesión con una cuenta ChatGPT Plus existente mediante la opción original OpenAI / ChatGPT, sin clave API. Seguir la [configuración oficial](https://nod.n8n.io/docs/connect/models/). No recopilar ni registrar tokens OAuth, contraseñas ni URL de retorno con credenciales. El propietario completa la autenticación en el navegador oficial. Comprobar modelos disponibles, una conversación inocua, persistencia tras reinicio y ejecución programada dentro de los límites de la suscripción. No garantizar acceso ni ausencia de cargos adicionales sin validar la conexión real. Utilizar el acceso privado documentado antes de probar Ingress.

La siguiente fase técnica es comprobar el disco de la VM en HA real y después la red del invitado sin socket Docker del host, montajes de sus archivos ni exposición pública entrante. El proyecto original recomienda dos núcleos, 8 GB de RAM y 50 GB de disco como punto de partida; medir recursos disponibles antes de aprovisionar el invitado completo.

### Criterios de aceptación de la beta

1. Instalar y arrancar desde el repositorio de aplicaciones en una instancia HA OS amd64 de pruebas. Verificar el arranque sin montajes del Docker del host ni de archivos de HA.
2. Completar la configuración con una conexión de modelo de pruebas, abrir una página pública de prueba desde Nod y comprobar que el entorno de trabajo no puede conectar con un servidor HTTP de prueba en la red privada.
3. Reiniciar la aplicación y comprobar que conserva el historial y la configuración. Verificar copia y restauración, incluida la clave original de cifrado de credenciales.
4. Medir memoria y CPU durante una tarea de navegador antes de probar junto a Frigate en el Lenovo. Obtener una validación real en HA antes de preparar la versión estable.
