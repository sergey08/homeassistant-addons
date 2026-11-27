# Nod upstream upgrade policy

Nod for Home Assistant is an integration layer around upstream n8n-io/nod, not a separately maintained product fork. The native app currently builds exact upstream revision 1128fcfd770d619f3391e0bd9f1ca2f9966f2be6. App version and upstream version/revision must be recorded separately.

## Upgrade procedure

1. Review upstream releases, release notes, security advisories, deployment requirements, supported Node/PostgreSQL versions, authentication and database migrations. Choose an official release and resolve its immutable commit SHA. Never build a moving branch in a release.
2. Work on a dedicated beta branch. Keep HA-specific code in the app directory and minimize upstream source changes. The current build-time UI patch is guarded by exact anchors and must fail if the upstream code changes; review and remove patches whenever upstream supplies an equivalent supported feature. Use the canonical upstream manifest and generate the independent build-context pins before the first upstream upgrade.
3. Test compilation and the native runtime, persistent database and vault, old-version-to-new-version migration using synthetic data, HTTPS and Ingress isolation, embedded and standalone authentication, SSE, and local MCP adapter behavior. Also test real model login/chat, MCP discovery/read, mobile and any supported workspace/browser features. Do not export production secrets or data to CI. Record any untested features explicitly.
4. Before deploying a beta on HA, make and verify a private backup of the application data (including PostgreSQL and encryption keys); use a consistent database backup or stop the app for a cold backup. Store the previous image/version and document the restore procedure. Never downgrade an already-migrated database without proving compatibility; restore the paired pre-upgrade data and keys if necessary. Test migration and rollback on disposable data before updating production.
5. Only deploy after CI passes, then validate against the real Home Assistant installation. No stable merge/release without user approval. Keep the current working version available while evaluating upstream releases. Record upstream SHA/tag, addon version, patches, migrations, test results and rollback instructions in the changelog and Obsidian.

## Español

La aplicación debe seguir a Nod oficial, manteniendo separadas las adaptaciones de HA. Cada actualización partirá de una versión oficial identificada por SHA inmutable, se probará en una beta con CI y pruebas de migración y restauración, y se validará en el HA real antes de liberar estable con aprobación del usuario. No actualizar automáticamente producción ni cambiar PostgreSQL de versión mayor sin una migración específica. Antes de actualizar, guardar una copia privada consistente de datos y claves y conservar la versión anterior; para revertir una migración incompatible, restaurar también los datos anteriores. Reducir los parches propios cuando Nod incorpore soporte equivalente. La referencia canónica está en nod-upstream.json; generar y verificar los pins antes de cada upgrade. No se ha validado todavía una migración entre dos revisiones upstream distintas.


## Maintenance architecture (2026-11-27)

Keep Server, Browser and Workspace isolated as three HA apps. Treat them as a coordinated release set, not three product forks. Preserve separate build contexts for HA local builds; `nod-upstream.json` is the canonical tag and immutable SHA. The generated pins in the three Dockerfiles and browser CI checkout must match. Run `node scripts/check-nod-upstream.mjs --write` after changing the manifest, review the diff, then run without arguments. Never change only one pin. CI checks the manifest, generated pins and upstream tag resolution. No runtime or image changes in this maintenance-only PR.

Future work: automate discovery of stable upstream releases and produce a candidate report/PR, without automatic promotion; review upstream patch anchors and prune obsolete HA patches; build and test all three components from the candidate SHA; test database migration and rollback with synthetic data; publish immutable images with fresh component versions as required; coordinate update and verify component compatibility before exposing production updates. A full single-action HA upgrade is a design goal, not an implemented feature. Keep the existing three-app install flow.

Latest release observed on 2026-11-27: nod-v0.10.3, after 0.10.0, 0.10.1 and 0.10.2 on the same day. Evaluate 0.10.3 separately after the maintenance guard is validated. The currently pinned release is nod-v0.9.7. No upstream upgrade is performed here.

## Español — mantenimiento coordinado

Mantener tres aplicaciones aisladas y una única referencia canónica de Nod. Los Dockerfiles conservan sus propios contextos de compilación para HA; el script genera los pins desde el manifiesto y CI detecta discrepancias. Automatizar la detección de versiones oficiales, análisis de cambios, compilación y pruebas de migración, pero no la promoción a producción. La actualización coordinada desde la integración es un objetivo pendiente, no una funcionalidad existente. La beta de adaptación a 0.10.3 será independiente y conservará la versión anterior hasta validar la migración.
