# Nod isolation preflight

## English

Experimental amd64 app for a disposable Home Assistant OS instance. Start the app manually with Supervisor protection enabled and read its log. Stop it after the probe completes. No model, credentials, external service, or port is required. Tests the ability of a non-root process to create a private network namespace and apply IPv4 firewall rules inside it. A pass is a prerequisite check only. A failure applies to this unprivileged approach. This app does not run Nod.

[GitHub Actions smoke test](https://github.com/sergey08/homeassistant-addons/actions/runs/45277927273/job/138054450795): the image built and the probe ran. Docker on the runner denied `unshare` with `Operation not permitted`. This result applies only to that runner.

The Lenovo passed the network namespace and IPv4 firewall check with Supervisor protection enabled on 24 November 2026. Version 0.1.0-dev.2 additionally attempts to launch a local offline OCI fixture with rootless Podman. A pass only validates basic container startup.

## Español

Aplicación experimental amd64 para una instancia desechable de Home Assistant OS. Iníciala manualmente con la protección del Supervisor activa y consulta el registro. Detén la aplicación tras la prueba. No requiere modelo, credenciales, servicios externos ni puertos. Comprueba si un proceso sin privilegios puede crear un espacio de red privado y aplicar reglas IPv4 dentro de él. Un resultado correcto solo acredita este requisito previo. Un fallo se refiere a este enfoque sin privilegios. Esta aplicación solo ejecuta el diagnóstico.

[Prueba de GitHub Actions](https://github.com/sergey08/homeassistant-addons/actions/runs/45277927273/job/138054450795): la imagen se compiló y el diagnóstico se ejecutó. Docker en el runner denegó `unshare` con `Operation not permitted`. El resultado corresponde a ese runner y corresponde únicamente al runner.

El Lenovo superó la prueba de espacio de red y cortafuegos IPv4 con la protección del Supervisor activa el 24 de noviembre de 2026. La versión 0.1.0-dev.2 también intenta arrancar un contenedor OCI local sin red mediante Podman sin privilegios. Un resultado correcto solo acredita el arranque básico del contenedor.
