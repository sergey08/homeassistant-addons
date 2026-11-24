# Native Nod web access — design decision

Upstream revision: 6670bc233b6b7dddaa75b25b89b4a89f0e92bcac.

## Verified baseline

Dev.3 runs on the physical Home Assistant OS Lenovo. The user confirmed the read-only Ingress page from the mobile HA app. Direct requests to the diagnostic app are refused. The original Nod server stays on loopback, with persistent PostgreSQL and private keys.

## Why not transparently reverse-proxy the original UI under Ingress?

- `src/server/network.ts` requires a standalone HTTPS origin (HTTP only on localhost), without a subpath.
- `src/server/access.ts` validates Host, Origin, cross-site requests and authentication, emits `frame-ancestors 'none'`, and scopes the authentication cookie to Path=/.
- The frontend uses absolute API and navigation paths in `src/web/lib/api.ts`, `navigation.ts`, `session.ts` and other files. Vite uses root assets by default. OAuth callbacks and WebSocket/streaming paths also require review.
- HA Ingress shares the HA browser origin. Running agent-generated web content in that origin requires an explicit security review. Rewriting HTML alone, disabling Host/Origin checks, removing frame protections globally or forwarding an implicit owner token are not acceptable shortcuts.

## Next test

Verify the original web shell, authenticated session and refusal of hostile Host/Origin/unauthenticated requests in isolated CI, with the original server unchanged. A dedicated HTTPS origin is the preferred candidate for the complete UI; an HA sidebar entry could link to it instead of embedding it. Choosing the real hostname, TLS certificate, network scope and remote access needs a separate deployment decision. No new external ports, DNS entries, proxy rules or certificates will be configured in this phase.

The full browser/workspace and model/MCP connections remain separate tasks; access to the original UI does not prove those capabilities. Preserve the VM experiment and the native database throughout.

## Español

La dev.3 está validada en el móvil por Ingress. La interfaz original exige un origen propio y aplica validaciones de Host/Origin, cookie de autenticación y bloqueo de iframe. No basta con reescribir rutas ni retirar protecciones. La opción preferente para la interfaz completa es un origen HTTPS independiente enlazado desde HA; el destino real y su exposición quedan pendientes de decisión. Primero se prueban la interfaz y las garantías originales en CI aislada, sin tocar DNS, puertos, certificados ni la instalación de producción.
