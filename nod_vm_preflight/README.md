# Nod VM preflight

## English

Version 0.1.0-dev.5 additionally boots a disposable Debian guest with 2 GiB RAM, two virtual CPUs and an ephemeral 3 GiB disk, starts its own Docker daemon with networking disabled, and runs a locally imported BusyBox container. This is an offline engine test, not Nod or persistent guest storage.

Version 0.1.0-dev.4 adds a TLS-verified DNS-over-HTTPS query for example.com via a fixed TCP relay to 1.1.1.1:443. QEMU remains restricted; no general Internet or LAN access is enabled. Offline CI checks disk and gateway only; real HA must report NOD_VM_DOH_HTTPS_OK twice and PASS.

Version 0.1.0-dev.3 boots a minimal QEMU Linux guest (one virtual CPU, 256 MiB RAM), checks the persistent 8 MiB disk across two boots, and tests the restricted virtual gateway at 10.0.2.2. QEMU user networking uses restrict=on without port forwarding. No host Docker socket, host devices or other app data are mounted. This is not an Internet, DNS, HTTPS or full security test. Start manually with Supervisor protection enabled, check the PASS marker in the logs, then stop the app. Nod itself is not included.

## Español

La versión 0.1.0-dev.5 arranca además un invitado Debian desechable de 2 GiB de RAM, dos CPU virtuales y disco temporal de 3 GiB, inicia su Docker interno sin red y ejecuta un contenedor BusyBox importado localmente. Es una prueba del motor sin red, no de Nod ni del almacenamiento persistente del invitado.

La versión 0.1.0-dev.4 añade una consulta DNS sobre HTTPS de example.com con validación TLS mediante un relé TCP fijo a 1.1.1.1:443. QEMU sigue restringido; no habilita acceso general a Internet ni a la LAN. CI sin red comprueba disco y puerta de enlace; HA real debe mostrar NOD_VM_DOH_HTTPS_OK dos veces y PASS.

La versión 0.1.0-dev.3 arranca un Linux mínimo en QEMU (una CPU virtual, 256 MiB de RAM), comprueba el disco persistente de 8 MiB en dos arranques y prueba la puerta de enlace virtual restringida 10.0.2.2. La red de usuario de QEMU usa restrict=on sin redirección de puertos. No monta el socket Docker, dispositivos del host ni datos de otras aplicaciones. No constituye una prueba de Internet, DNS, HTTPS ni de seguridad completa. Iniciar manualmente con la protección del Supervisor activa, comprobar la marca PASS en el registro y detener la aplicación. Todavía no incluye Nod.
