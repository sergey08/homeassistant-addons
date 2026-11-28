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

## Dev.5: embedded Home Assistant panel — implementation gate

Dev.4 is deployed and the owner has validated a real ChatGPT subscription conversation. Preserve the dedicated HTTPS URL, database and existing standalone login. The owner has requested a full HA sidebar panel before MCP/browser/workspace work.

Do not serve the Nod frontend or agent-controlled content on the HA origin. The Ingress page should contain a cross-origin iframe pointing at the configured dedicated Nod HTTPS origin and a visible standalone fallback link. Keep the diagnostic page if HTTPS is disabled. No owner token in HTML, URL, HA logs or automatic proxy headers.

Design candidate (not yet implemented or validated): explicit opt-in, one administrator-supplied HTTPS HA ancestor origin, validated as an origin and distinct from Nod. Keep CSP frame-ancestors 'none' by default; allow only the configured ancestor for embedding. Review the HA Ingress iframe sandbox and ancestor chain. Treat initial cross-site iframe GET navigation narrowly (public shell only), never exempt API requests from authentication, exact Host/Origin or cross-site protection. Retain independent login inside the frame. Evaluate Secure, HttpOnly, SameSite=None, Partitioned cookie scoped to the dedicated Nod host, distinct from existing standalone cookie, with explicit tests of partition separation and existing standalone authentication. Do not weaken authentication to work around browsers that block third-party storage; use standalone fallback when unsupported.

Before deploying: browser-based Chromium test using distinct HTTPS sites (not merely different ports on the same site), an HA-like nested Ingress frame, real UI authentication, API reads and writes, streaming, reload, navigation and OAuth popup/manual callback. Negative tests: foreign ancestor, wrong Host/Origin, cross-site API request, missing or invalid token, unauthorized peer, no leaked HA/Nod cookies or token in link/HTML, disabled embedding, preserved standalone behavior and persistence. Verify Safari/mobile separately before claiming support. Keep webhook/upgrade restrictions unchanged. Do not deploy until CI passes and do not merge to main without user approval.

### Español

Prioridad dev.5: interfaz completa dentro del menú lateral de Home Assistant. Mantener origen HTTPS independiente, iframe de origen cruzado, autenticación propia y autorización explícita de un único origen padre de HA. Probar cookies particionadas, navegación, streaming y bloqueo de sitios ajenos en navegador real antes de desplegar. Si el navegador no admite la autenticación embebida, conservar el enlace externo. No se ha implementado todavía el iframe ni cambiado producción. MCP, Chromium y Workspace quedan para después.
