# Nod isolation preflight

## English

Experimental amd64 app for a disposable Home Assistant OS instance. Start the app manually with Supervisor protection enabled and read its log. Stop it after the probe completes. No model, credentials, external service, or port is required. Tests the ability of a non-root process to create a private network namespace and apply IPv4 firewall rules inside it. A pass is a prerequisite check only. A failure applies to this unprivileged approach. This app does not run Nod.

## Español

Aplicación experimental amd64 para una instancia desechable de Home Assistant OS. Iníciala manualmente con la protección del Supervisor activa y consulta el registro. Detén la aplicación tras la prueba. No requiere modelo, credenciales, servicios externos ni puertos. Comprueba si un proceso sin privilegios puede crear un espacio de red privado y aplicar reglas IPv4 dentro de él. Un resultado correcto solo acredita este requisito previo. Un fallo se refiere a este enfoque sin privilegios. Esta aplicación solo ejecuta el diagnóstico.
