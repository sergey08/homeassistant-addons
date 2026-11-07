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

## Verificación de revisión inmutable de Alpine (2026-11-07)

Se ha identificado el commit completo de la rama upstream `alpinelinux/aports:3.22-stable` en el momento del cotejo:

- Commit de aports: [`2235ae248c31ea48a9df764becdfecc2a85b4f31`](https://github.com/alpinelinux/aports/commit/2235ae248c31ea48a9df764becdfecc2a85b4f31) (fecha Git del commit: 2026-11-07 12:43:18 UTC).
- Se han vuelto a recuperar **las diez rutas `main/<familia>/APKBUILD` indicando expresamente ese commit**, no la rama.
- Resultado: **los 10 blobs Git coinciden exactamente con los SHA de la tabla superior**.
- Para reproducir la lectura de un archivo, usar `https://github.com/alpinelinux/aports/blob/2235ae248c31ea48a9df764becdfecc2a85b4f31/main/<familia>/APKBUILD` (sustituir `<familia>`).
- Esta comprobación da un punto de referencia **inmutable** para las recetas de los 16 paquetes auditados, pero **no** certifica que el paquete binario instalado fuera construido precisamente con este árbol, ni que ya se hayan inspeccionado sus ficheros auxiliares y fuentes completas.
- La fuente correspondiente, parches, excepciones y obligaciones de licencia siguen pendientes de validación individual por el revisor.

## Cotejo del árbol de fuentes auxiliares (2026-11-07)

Se ha usado **el mismo commit fijado** de `alpinelinux/aports` (`2235ae248c31ea48a9df764becdfecc2a85b4f31`) para leer tanto los `APKBUILD` como los listados del directorio `main/<familia>/`. Se han extraído los **nombres**, no los contenidos, de las entradas `sha512sums` y se han cruzado con los archivos publicados. **No se han descargado aún los tarballs ni recalculado sus SHA-512.**

| Familia | Entradas SHA-512 de la receta | Archivos coincidentes en la carpeta de aports | Entradas externas/restantes | Observación |
|---|---:|---:|---:|---|
| alpine-baselayout | 12 | 10 | 2 | `protocols-6.4` y `services-6.4`: recurso externo de netbase |
| apk-tools | 2 | 1 | 1 | tarball fuente externo |
| busybox | 72 | **71** | 1 | tarball upstream; todos los parches, `ssl_client.c` y otros auxiliares enumerados presentes |
| ca-certificates | 1 | 0 | 1 | tarball externo |
| gdbm | 1 | 0 | 1 | tarball GNU |
| gcc | 41 | **40** | 1 | tarball GCC; todos los auxiliares/parches enumerados presentes |
| musl | 18 | **17** | 1 | tarball musl; todos los parches enumerados presentes |
| readline | 17 | 3 | 14 | 1 tarball GNU y **13 parches GNU numerados** añadidos dinámicamente por la receta |
| pax-utils | 1 | 0 | 1 | tarball externo |
| xz | 1 | 0 | 1 | tarball upstream |

**Resultado limitado pero verificable:** 142 entradas de fuentes auxiliares con nombre coincidente en el directorio aports fijado (10+1+71+40+17+3). Las otras 24 entradas corresponden a recursos externos declarados o generados dinámicamente por recetas; su ausencia en el directorio local **no es un error de empaquetado**. La lectura confirma rutas/nombres, no los checksums SHA-512 de los bytes. Un enlace a archivos GitHub tampoco equivale a evidencia completa de código fuente correspondiente.

**Precaución sobre Readline:** `readline82-001.patch` a `readline82-013.patch` figuran en la lista de checksums, y la receta los añade desde la URL GNU de parches mediante un bucle. No marcarlos como archivos locales desaparecidos.

**Próximo cierre verificable:** obtener y cotejar cada descarga con el SHA-512 de la receta y registrar el tratamiento de parches, scripts de compilación, excepciones de licencia y fuentes accesibles para terceros. Las aprobaciones de los 129 `bom-ref` se mantienen `PENDING`.

## Verificación de integridad real SHA-512 automatizada (07/11/2026)

- La rama DEV añade `moonraker_mcp/alpine_source_integrity.py` y el job independiente `alpine-source-integrity` en GitHub Actions.
- El job obtiene el **commit exacto** `2235ae248c31ea48a9df764becdfecc2a85b4f31` de aports mediante `git fetch --depth=1 --filter=blob:none` y checkout disperso de las diez carpetas.
- Se leen las entradas `sha512sums` de cada `APKBUILD`, se calculan hashes de bytes reales de los 142 ficheros locales y se comprueban sus coincidencias. **Job SUCCESS** en [CI 42416854656](https://github.com/sergey08/homeassistant-addons/actions/runs/42416854656), commit `1296177f326579d85d0247cc8cff9d8e2f708e34`.
- Los **24 archivos externos** quedan señalados `external_source_entries_unverified`: no se descargaron ni se verificaron mediante SHA-512. La ausencia no implica un fallo cuando la receta indica un recurso remoto.
- El artefacto `moonraker-mcp-alpine-source-integrity` conserva `alpine-source-integrity.json` con diez resultados por familia y bandera `license_approved: false`.
- **Alcance estricto:** se ha confirmado la integridad del árbol de fuentes auxiliares coincidentes con las recetas fijadas, no la correspondencia final de cada binario, las licencias por archivo, las descargas remotas ni la suficiencia de los avisos GPL/LGPL/MPL. No cambiar el estado `PENDING` de ningún componente SBOM.

## Verificación de parches remotos GNU Readline (07/11/2026)

- La CI añade `readline-remote-integrity`, que obtiene el `APKBUILD` Readline del commit `2235ae248c31ea48a9df764becdfecc2a85b4f31` y reproduce las **13 URLs de parches numerados** de GNU Readline 8.2: `https://ftp.gnu.org/gnu/readline/readline-8.2-patches/readline82-001` … `readline82-013`.
- El script `moonraker_mcp/readline_patch_integrity.py` exige la versión `readline 8.2.13-r1`, un orden 001–013 y coteja el SHA-512 real de cada descarga contra el checksum de su alias `readline82-NNN.patch` en la receta.
- **Job SUCCESS** en [CI 42417365817](https://github.com/sergey08/homeassistant-addons/actions/runs/42417365817): se han verificado **13 fuentes remotas adicionales**, sin ejecución ni instalación.
- Estado de cobertura: **142 auxiliares locales + 13 parches GNU remotos = 155 entradas verificadas de 166**. **11 externas pendientes**: nueve tarballs upstream y dos recursos netbase (protocols/services 6.4).
- El artefacto `moonraker-mcp-readline-remote-integrity` almacena URLs, tamaños y digests SHA-512, sin guardar secretos ni aprobar licencias. Todos los componentes del SBOM permanecen `PENDING`.
- El job es evidencia de integridad, no certificación de fuentes correspondientes a binarios ni conclusión legal.

## Auditoría de las 11 fuentes externas restantes (07/11/2026)

- Se ha creado el manifiesto **`alpine-external-sources-pending.json`** con las **11 URLs y SHA-512 exactos** obtenidos de las diez recetas Alpine inmutables: **9 archivos fuente upstream y 2 recursos `netbase`**. Todas sus entradas tienen `status: PENDING_DOWNLOAD_SHA512`: preparar evidencias **no** equivale a descargar y verificar los bytes.
- Se ha añadido `alpine_remote_source_integrity.py` para descargar cada archivo por HTTPS en flujo de bloques (sin ejecutar el código), limitar el tamaño, calcular SHA-512 y comparar con la receta. Ante cualquier fallo de red, límite o checksum, devuelve **ERROR**, no `PASS`.
- Trabajo de CI `alpine-remote-source-integrity`: **solo ejecución manual mediante `workflow_dispatch`**, porque las descargas grandes de GCC y las restricciones de acceso externo pueden producir fallos de red intermitentes ajenos al código. También se ha pasado el trabajo `readline-remote-integrity` a ejecución manual por ese motivo; las 13 descargas Readline ya pasaron previamente una verificación real en [run 42417365817](https://github.com/sergey08/homeassistant-addons/actions/runs/42417365817), pero [run 42417415603](https://github.com/sergey08/homeassistant-addons/actions/runs/42417415603) falló por `Network is unreachable`, **no** por SHA-512.
- Los 11 recursos permanecen **SIN VERIFICAR** hasta disponer de un artefacto válido de ese trabajo manual. No rebajar el umbral de integridad para declarar cumplimiento.
- Estado total de integridad conocido: **155/166 verificados**, **11/166 pendientes**. La revisión de obligaciones legales y el manifiesto humano de los 129 registros SBOM siguen sin completar.
- Esta etapa no cambia las credenciales, el túnel ni la instalación Lenovo; no es aprobación legal ni autorización de publicación.

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
