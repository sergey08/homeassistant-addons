# Nod VM preflight

## English

Version 0.1.0-dev.3 boots a minimal QEMU Linux guest (one virtual CPU, 256 MiB RAM), checks the persistent 8 MiB disk across two boots, and tests the restricted virtual gateway at 10.0.2.2. QEMU user networking uses restrict=on without port forwarding. No host Docker socket, host devices or other app data are mounted. This is not an Internet, DNS, HTTPS or full security test. Start manually with Supervisor protection enabled, check the PASS marker in the logs, then stop the app. Nod itself is not included.

## Español

La versión 0.1.0-dev.3 arranca un Linux mínimo en QEMU (una CPU virtual, 256 MiB de RAM), comprueba el disco persistente de 8 MiB en dos arranques y prueba la puerta de enlace virtual restringida 10.0.2.2. La red de usuario de QEMU usa restrict=on sin redirección de puertos. No monta el socket Docker, dispositivos del host ni datos de otras aplicaciones. No constituye una prueba de Internet, DNS, HTTPS ni de seguridad completa. Iniciar manualmente con la protección del Supervisor activa, comprobar la marca PASS en el registro y detener la aplicación. Todavía no incluye Nod.
