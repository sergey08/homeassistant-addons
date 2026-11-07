# Moonraker MCP v0.1.0 — Prioridades de revisión legal / Legal review priorities

**Origen de evidencia:** [GitHub Actions DEV12 run 42401009003](https://github.com/sergey08/homeassistant-addons/actions/runs/42401009003), job `validate`, archivo `alpine-license-review.csv` y registros generados desde la base APK de la **imagen compilada**. Estado: **TRIAGE ONLY — NO REDISTRIBUTION APPROVAL**.

## Resultado exacto observado / Observed counts

| Grupo de clasificación automatizada | Paquetes | Nivel práctico de atención |
| --- | ---: | --- |
| `COPYLEFT_OR_RECIPROCAL_REVIEW` | 16 | Revisar antes |
| `OTHER_OR_COMPOUND_REVIEW` | 9 | Revisar a continuación |
| `STANDARD_PERMISSIVE_CANDIDATE` | 12 | Revisar textos y avisos |
| **Total** | **37** | **Los 37 siguen PENDING** |

**Advertencia:** la clasificación se obtiene de las expresiones `L:` instaladas y reglas conservadoras; no es un análisis jurídico de la combinación de programas o del tipo de distribución. Las expresiones `GPL`, `LGPL`, `MPL` y combinadas **no demuestran por sí mismas** incumplimiento, ni se debe afirmar que extiendan automáticamente su copyleft a todo el contenedor.

## Prioridad 1 — paquetes y obligaciones recíprocas / Reciprocal license review

Los siguientes paquetes y versiones quedaron registrados como `REVIEW_APK` en el run indicado. Se debe verificar para cada uno la licencia oficial de su versión, los cambios si los hay, las condiciones de código fuente correspondiente, copyright, avisos y forma de cumplimiento para distribución de la imagen:

| Paquete | Versión | Expresión declarada en APK |
| --- | --- | --- |
| alpine-baselayout | 3.7.0-r0 | GPL-2.0-only |
| alpine-baselayout-data | 3.7.0-r0 | GPL-2.0-only |
| apk-tools | 2.14.13-r0 | GPL-2.0-only |
| busybox | 1.37.0-r20 | GPL-2.0-only |
| busybox-binsh | 1.37.0-r20 | GPL-2.0-only |
| ca-certificates | 20261020-r0 | MPL-2.0 AND MIT |
| ca-certificates-bundle | 20261020-r0 | MPL-2.0 AND MIT |
| gdbm | 1.24-r0 | GPL-3.0-or-later |
| libapk2 | 2.14.13-r0 | GPL-2.0-only |
| libgcc | 14.2.0-r6 | GPL-2.0-or-later AND LGPL-2.1-or-later |
| libstdc++ | 14.2.0-r6 | GPL-2.0-or-later AND LGPL-2.1-or-later |
| musl-utils | 1.2.5-r13 | MIT AND BSD-2-Clause AND GPL-2.0-or-later |
| readline | 8.2.13-r1 | GPL-3.0-or-later |
| scanelf | 1.3.8-r1 | GPL-2.0-only |
| ssl_client | 1.37.0-r20 | GPL-2.0-only |
| xz-libs | 5.8.4-r0 | GPL-2.0-or-later AND 0BSD AND Public-Domain AND LGPL-2.1-or-later |

**No extrapolar**: la etiqueta `COPYLEFT_OR_RECIPROCAL_REVIEW` es una prioridad de examen y no una conclusión sobre la obligación exacta. Comprobar excepciones, licencia por archivos, licencias combinadas y disponibilidad de fuentes de cada paquete exacto.

## Prioridad 2 — expresiones no reconocidas o combinadas / Other expressions

Entre los nueve paquetes de esta categoría, los registros visibles incluyen:

- `libbz2 1.0.8-r6` → `bzip2-1.0.6`
- `libncursesw 6.5_p20250503-r0` y `libpanelw 6.5_p20250503-r0` → `X11`
- `ncurses-terminfo-base 6.5_p20250503-r0` → `X11`
- `pyc 3.12.16-r0`, `python3 3.12.16-r0`, `python3-pyc 3.12.16-r0`, `python3-pycache-pyc0 3.12.16-r0` → `PSF-2.0`
- `sqlite-libs 3.49.2-r1` → `blessing`

Que el clasificador no reconozca una expresión como permisiva no significa que esta licencia sea restrictiva. Consultar siempre los términos originales.

## Prioridad 3 — fuente Go y componentes sin datos / Go source evidence

La CI más reciente conserva un SBOM de **129 componentes**. El informe específico registra **92 componentes sin metadatos de licencia automáticos** (89 PURL Go y 3 sin PURL), y un paquete de textos legales de terceros. El documento `license-review-evidence-hints.json` relaciona referencias exactas del SBOM con evidencias de licencias de Go y metadatos Alpine.

Para los binarios compilados `mcp-raker` y `tunnel-client`, comprobar además licencias y avisos de los repositorios fuente y sus módulos *realmente enlazados*, no las dependencias teóricas de un `go.mod`. **El cliente de túnel incluido es una compilación desde código fijado, no el ZIP oficial sin cambios.**

## Criterio para cierre / Gate closure

1. Descargar los artefactos del **SHA final** aprobado, no reutilizar automáticamente un SBOM de un commit previo si cambia cualquier dependencia o imagen.
2. Revisar los componentes del manifiesto `license-review-pending.json` contra sus versiones exactas y completar registros reales de autor/revisor, evidencia y obligaciones.
3. Decidir y documentar ubicación de LICENSE, NOTICE y, en su caso, acceso a código fuente correspondiente.
4. Ejecutar `license_release_gate.py` sobre el mismo SBOM y manifiesto firmado; un resultado favorable confirma cobertura documental, **no emite una aprobación legal automática**.
5. Mantener la PR #89 DRAFT y la publicación estable detenida hasta revisión y autorización humana.

Otros controles pendientes independientes: rotación/revocación de credenciales y prueba de restauración en HA desechable; revisión visual de traducciones del formulario de token.
