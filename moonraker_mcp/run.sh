#!/bin/sh
set -eu
OPTIONS=/data/options.json
if [ ! -f "$OPTIONS" ]; then
  echo "Missing Home Assistant options" >&2
  exit 1
fi
if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required in the upstream image; packaging must be adapted" >&2
  exit 1
fi
export MOONRAKER_URL="$(jq -r '.moonraker_url' "$OPTIONS")"
export MOONRAKER_API_KEY="$(jq -r '.moonraker_api_key // ""' "$OPTIONS")"
export MCP_HTTP_TOKEN="$(jq -r '.mcp_http_token // ""' "$OPTIONS")"
if [ -z "$MCP_HTTP_TOKEN" ]; then
  echo "Configure a nonempty MCP HTTP token" >&2
  exit 1
fi
export MCP_HTTP_HOST=0.0.0.0
export MCP_HTTP_PORT=8765
export MOONRAKER_ENABLE_ADMIN=false
exec /mcp-raker
