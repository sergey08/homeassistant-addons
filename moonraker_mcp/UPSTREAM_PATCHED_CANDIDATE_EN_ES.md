# Patched mcp-raker source build candidate / Compilación experimental de mcp-raker

**2026-11-06 — NO DEPLOYMENT / SIN INSTALACIÓN.**

## English

DEV10 currently runs the pinned upstream container `ghcr.io/lexfrei/mcp-raker@sha256:cdfbb9b4ead2b3f8a253eb55c1996a69cfdbc17088cc111b7d265d8b71f7090e`. The image scan found 15 HIGH vulnerability matches in an older Go runtime and `golang.org/x/text`; this is a release blocker but not proof of remote exploitation.

A separate **CI-only** source candidate has been added. It uses:

- Exact upstream Git commit `f01636bec21a21cfc5f9ee84dc68dad7d44d6dd9` (not a mutable master ref), fetched with Git and SHA-verified.
- Go compiler image `golang:1.27.3-alpine` pinned to `sha256:d200d2dd76b03a99b52651fd1325aff7dcd35422c35c01bac56571b0507f3deb`.
- Repository source `go.mod` declares `golang.org/x/text v0.41.0`, `go test ./...`, `go mod verify`, CGO-disabled amd64 binary.
- `Dockerfile.upstream-candidate` produces the experimental upstream executable, while the normal add-on Dockerfile still defaults to the original immutable image unless `UPSTREAM_IMAGE` is explicitly overridden **during a separate CI build**.
- The workflow `moonraker-mcp-upstream-candidate.yml` builds a non-deployed add-on candidate, verifies embedded compiler/dependency versions, tests the actual authenticated MCP modern discovery and five safe tools with no printer or external network, scans its built image with SHA-pinned Trivy, then applies the HIGH/CRITICAL security gate.

**Result:** See the workflow execution before asserting the candidate is compatible or vulnerability-free. The standard DEV10 installation and main branch have not changed.

Caveat: A source build from a fixed commit still needs security review of its own build chain, code changes and behavior. Even if the HIGH gate passes, this does not mean all MEDIUM/LOW issues, license obligations, clean-install requirements and maintainer approval are satisfied.

## Español

La versión DEV10 operativa continúa utilizando el binario upstream original. Para investigar las 15 alertas HIGH se ha preparado **otra imagen exclusiva de pruebas**, compilada desde un commit concreto de `mcp-raker`, con Go 1.27.3 y dependencias actualizadas. La construcción normal de Home Assistant **no cambia** salvo que una prueba CI solicite expresamente el nuevo origen.

GitHub Actions compilará esta candidata, comprobará el protocolo MCP moderno y las cinco herramientas de lectura usando datos de prueba sin impresora, repetirá Trivy y ejecutará el control de vulnerabilidades HIGH/CRITICAL. **No se instalará ni publicará automáticamente**, aunque la CI pase.

La decisión final exige validar compatibilidad con el túnel real y la Snapmaker U1, completar la auditoría de licencias y procedencia y obtener autorización para publicar.
