# Nod native preflight

Experimental amd64-only Home Assistant app. It compiles upstream Nod at revision `6670bc233b6b7dddaa75b25b89b4a89f0e92bcac` and checks its authenticated health endpoint against PostgreSQL 17. Both services listen only on loopback, run as separate unprivileged users, use disposable data and generated secrets, and stop after the probe. No ingress, mapped ports, host Docker socket, additional permissions, browser or workspace. Not a usable agent yet. Upstream Nod is Apache-2.0 licensed by n8n GmbH; its license is included in the image.

## Español

Aplicación experimental amd64. Comprueba el arranque nativo del servidor original y PostgreSQL 17, con usuarios separados y sin QEMU, KVM, socket Docker del host, permisos adicionales ni puertos publicados. Datos y credenciales de prueba desechables; los servicios se detienen al terminar. Todavía no es un agente funcional.
