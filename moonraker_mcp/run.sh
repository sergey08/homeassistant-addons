#!/bin/sh
set -eu
OPTIONS=/data/options.json
if [ ! -f "$OPTIONS" ]; then
  echo "Missing Home Assistant options" >&2
  exit 1
fi
export MOONRAKER_URL="$(jq -er '.moonraker_url | select(type=="string" and length>0)' "$OPTIONS")"
export MOONRAKER_API_KEY="$(jq -r '.moonraker_api_key // ""' "$OPTIONS")"
export MCP_HTTP_TOKEN="$(jq -r '.mcp_http_token // ""' "$OPTIONS")"
if [ -z "$MCP_HTTP_TOKEN" ]; then
  echo "Configure a nonempty MCP HTTP token" >&2
  exit 1
fi
export MCP_ALLOWED_PROFILES="$(jq -ecr '[["files", .enable_files], ["objects", .enable_objects], ["history", .enable_history], ["sensors", .enable_sensors], ["spoolman", .enable_spoolman], ["power", .enable_power]] | if all(.[]; .[1] == null or (.[1] | type) == "boolean") then map(select(.[1] == true) | .[0]) else error("Optional MCP profiles must be boolean") end' "$OPTIONS")"
export MCP_HTTP_HOST=127.0.0.1
export MCP_HTTP_PORT=8766
export MOONRAKER_ENABLE_ADMIN=false
export MOONRAKER_TOKEN_FILE=/data/moonraker-token.json
# Keep upstream bound to loopback. Never expose its unfiltered tool set.
# Keep stdin open: upstream serves both stdio and HTTP and exits when stdio closes.
mkfifo /tmp/moonraker-stdin
tail -f /dev/null > /tmp/moonraker-stdin &
KEEPALIVE_PID=$!
/usr/local/bin/mcp-raker < /tmp/moonraker-stdin &
UPSTREAM_PID=$!
trap 'kill "$UPSTREAM_PID" "$KEEPALIVE_PID" 2>/dev/null || true' EXIT INT TERM
cd /opt/moonraker-mcp
python3 -u gateway.py
