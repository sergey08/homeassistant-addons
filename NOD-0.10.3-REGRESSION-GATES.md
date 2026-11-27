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

The CI migration first passed at `320e6bd` using the exact dev.34 source. It checks synthetic chat history, preferences, a memory note, an encrypted Vault entry, a configured model, an authenticated MCP connector, a disabled schedule, an artifact, options and keys after upgrade and restart. The stopped dev.34 volume is restored to a separate volume and verified with dev.34. See [the native-app run](https://github.com/sergey08/homeassistant-addons/actions/runs/46072567455).

The current CI uses the digest-pinned, previously published dev.34 Server and dev.6 Workspace images as upgrade sources. Workspace CI checks the existing private workspace and Supervisor options through container replacement and restart, alongside its isolation and real worker task tests. The database and file archive is private to the runner and is discarded. Test fixtures contain only synthetic data.

The staged test version set is Server 0.1.0-dev.35, Browser 0.1.0-dev.7 and Workspace 0.1.0-dev.7. The gates above determine whether the versions can be installed for validation. Image push and anonymous pull checks must agree before any install. Real provider OAuth and Supervisor backup/restore require separate evidence on Home Assistant. See [the validation and rollback guide](docs/nod/0.10.3-validation.md).
