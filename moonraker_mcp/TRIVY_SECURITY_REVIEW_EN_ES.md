# DEV10 — Trivy security findings / Hallazgos de seguridad de Trivy

**Scan date / Fecha:** 2026-11-06. **Scope:** `moonraker-mcp:ci`, built from pinned DEV10 image and dependencies. **Status:** stable-release BLOCKER; no waiver or vulnerability remediation is implied.

## English — Evidence

Image security scan executed inside GitHub Actions with `aquasecurity/trivy-action` **pinned to full reviewed commit SHA** `ed142fd0673e97e23eac54620cfb913e5ce36c25` (v0.36.0). We intentionally do not depend on mutable tags following the March 2026 Trivy supply-chain incident. The scanner analyzes vulnerabilities and license classifications, writes JSON and a human-readable summary to the 14-day CI artifact. Dev CI is **nonblocking on findings** (`exit-code: 0`); a green workflow is not a zero-vulnerability result. The scan itself and final GitHub CI run passed:
- https://github.com/sergey08/homeassistant-addons/actions/runs/42197590846
- https://github.com/sergey08/homeassistant-addons/actions/runs/42197600262

### Initial vulnerability counts

| Severity | Count |
| --- | ---: |
| Critical | 0 |
| High | **15** |
| Medium | 10 |
| Low | 2 |
| Unknown | 3 |

**All 15 HIGH findings in the initial detailed summary refer to `stdlib` v1.26.4 (13 entries) or `golang.org/x/text` v0.23.0 (2 entries).** The scanner names example identifiers CVE-2026-111943, CVE-2026-33818, CVE-2026-39821, CVE-2026-56851/56852, and CVE-2026-97031. The scanner's recommended fixed branches include Go 1.26.10 or 1.27.3 (depending on the advisory) and `golang.org/x/text` 0.39.0/0.41.0. **A scanner finding is not proof of exploitability in the running deployment.** A binary-level reachability analysis and the advisory requirements are needed to assess real risk.

The pinned `mcp-raker` upstream release remains `v0.2.0` (2026-06-22). Its pinned source revision uses Go 1.26.4 and earlier Go modules, consistent with the detected HIGH dependencies. As of this review, the upstream repository `master` has moved to Go **1.27.3** and `golang.org/x/text` **v0.41.0**; this suggests a potential route to a safer **new separately tested source build**, but we must not replace the existing pinned release binary with an unverified mutable branch. Pin an exact commit, validate source provenance, compare behavior and pass the full DEV CI plus live ChatGPT tests before any upgrade.

### License scan

**46 detected license entries**: 16 `notice`, 17 `restricted`, 2 `reciprocal`, 1 `unencumbered`, 10 `unknown`. Restricted entries include Alpine packages under GPL-2.0, GPL-3.0 and LGPL; reciprocal entries include ca-certificates packages tagged MPL-2.0. Unknown includes `PSF-2.0`, `X-11`, `Public-Domain`, and other labels that the automated classifier does not recognize. **These are classifier categories, not legal conclusions.** Redistributing normal Alpine packages under GPL/LGPL may be legitimate with the applicable obligations; counsel or maintainer must review the exact notices and source-offer requirements. Do not label all restricted packages as prohibited.

### Release decision

- [x] Run real image scan, retain machine-readable report and explain nonblocking CI semantics.
- [x] Locate initial high-risk packages and possible patched upstream versions.
- [ ] Determine per-finding affected binary and relevant application attack surface; distinguish reachable vulnerabilities from library matches.
- [ ] Rebuild or update pinned `mcp-raker` with patched Go compiler and module dependencies; verify behavior, licensing and provenance.
- [ ] Re-run vulnerability and license scans, record remaining justified exceptions with source/advisory references.
- [ ] Complete transitive-license compliance review and full SBOM validation.
- [ ] Perform independent fresh GUI installation and explicit maintainer release authorization.

**No stable release and no merge to `main` until these gates are addressed.**

## Español — Conclusiones

El escáner Trivy sobre la imagen real de **Moonraker MCP DEV10** detectó **0 vulnerabilidades críticas, 15 altas, 10 medias, 2 bajas y 3 de gravedad desconocida**. Entre las 15 altas, las dependencias señaladas son la biblioteca estándar de **Go 1.26.4** y `golang.org/x/text` **0.23.0**. El propio informe señala versiones corregidas, pero **no se ha demostrado que todas esas vulnerabilidades sean explotables** desde nuestro MCP privado de solo lectura.

La versión oficial fijada de `mcp-raker` es v0.2.0; su repositorio de desarrollo ha avanzado a Go 1.27.3 y a `x/text` 0.41.0. Es una opción para estudiar y construir una versión actualizada desde un commit concreto, pero requiere una nueva batería de pruebas y no justifica actualizar automáticamente el binario instalado.

Se detectaron **46 entradas de licencia**: 17 marcadas como restrictivas y 10 como desconocidas, principalmente en paquetes del sistema Alpine (GPL/LGPL) y etiquetas de licencias que Trivy no clasifica. Estas categorías **no significan por sí mismas que esté prohibida la distribución**. Hay que comprobar el cumplimiento de cada licencia y los avisos legales necesarios.

La acción Trivy está fijada por **SHA completo**, no por una etiqueta mutable, debido al incidente de seguridad que afectó a la cadena de suministro de Trivy en marzo de 2026. El escaneo está configurado para **informar sin detener la CI de desarrollo**; por tanto, que GitHub Actions esté en verde no quiere decir que no existan vulnerabilidades.

**Publicación estable BLOQUEADA.** La versión DEV10 instalada se conserva; no abrir puertos, no ampliar permisos, no publicar y no fusionar la PR #89 con `main` hasta remediar y verificar lo anterior.
