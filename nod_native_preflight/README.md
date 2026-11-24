# Nod native preflight

Experimental amd64-only Home Assistant app. It compiles upstream Nod at revision `6670bc233b6b7dddaa75b25b89b4a89f0e92bcac` and checks its authenticated health endpoint against PostgreSQL 17. Both services listen only on loopback, run as separate unprivileged users and remain running after the health check. Version dev.2 stores data and generated credentials under the app's private `/data/nod-native-v1` directory. CI checks database and key persistence across container replacement. No ingress, mapped ports, host Docker socket, additional permissions, browser or workspace. Not a usable agent yet. Upstream Nod is Apache-2.0 licensed by n8n GmbH; its license is included in the image.

## Español

Aplicación experimental amd64. Arranque nativo de Nod y PostgreSQL 17 con usuarios separados, sin QEMU, KVM, socket Docker del host, permisos adicionales ni puertos publicados. La dev.2 conserva datos y claves en el almacenamiento privado de la aplicación y mantiene los servicios arrancados después de comprobar su salud. Todavía no es un agente funcional: faltan acceso web, navegador, espacio de trabajo y conexiones.
