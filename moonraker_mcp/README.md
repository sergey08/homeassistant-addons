# Moonraker MCP for Home Assistant (DEV)

Experimental Home Assistant OS add-on packaging [lexfrei/mcp-raker](https://github.com/lexfrei/mcp-raker) (BSD-3-Clause).

**Not ready for installation.** The upstream image entrypoint, binary location and availability of `jq` must be validated; the current Dockerfile and startup script are scaffolding, not a tested build.

- Runs the upstream Moonraker MCP server as an isolated add-on.
- HTTP MCP on container port 8765, bearer token required.
- Moonraker URL and optional API key in add-on options.
- Admin tools disabled, **but printing/G-code/restart tools are still exposed** by upstream. Treat all clients as privileged.
- Do not publish the MCP port to the internet. Use authenticated TLS reverse proxy only after testing.
- Does not modify the printer or existing Home Assistant integrations.

## Next
1. Inspect upstream container filesystem, entrypoint and runtime dependencies.
2. Replace provisional Dockerfile and startup with verified commands.
3. Pin a reviewed upstream image digest/version.
4. Build in DEV and test with the printer in read-only workflows.
5. Confirm compatibility with ChatGPT's remote MCP transport/authentication.
6. Add Spanish/English documentation and release after review.

## Español
Complemento experimental para ejecutar el MCP existente de Moonraker en Home Assistant OS. **No está listo para instalar** hasta validar la imagen y el arranque. Las herramientas de impresión siguen pudiendo actuar sobre la máquina aunque se deshabiliten las funciones administrativas.
