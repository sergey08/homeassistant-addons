# Nod VM preflight

## English

Boots a minimal Linux guest in QEMU using software emulation, one virtual CPU and 256 MiB of guest RAM. The probe uses no guest network, host devices, Docker socket, or access to other apps' data. Start manually with Supervisor protection enabled, check the guest boot marker in the log, then stop the app. A successful boot validates the VM mechanism. Version 0.1.0-dev.2 adds an 8 MiB disk in the app's persistent data directory and checks that a marker written by the guest survives a reboot. Nod, guest networking and production performance require separate validation.

## Español

Arranca un Linux mínimo en QEMU por emulación de software, con una CPU virtual y 256 MiB de RAM para la máquina virtual. La prueba prescinde de red para el invitado, dispositivos del host, socket de Docker y acceso a datos de otras aplicaciones. Inicia manualmente con la protección del Supervisor activa, comprueba la marca de arranque en el registro y detén la aplicación. Un arranque correcto valida el funcionamiento de la máquina virtual. La versión 0.1.0-dev.2 añade un disco de 8 MiB en el directorio persistente de la aplicación y comprueba que una marca escrita por el invitado se recupera tras reiniciar. Quedan por comprobar Nod, la red y el rendimiento.
