# Moonraker MCP — Alpine 3.22: trazabilidad de fuentes prioritarias (ES/EN)

**Fecha de contraste: 2026-11-07. Estado: evidencia preliminar, SIN APROBACIÓN DE REDISTRIBUCIÓN.**

Se han leído directamente 10 archivos `APKBUILD` del repositorio oficial `alpinelinux/aports`, rama `3.22-stable`. Sus pares `pkgver/pkgrel` coinciden con los nombres y versiones del informe de 16 paquetes del contenedor DEV12. Los SHA de la tabla son **hashes de objeto Git de cada archivo APKBUILD**, no los SHA de la fuente descargada ni un commit de la rama; la rama puede avanzar. La tabla no certifica por sí sola que se haya descargado/verificado la fuente o que sea completa.

| Receta Alpine | Versión | Blob SHA Git APKBUILD | Paquetes de los 16 | Licencia declarada o relevante | Pendiente de revisión |
|---|---|---|---|---|---|
| [alpine-baselayout](https://github.com/alpinelinux/aports/blob/3.22-stable/main/alpine-baselayout/APKBUILD) | `3.7.0-r0` | `ac40b76fd9113908ceeeca54f3fb5350b7ea0ef4` | alpine-baselayout; alpine-baselayout-data | GPL-2.0-only | El APKBUILD incluye ficheros locales y recursos de netbase; inspeccionar copyright de cada recurso. |
| [apk-tools](https://github.com/alpinelinux/aports/blob/3.22-stable/main/apk-tools/APKBUILD) | `2.14.13-r0` | `dc23440fdf09d80a1771796c3c78aa322e36e453` | apk-tools; libapk2 | GPL-2.0-only | Fuente desde GitLab Alpine y helper _apk; comprobar receta y fuente correspondientes. |
| [busybox](https://github.com/alpinelinux/aports/blob/3.22-stable/main/busybox/APKBUILD) | `1.37.0-r20` | `30756169bd9b7372c2c27e03e0a4ba143d69006a` | busybox; busybox-binsh; ssl_client | GPL-2.0-only | Múltiples parches locales y ssl_client.c añadido en la receta; comprobar fuente correspondiente de la compilación. |
| [ca-certificates](https://github.com/alpinelinux/aports/blob/3.22-stable/main/ca-certificates/APKBUILD) | `20261020-r0` | `c76805bafbc2a5867c1fe67aa0437573022a36fd` | ca-certificates; ca-certificates-bundle | MPL-2.0 AND MIT | Verificar qué ficheros quedan sujetos a cada licencia, avisos de certificados y publicación del código aplicable. |
| [gdbm](https://github.com/alpinelinux/aports/blob/3.22-stable/main/gdbm/APKBUILD) | `1.24-r0` | `c2b6e155030b3dc945953963962d32ab8532fa07` | gdbm | GPL-3.0-or-later | Fuente original GNU; comprobar modificaciones de empaquetado y medios de entrega de fuente. |
| [gcc](https://github.com/alpinelinux/aports/blob/3.22-stable/main/gcc/APKBUILD) | `14.2.0-r6` | `9c32de4f448d02148af4527478d0714b90440e8c` | libgcc; libstdc++ | GPL-2.0-or-later AND LGPL-2.1-or-later | Numerosos parches; revisar licencias específicas y excepciones de runtime por archivo. |
| [musl](https://github.com/alpinelinux/aports/blob/3.22-stable/main/musl/APKBUILD) | `1.2.5-r13` | `bd1e8555087993da04083d3e1ec3c7bc056e199e` | musl-utils | APKBUILD: MIT; metadatos de musl-utils: MIT AND BSD-2-Clause AND GPL-2.0-or-later | La discrepancia de expresiones exige inspección por archivo y de metadatos del subpaquete, no reinterpretación automática. |
| [readline](https://github.com/alpinelinux/aports/blob/3.22-stable/main/readline/APKBUILD) | `8.2.13-r1` | `dcb00fcc89b735049017c5ebe987baf6f037cab3` | readline | GPL-3.0-or-later | Fuente GNU, dos parches locales y parches numerados upstream; preservar el conjunto aplicable. |
| [pax-utils](https://github.com/alpinelinux/aports/blob/3.22-stable/main/pax-utils/APKBUILD) | `1.3.8-r1` | `5073fed2e6898f789f16ba8dfa543f6bf4706864` | scanelf | GPL-2.0-only | El paquete de origen pax-utils genera el subpaquete scanelf; identificar fuente y licencia del ejecutable distribuido. |
| [xz](https://github.com/alpinelinux/aports/blob/3.22-stable/main/xz/APKBUILD) | `5.8.4-r0` | `b2d6af2e7b824108755dba06fc4ff1fa47211fa9` | xz-libs | GPL-2.0-or-later AND 0BSD AND Public-Domain AND LGPL-2.1-or-later | Distinguir licencias por archivo y comprobar ofertas de fuentes si son exigibles. |

## Trabajo para cerrar el gate humano

1. Descargar el SBOM CycloneDX del **SHA final de la imagen**, el inventario APK y las diferencias de `go.mod/go.sum`. El inventario DEV12 verificado hasta ahora corresponde a [CI 42408893008](https://github.com/sergey08/homeassistant-addons/actions/runs/42408893008), SHA `06696618cf00da5ee31ec1efd0f5ba2f40dfb4fa`.
2. Identificar el **commit** de `3.22-stable` que contenía cada receta y sus archivos auxiliares para registrar una referencia inmutable. Los hashes de blob identifican solamente los contenidos del APKBUILD. Verificar `source`, `sha512sums`, ficheros adicionales, `prepare()`, parcheado y subpaquetes.
3. Para cada paquete instalado, verificar correspondencia entre el paquete binario de la imagen y el código fuente publicado por Alpine, incluidas configuraciones, parches y scripts de compilación cuando proceda.
4. Examinar textos legales originales y condiciones aplicables por componente/archivo, excepciones runtime de GCC y licencias combinadas. Determinar qué avisos, licencias, fuentes u ofertas de fuente deben acompañar la **distribución binaria** y dónde se suministrarán.
5. Registrar cada `bom-ref` separadamente y completar el manifiesto de revisión humana **solo cuando exista evidencia suficiente y revisión real**. No cambiar ningún estado `PENDING` por esta tabla.

## Límites de esta evidencia / Evidence limitations

- Una expresión de licencia en APK no determina por sí sola obligaciones exactas ni significa incumplimiento.
- No consta aún verificación descargando los source tarballs para los diez orígenes; la auditoría de fuentes completas y atribuciones **sigue pendiente**.
- Las 10 familias agrupan 16 subpaquetes a efectos de investigación; **no** reducen a 10 los registros de aprobación necesarios.
- Mantener intactas credenciales/túnel y la instalación Lenovo. El mantenedor no quiere claves ni túneles nuevos para pruebas.
- La PR #89 sigue DRAFT; no fusionar ni publicar `0.1.0` sin decisión expresa del mantenedor y revisión legal.

EN: This is verified APKBUILD recipe discovery and source-origin triage, **not license clearance or complete corresponding-source verification**.
