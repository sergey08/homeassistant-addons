# Nod VM preflight

## English

Boots a minimal Linux guest in QEMU using software emulation, one virtual CPU and 256 MiB of guest RAM. The probe uses no guest network, host devices, Docker socket, or persistent guest disk. Start manually with Supervisor protection enabled, check the guest boot marker in the log, then stop the app. A successful boot validates the VM mechanism. Nod, guest networking, storage and production performance require separate validation.

## Español

Arranca un Linux mínimo en QEMU por emulación de software, con una CPU virtual y 256 MiB de RAM para la máquina virtual. La prueba prescinde de red para el invitado, dispositivos del host, socket de Docker y disco persistente. Inicia manualmente con la protección del Supervisor activa, comprueba la marca de arranque en el registro y detén la aplicación. Un arranque correcto valida el funcionamiento de la máquina virtual. Quedan por comprobar Nod, la red, el almacenamiento y el rendimiento.
