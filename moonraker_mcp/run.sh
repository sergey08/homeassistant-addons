#!/bin/sh
set -eu
OPTIONS=/data/options.json
if [ ! -f "$OPTIONS" ]; then
  echo "Missing Home Assistant options" >&2
  exit 1
fi
MOONRAKER_URL="$(jq -er '.moonraker_url | select(type=="string" and length>0)' "$OPTIONS")"
export MOONRAKER_URL
MOONRAKER_API_KEY="$(jq -er 'if .moonraker_api_key == null then "" else .moonraker_api_key | select(type=="string") end' "$OPTIONS")"
export MOONRAKER_API_KEY
MCP_HTTP_TOKEN="$(jq -er 'if .mcp_http_token == null then "" else .mcp_http_token | select(type=="string") end' "$OPTIONS")"
export MCP_HTTP_TOKEN
MCP_ENABLE_TUNNEL="$(jq -r 'if .enable_tunnel == null then "false" elif (.enable_tunnel | type) == "boolean" then (.enable_tunnel | tostring) else error("enable_tunnel must be boolean") end' "$OPTIONS")"
MCP_TUNNEL_ID="$(jq -er 'if .tunnel_id == null then "" else .tunnel_id | select(type=="string") end' "$OPTIONS")"
export MCP_TUNNEL_ID
if [ -z "$MCP_HTTP_TOKEN" ]; then
  echo "Configure a nonempty MCP HTTP token" >&2
  exit 1
fi
MCP_ALLOWED_PROFILES="$(jq -ecr '[["jobqueue", .enable_jobqueue], ["files", .enable_files], ["objects", .enable_objects], ["history", .enable_history], ["sensors", .enable_sensors], ["spoolman", .enable_spoolman], ["power", .enable_power]] | if all(.[]; .[1] == null or (.[1] | type) == "boolean") then map(select(.[1] == true) | .[0]) else error("Optional MCP profiles must be boolean") end' "$OPTIONS")"
export MCP_ALLOWED_PROFILES
# Fail before starting the gateway if the optional tunnel cannot authenticate.
# The tunnel process runs as UID 65534; do not loosen private key permissions.
if [ "$MCP_ENABLE_TUNNEL" = "true" ]; then
  if [ -z "$MCP_TUNNEL_ID" ] ||
     [ ! -f /data/tunnel/api-key ] ||
     [ ! -f /data/tunnel/bin/tunnel-client ] ||
     ! su-exec 65534:65534 test -r /data/tunnel/api-key ||
     ! su-exec 65534:65534 test -x /data/tunnel/bin/tunnel-client; then
    echo "Tunnel configuration incomplete or inaccessible to runtime UID" >&2
    exit 1
  fi
  if ! python3 -c 'import os,stat; p="/data/tunnel/api-key"; s=os.stat(p); assert stat.S_ISREG(s.st_mode) and not (s.st_mode & 0o077) and s.st_uid == 65534'; then
    echo "Tunnel API key must be a private regular file owned by UID 65534" >&2
    exit 1
  fi
fi
export MCP_HTTP_HOST=127.0.0.1
export MCP_HTTP_PORT=8766
export MOONRAKER_ENABLE_ADMIN=false
export MOONRAKER_TOKEN_FILE=/data/moonraker-token.json
# Keep upstream bound to loopback. Never expose its unfiltered tool set.
# Keep stdin open: upstream serves both stdio and HTTP and exits when stdio closes.
mkfifo /run/moonraker-stdin
chown 65534:65534 /run/moonraker-stdin
# Redirections are executed by the shell, so run the shells as the
# unprivileged FIFO owner as well. Supervisor containers may lack DAC override.
su-exec 65534:65534 sh -c 'exec tail -f /dev/null > /run/moonraker-stdin' &
KEEPALIVE_PID=$!
su-exec 65534:65534 sh -c 'exec /usr/local/bin/mcp-raker < /run/moonraker-stdin' &
UPSTREAM_PID=$!
TUNNEL_PID=""
cleanup() {
  if [ -n "$TUNNEL_PID" ]; then
    kill "$TUNNEL_PID" 2>/dev/null || true
  fi
  kill "$UPSTREAM_PID" "$KEEPALIVE_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM
cd /opt/moonraker-mcp
if [ "$MCP_ENABLE_TUNNEL" = "true" ]; then
  # Dedicated loopback bridge injects the bearer token without passing it in
  # tunnel-client command arguments or exposing an unauthenticated HA port.
  su-exec 65534:65534 python3 -u tunnel_runtime.py &
  TUNNEL_PID=$!
fi
su-exec 65534:65534 python3 -u gateway.py
