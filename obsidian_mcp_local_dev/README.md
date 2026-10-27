# Obsidian MCP Local (Development)

Isolated test app for the local Markdown folder option. Separate Home Assistant slug and `/data` from production. Default test folder: `/share/obsidian-prueba-local` (create it before starting).

**Do not enable tunnel or LiveSync**; this staging build deliberately refuses both. Use only non-sensitive test notes. The app has writable access to `/share` but does not mount `all_app_configs`.

Install only after merging into repository main or using a separate published test repository; the feature branch itself is not served by Home Assistant add-on catalog.
