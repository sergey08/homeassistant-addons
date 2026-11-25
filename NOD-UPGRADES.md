# Nod upstream upgrade policy

Nod for Home Assistant is an integration layer around upstream n8n-io/nod, not a separately maintained product fork. The native app currently builds exact upstream revision 6670bc233b6b7dddaa75b25b89b4a89f0e92bcac. App version and upstream version/revision must be recorded separately.

## Upgrade procedure

1. Review upstream releases, release notes, security advisories, deployment requirements, supported Node/PostgreSQL versions, authentication and database migrations. Choose an official release and resolve its immutable commit SHA. Never build a moving branch in a release.
2. Work on a dedicated beta branch. Keep HA-specific code in the app directory and minimize upstream source changes. The current build-time UI patch is guarded by exact anchors and must fail if the upstream code changes; review and remove patches whenever upstream supplies an equivalent supported feature. Consolidate the upstream revision into one build-time source of truth before the first upstream upgrade.
3. Test compilation and the native runtime, persistent database and vault, old-version-to-new-version migration using synthetic data, HTTPS and Ingress isolation, embedded and standalone authentication, SSE, and local MCP adapter behavior. Also test real model login/chat, MCP discovery/read, mobile and any supported workspace/browser features. Do not export production secrets or data to CI. Record any untested features explicitly.
4. Before deploying a beta on HA, make and verify a private backup of the application data (including PostgreSQL and encryption keys); use a consistent database backup or stop the app for a cold backup. Store the previous image/version and document the restore procedure. Never downgrade an already-migrated database without proving compatibility; restore the paired pre-upgrade data and keys if necessary. Test migration and rollback on disposable data before updating production.
5. Only deploy after CI passes, then validate against the real Home Assistant installation. No stable merge/release without user approval. Keep the current working version available while evaluating upstream releases. Record upstream SHA/tag, addon version, patches, migrations, test results and rollback instructions in the changelog and Obsidian.

## Español

La aplicación debe seguir a Nod oficial, manteniendo separadas las adaptaciones de HA. Cada actualización partirá de una versión oficial identificada por SHA inmutable, se probará en una beta con CI y pruebas de migración y restauración, y se validará en el HA real antes de liberar estable con aprobación del usuario. No actualizar automáticamente producción ni cambiar PostgreSQL de versión mayor sin una migración específica. Antes de actualizar, guardar una copia privada consistente de datos y claves y conservar la versión anterior; para revertir una migración incompatible, restaurar también los datos anteriores. Reducir los parches propios cuando Nod incorpore soporte equivalente. El primer upgrade upstream deberá centralizar la revisión en una única referencia de compilación. No se ha validado todavía una migración entre dos revisiones upstream distintas.

