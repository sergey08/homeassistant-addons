# Moonraker MCP v0.1.0 — Acceso a fuentes y avisos de terceros
# Third-party source access and notices

**Estado / Status: documento de acompañamiento, NO dictamen ni certificación de cumplimiento.**

Esta versión utiliza una imagen Alpine 3.22 fijada por digest, paquetes del repositorio Alpine y dos binarios Go compilados desde revisiones fijadas. El [inventario de terceros](./THIRD_PARTY_NOTICES_EN_ES.md) y los artefactos de [la CI](https://github.com/sergey08/homeassistant-addons/actions) identifican las versiones exactas. Las fuentes upstream se enlazan como **referencias**, sin afirmar que estos enlaces por sí solos cumplan obligaciones GPL/LGPL/MPL de redistribución.

## Binarios principales / Main binaries

- `mcp-raker`: [fuentes en commit f01636be](https://github.com/lexfrei/mcp-raker/tree/f01636bec21a21cfc5f9ee84dc68dad7d44d6dd9), licencia BSD-3-Clause incluida en la imagen.
- `tunnel-client`: [fuentes en commit c2144b09](https://github.com/openai/tunnel-client/tree/c2144b0904980bcbae2636cdca4f4167e9818e0b), licencia Apache-2.0 y NOTICE incluidos.
- Las modificaciones de dependencias Go (`golang.org/x/net v0.62.0`) quedan documentadas como archivos `*-dependencies.patch` y `*-upstream.txt` en `/usr/share/doc/moonraker-mcp/provenance/` de la imagen.

## Familias Alpine con prioridad GPL/LGPL/MPL

Las siguientes son **referencias a recetas de compilación, parches y procedencia**, no una oferta certificada de fuente correspondiente a un binario específico. Las versiones son las observadas en el inventario de la imagen candidata:

| Familia Alpine | Versión inventariada | Receta fuente (referencia fija) |
| --- | --- | --- |
| alpine-baselayout | 3.7.0-r0 | [APKBUILD](https://github.com/alpinelinux/aports/tree/2235ae248c31ea48a9df764becdfecc2a85b4f31/main/alpine-baselayout) |
| apk-tools / libapk2 | 2.14.13-r0 | [APKBUILD](https://github.com/alpinelinux/aports/tree/2235ae248c31ea48a9df764becdfecc2a85b4f31/main/apk-tools) |
| busybox / ssl_client | 1.37.0-r20 | [APKBUILD](https://github.com/alpinelinux/aports/tree/2235ae248c31ea48a9df764becdfecc2a85b4f31/main/busybox) |
| ca-certificates | 20261020-r0 | [APKBUILD](https://github.com/alpinelinux/aports/tree/2235ae248c31ea48a9df764becdfecc2a85b4f31/main/ca-certificates) |
| gdbm | 1.24-r0 | [APKBUILD](https://github.com/alpinelinux/aports/tree/2235ae248c31ea48a9df764becdfecc2a85b4f31/main/gdbm) |
| gcc runtime / libstdc++ | 14.2.0-r6 | [APKBUILD](https://github.com/alpinelinux/aports/tree/2235ae248c31ea48a9df764becdfecc2a85b4f31/main/gcc) |
| musl-utils | 1.2.5-r13 | [APKBUILD](https://github.com/alpinelinux/aports/tree/2235ae248c31ea48a9df764becdfecc2a85b4f31/main/musl) |
| readline | 8.2.13-r1 | [APKBUILD](https://github.com/alpinelinux/aports/tree/2235ae248c31ea48a9df764becdfecc2a85b4f31/main/readline) |
| pax-utils / scanelf | 1.3.8-r1 | [APKBUILD](https://github.com/alpinelinux/aports/tree/2235ae248c31ea48a9df764becdfecc2a85b4f31/main/pax-utils) |
| xz-libs | 5.8.4-r0 | [APKBUILD](https://github.com/alpinelinux/aports/tree/2235ae248c31ea48a9df764becdfecc2a85b4f31/main/xz) |

El listado abarca únicamente las **diez familias priorizadas** del inventario legal; otros paquetes y módulos Go también tienen requisitos de atribución y licencia. El detalle se consulta en el SBOM (`moonraker-mcp-dev12-cyclonedx-sbom`) y el inventario de binarios de la CI del commit final. El árbol `aports` fijado conserva las recetas y archivos de parche de Alpine; puede que el código fuente de origen resida en los servidores indicados por cada receta.

**Estado verificado:** 164/166 entradas del inventario de fuentes auxiliares han superado SHA-512 en verificaciones anteriores. Dos archivos de origen, `apk-tools-v2.14.13.tar.gz` y `ca-certificates-20261020.tar.bz2`, devolvieron error HTTP y **no** quedaron acreditados mediante descarga. Esta observación no determina por sí sola el cumplimiento de las licencias.

## Pendiente antes de publicar / Outstanding before release

- Confirmar qué textos de licencia/copyright y avisos deben acompañar la imagen distribuida, incluidos los paquetes Alpine y los módulos Go incorporados.
- Confirmar el mecanismo de entrega de **fuentes correspondientes** de versiones distribuidas y parches/scripts de compilación cuando lo exija la licencia aplicable. No reemplazar esta comprobación por enlaces generales a proyectos upstream.
- Si se decide hacer una oferta de suministro de fuentes a terceros, fijar su contenido, responsable, canal y periodo de disponibilidad aplicable antes de publicarla. **Este documento no constituye dicha oferta.**
- Mantener la PR estable en borrador hasta revisión concreta y autorización expresa.

**EN:** Pinned upstream recipes and project links are supplied as reference evidence only. They are not a verified corresponding-source offer or independent license compliance clearance. Confirm notice inclusion and the availability of the exact corresponding source, as required by each applicable license, before distributing the image.
