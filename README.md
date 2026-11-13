# SeRgEY — Home Assistant Apps / Aplicaciones para Home Assistant

**EN:** Open-source Home Assistant apps, distributed through one repository.  
**ES:** Aplicaciones de código abierto para Home Assistant, distribuidas desde un único repositorio.

[![Add this repository to Home Assistant](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fsergey08%2Fhomeassistant-addons)

## English

### One-click repository setup

Click the **Add Repository** badge above. Choose your Home Assistant instance and confirm adding this repository.

If needed, open **Settings → Apps → App Store → ⋮ → Repositories** and paste:

```text
https://github.com/sergey08/homeassistant-addons
```

### Available apps

**Obsidian MCP for Home Assistant — 0.2.6 (stable)**

- Local Markdown or Self-hosted LiveSync + optional OpenAI Secure MCP Tunnel for ChatGPT.

[App source](./obsidian_suite/) · [Documentation](./obsidian_suite/DOCS.md)

**Obsidian MCP for Home Assistant (Beta) — 0.2.7-beta.1 (optional)**

- Appears **next to** the stable add-on in Home Assistant Applications.
- Same features as 0.2.6 plus optional authenticated remote MCP for **Grok**.
- Separate data path (`/app_configs/obsidian_bridge_beta`). Does not auto-replace the stable install.

[App source](./obsidian_suite_beta/) · Branch: `feature/remote-mcp-auth-grok`

**Obsidian Client — 0.1.0-dev2 (experimental)** and **Moonraker MCP — v0.1.0** — see folders in this repository.

### Contributing and security

Use **Issues** and **Pull requests**. Do not publish secrets or private vault contents.

## Español

**Obsidian MCP for Home Assistant — 0.2.6 (estable)** y **Obsidian MCP for Home Assistant (Beta) — 0.2.7-beta.1 (opcional)** aparecen como **dos aplicaciones distintas** en Home Assistant.

La beta añade MCP remoto autenticado para Grok y no sustituye la estable.

---

## License / Licencia

[MIT](./LICENSE).
