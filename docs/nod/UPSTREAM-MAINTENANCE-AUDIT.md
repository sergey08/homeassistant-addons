# Nod for Home Assistant: upstream maintenance and packaging investigation

Status: research, 2026-11-27. Baseline: Server dev.34 and Browser/Workspace dev.6, distribution commit 5487ed948e31b0f32eb75f71f98e4ce577aec76f. No production changes.

## Findings
- The three Dockerfiles currently pin upstream commit 1128fcfd770d619f3391e0bd9f1ca2f9966f2be6 (Nod desktop 0.9.7 release commit). Browser CI repeats the same SHA. NOD-UPGRADES.md still mentions the older 6670bc233b6b7dddaa75b25b89b4a89f0e92bcac revision.
- Server and Workspace hardcode the SHA; Browser uses a build argument with a default. Publication is split into a Server workflow and a two-worker matrix. Existing image tags are intentionally preserved; a new upstream revision must not reuse a published component tag for changed content.
- Official self-host Nod separates Server, PostgreSQL, Browser, Workspace, network firewall and runtime proxy. Our existing three-app adaptation already consolidates Server and database and avoids host Docker access. Browser and Workspace have distinct trust/network boundaries. Consolidating them is not proven safer or cheaper to maintain.
- Latest official release observed today: nod-v0.10.3 (17:52 UTC). Four releases 0.10.0–0.10.3 were published on 27 November. GitHub comparison from our 0.9.7 source commit to 0.10.3 reports 149 commits ahead and a capped list of 300 changed files, including Browser protocol/bridge/client/worker, Workspace Dockerfile, server routes and database code. Desktop release notes do not guarantee self-host compatibility. Review exact self-host source and migrations.

## Recommended first beta architecture
Keep three independently isolated Supervisor applications and the existing guided installation experience. Treat them as one product/version set. Prefer one update entry point where supported by Supervisor and the integration, with explicit administrator authorization and progress/diagnostics. Do not grant host Docker socket or disable protection for convenience. Investigate a two-app layout only if an equivalent security boundary and measurable maintenance benefit can be demonstrated. No implementation or deployment of such consolidation yet.

## Maintenance automation plan
1. One checked-in release manifest records immutable upstream SHA, tag/source release, compatible component versions, and image digests after publication. Use the same source for Docker builds and CI, including the original Browser reference check. Keep old fixtures explicitly pinned and distinct from current builds.
2. Scheduled read-only check for official releases; open a candidate PR for a chosen revision. Coalesce rapid patch releases; expedite security fixes. Never directly follow a moving main branch.
3. Maintain HA-specific adapters and patches separately, with guarded patch application and compatibility tests. Prefer reuse of upstream public interfaces and contribute generally useful fixes upstream.
4. Build all affected images, run unit/integration tests, model chat, browser/workspace task, Ingress, network isolation, resource policy, data persistence and migration/restore checks. Rebuild and retag every changed component; retain immutable prior images. Enforce version compatibility or reject unsupported combinations without silently granting access.
5. Publish candidate images only after checks pass, verify anonymous pull/digests, then advertise the coherent version set. Test installation and interrupted update/rollback in disposable HA with synthetic data; validate actual HA with owner approval before stable promotion. Do not auto-deploy or perform database downgrade in place.
6. Document upstream and HA versions, known limitations, security and backup/restore. Make update experience as simple as the present onboarding; verify integration/Supervisor update APIs and permissions before promising one-click coordinated updates.

## First engineering gate
Centralize the upstream pin and validate that all current builds use the same 0.9.7 commit, without changing existing public image tags. Then exercise the pipeline against a newer official upstream candidate (0.10.3 at time of audit), without replacing dev.34 or personal Ollama settings. No automatic publish on failed patch/tests or migration. No public beta until the upgrade path has been demonstrated.

## Evidence
- https://github.com/sergey08/homeassistant-addons/tree/feat/nod-home-assistant
- https://github.com/sergey08/homeassistant-addons/blob/feat/nod-home-assistant/NOD-UPGRADES.md
- https://github.com/n8n-io/nod/blob/main/deployment/self-host/compose.yaml
- https://github.com/n8n-io/nod/releases/tag/nod-v0.10.3
- https://github.com/n8n-io/nod/compare/1128fcfd770d619f3391e0bd9f1ca2f9966f2be6...nod-v0.10.3
