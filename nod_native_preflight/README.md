# Nod native preflight

Experimental amd64-only Home Assistant app. It compiles upstream Nod at revision `6670bc233b6b7dddaa75b25b89b4a89f0e92bcac` and checks its authenticated health endpoint against PostgreSQL 17. Both services listen only on loopback, run as separate unprivileged users and remain running after the health check. Version dev.2 stores data and generated credentials under the app's private `/data/nod-native-v1` directory. CI checks database and key persistence across container replacement. Dev.3 adds a read-only Ingress status page, not the original Nod UI. Only the Supervisor ingress source 172.30.32.2 is accepted. No mapped ports, host Docker socket, additional permissions, browser or workspace. Not a usable agent yet. Upstream Nod is Apache-2.0 licensed by n8n GmbH; its license is included in the image.

## Español

Aplicación experimental amd64. Arranque nativo de Nod y PostgreSQL 17 con usuarios separados, sin QEMU, KVM, socket Docker del host, permisos adicionales ni puertos publicados. La dev.2 conserva datos y claves en el almacenamiento privado de la aplicación y mantiene los servicios arrancados después de comprobar su salud. La dev.3 añade un panel de estado de solo lectura mediante Ingress; no es la interfaz original de Nod. Todavía faltan la interfaz del agente, navegador, espacio de trabajo y conexiones.
