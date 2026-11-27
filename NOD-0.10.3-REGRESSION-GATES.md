# Nod 0.10.3 candidate — mandatory regression and release gates

Baseline: deployed Server 0.1.0-dev.34, Browser and Workspace dev.6 (upstream nod-v0.9.7), distribution source 5487ed948e31b0f32eb75f71f98e4ce577aec76f. Candidate: nod-v0.10.3, immutable commit 8494bcf12030451ad1093f0579bba57caf34c1d9.

Do not publish or deploy this research branch. Existing app versions and public image tags must not be reused for changed images. Preserve all HA-specific patches and tests unless upstream provides an equivalent feature and replacement is tested. Never bypass a failing patch anchor or weaken authorization/network isolation to obtain a successful build.

| Gate | Required evidence before release |
|---|---|
| Ingress | Local HTTP and HA-managed HTTPS, mobile/desktop UI, authentication, streaming, asset URLs, downloads, navigation, settings, onboarding; deny unauthorized access |
| Certificate-free onboarding | Normal Ingress/internal communication works without manual certificate creation, installation or import; maintain existing authenticated transport and optional HTTPS; never disable TLS verification globally |
| Chat | Reload models (including empty/chunked POST), chat history, restart-context valid and invalid recovery, memory read/export, settings and preferences |
| Accounts and models | Model OAuth, local OpenAI-compatible discovery/refresh, model selection and routing, connector discovery/permissions; actual provider login/chat separately validated; personal Ollama performance is not a public beta gate |
| Computer use | Headless status is informative; no desktop control or host access through HA |
| Browser and Workspace | Real worker tasks, compatible protocol, authenticated transport, network boundaries, resource limits and artifact generation |
| Data migration | From dev.34, retain synthetic chats, preferences, memory, schedules, model/connector settings, database and encryption keys; confirm restart and restoration of a matched pre-upgrade backup |
| Distribution | Fresh immutable component tags, compatible version set, anonymous image pull, clean install and interrupted upgrade; retain dev.34 and previous data for rollback |

Existing automated tests are retained. The migration workflow now builds the exact dev.34 source as the previous image; its generic database sentinel and secrets fingerprint are only partial evidence, not proof that all application data survives. Expand fixtures for real app data and restoration and record manual checks before promotion. Tests must not use production credentials, data or keys. No production update until validation and owner approval.

Status: the server, Browser, pin consistency, worker recovery and resource admission CI passed at `151ca6a`. Server CI covered the original web authentication, the previous database marker, native HTTPS, embedded Chromium, Ingress authorization and Vault list/activity, artifacts, connector bridge and local model regressions. See [the native-app run](https://github.com/sergey08/homeassistant-addons/actions/runs/46071407516).

The expanded migration check in `.github/workflows/nod-native-app.yml` seeds the exact dev.34 image with synthetic chats, preferences, memory, an encrypted Vault entry, a configured model, an authenticated MCP connector, a disabled schedule and an artifact. It checks those records, options and keys after the upgrade and a restart. It also restores the stopped dev.34 volume to a new volume and verifies the contents while running dev.34. The archive is private to the runner and is discarded. Real provider OAuth and HA Supervisor backup/restore still require isolated Home Assistant validation.
