#!/bin/sh
set -eu
umask 077
root=/data/nod-native-v1
mkdir -p "$root"
chmod 0711 "$root"
server_pid=
ingress_pid=
relay_pid=
bridge_pid=
diagnostic_pid=
relay_origin=
ha_ancestor=
ingress_origin=
socket=$(mktemp -d /tmp/nod-pg.XXXXXX)
chown postgres:postgres "$socket"
cleanup() {
    if [ -n "$diagnostic_pid" ]; then
        kill "$diagnostic_pid" 2>/dev/null || true
        wait "$diagnostic_pid" 2>/dev/null || true
    fi
    if [ -n "$bridge_pid" ]; then
        kill "$bridge_pid" 2>/dev/null || true
        wait "$bridge_pid" 2>/dev/null || true
    fi
    if [ -n "$relay_pid" ]; then
        kill "$relay_pid" 2>/dev/null || true
        wait "$relay_pid" 2>/dev/null || true
    fi
    rm -rf /run/nod-relay /run/nod-browser-client
    if [ -n "$ingress_pid" ]; then
        kill "$ingress_pid" 2>/dev/null || true
        wait "$ingress_pid" 2>/dev/null || true
    fi
    if [ -n "$server_pid" ]; then
        kill "$server_pid" 2>/dev/null || true
        wait "$server_pid" 2>/dev/null || true
    fi
    gosu postgres pg_ctl -D "$root/db" -m fast -w stop >/dev/null 2>&1 || true
    rm -rf -- "$socket"
}
trap cleanup EXIT
trap 'exit 0' TERM INT
if [ ! -f "$root/secrets" ]; then
    [ ! -e "$root/db" ] && [ ! -e "$root/nod" ] || { echo 'FAIL: missing persistent secrets'; exit 1; }
    temp=$(mktemp "$root/secrets.XXXXXX")
    { openssl rand -hex 32; openssl rand -hex 32; openssl rand -base64 32; } > "$temp"
    chmod 0600 "$temp"
    mv "$temp" "$root/secrets"
fi
chmod 0600 "$root/secrets"
{
    IFS= read -r password
    IFS= read -r token
    IFS= read -r vault
} < "$root/secrets"
printf '%s\n%s\n' "$password" "$token" | grep -Eq '^[0-9a-f]{64}$'
[ "${#password}" -eq 64 ] && [ "${#token}" -eq 64 ]
case "$password$token" in *[!0-9a-f]*) echo 'FAIL: malformed persistent credentials'; exit 1;; esac
printf '%s\n' "$vault" | grep -Eq '^[A-Za-z0-9+/]{43}=$'
if [ ! -e "$root/db" ]; then
    newdb=$(mktemp -d "$root/db-init.XXXXXX")
    chown postgres:postgres "$newdb"
    gosu postgres initdb -D "$newdb" --auth-local=peer --auth-host=scram-sha-256 -U postgres >/dev/null
    mv "$newdb" "$root/db"
    echo NOD_NATIVE_STORAGE_CREATED
else
    [ -f "$root/db/PG_VERSION" ] || { echo 'FAIL: incomplete persistent database'; exit 1; }
    echo NOD_NATIVE_STORAGE_REUSED
fi
mkdir -p "$root/nod"
chown node:node "$root/nod"
chmod 0700 "$root/nod"
gosu postgres pg_ctl -D "$root/db" -l "$root/db/server.log" -o "-h 127.0.0.1 -p 5432 -k $socket" -w start >/dev/null
{
    printf "SELECT 'CREATE ROLE nod LOGIN PASSWORD ''%s''' WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname='nod');\n" "$password"
    printf '\\gexec\n'
    printf "SELECT 'CREATE DATABASE nod OWNER nod' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname='nod');\n"
    printf '\\gexec\n'
} | gosu postgres psql -h "$socket" -U postgres -v ON_ERROR_STOP=1 -q postgres >/dev/null
echo NOD_NATIVE_POSTGRES_OK
export NODE_ENV=production NOD_ENVIRONMENT=production NOD_HOST=127.0.0.1 PORT=4310 NOD_PUBLIC_URL=http://localhost:4310
if [ -f /data/options.json ]; then
    relay_origin=$(node /app/relay-config.mjs) || { echo 'FAIL: invalid HTTPS configuration'; exit 1; }
fi
if [ -n "$relay_origin" ]; then
    NOD_PUBLIC_URL="$relay_origin"
    ha_ancestor=$(node -p 'JSON.parse(require("node:fs").readFileSync("/run/nod-relay/settings.json","utf8")).haAncestor || ""')
    if [ -n "$ha_ancestor" ]; then ingress_origin="$relay_origin"; fi
    token=$(cat /run/nod-relay/token)
    rm -f /run/nod-relay/token
fi
export NOD_DATA_ROOT="$root/nod" NOD_AUTH_TOKEN="$token" NOD_VAULT_KEY="$vault"
export DATABASE_URL="postgresql://nod:$password@127.0.0.1:5432/nod"
export DOCKER_HOST=tcp://127.0.0.1:2375 WORKSPACE_CONTAINER=nod-workspace-unavailable BROWSER_CONTAINER=nod-browser-unavailable
export HOME=/home/node
rm -rf /run/nod-browser-client
NOD_HA_BROWSER_REMOTE=
if browser_flag=$(node /app/browser-config.mjs) && [ "$browser_flag" = 1 ]; then
    NOD_HA_BROWSER_REMOTE=1
    echo NOD_BROWSER_CLIENT_CONFIGURED
fi
export NOD_HA_BROWSER_REMOTE
gosu node node --import tsx src/server/index.ts > "$root/server.log" 2>&1 &
server_pid=$!
for attempt in $(seq 1 90); do
    if gosu node node /app/healthcheck.mjs >/dev/null 2>&1; then
        echo NOD_NATIVE_SERVER_HEALTH_OK
        env -i PATH=/usr/local/bin:/usr/bin:/bin gosu nodrelay node /app/ha-mcp-bridge.mjs &
        bridge_pid=$!
        for i in $(seq 1 10); do
            if node -e 'fetch("http://127.0.0.1:9591/mcp").then(r=>process.exit(r.status===401?0:1)).catch(()=>process.exit(1))'; then break; fi
            sleep 1
        done
        node -e 'fetch("http://127.0.0.1:9591/mcp").then(r=>process.exit(r.status===401?0:1)).catch(()=>process.exit(1))' || { echo 'FAIL: HA MCP bridge not listening'; exit 1; }
        if [ -n "$relay_origin" ]; then
            env -i PATH=/usr/local/bin:/usr/bin:/bin gosu nodrelay node /app/relay-start.mjs &
            relay_pid=$!
            for i in $(seq 1 10); do
                if node -e 'const s=require("node:net").connect(8443,"127.0.0.1");s.on("connect",()=>{s.destroy();process.exit(0)});s.on("error",()=>process.exit(1))'; then break; fi
                sleep 1
            done
            node -e 'const s=require("node:net").connect(8443,"127.0.0.1");s.on("connect",()=>{s.destroy();process.exit(0)});s.on("error",()=>process.exit(1))' || { echo 'FAIL: HTTPS relay not listening'; exit 1; }
        fi
        env -i PATH=/usr/local/bin:/usr/bin:/bin HOME=/home/node NOD_INGRESS_NOD_ORIGIN="$ingress_origin" NOD_INGRESS_HA_ORIGIN="$ha_ancestor" gosu node node /app/ingress.mjs &
        ingress_pid=$!
        for i in $(seq 1 10); do
            if node -e 'fetch("http://127.0.0.1:8099/").then(r=>{process.exit(r.status===403?0:1)}).catch(()=>process.exit(1))'; then break; fi
            sleep 1
        done
        node -e 'fetch("http://127.0.0.1:8099/").then(r=>{process.exit(r.status===403?0:1)}).catch(()=>process.exit(1))' || { echo 'FAIL: ingress access restriction'; exit 1; }
        echo NOD_NATIVE_INGRESS_DIRECT_DENIED
        echo 'PASS: native Nod and PostgreSQL running persistently on loopback'
        if [ "$NOD_HA_BROWSER_REMOTE" = 1 ]; then
            env -i PATH=/usr/local/bin:/usr/bin:/bin HOME=/home/node NOD_HA_BROWSER_REMOTE=1 gosu node node --import tsx /app/browser-diagnostic.mjs &
            diagnostic_pid=$!
        fi
        while kill -0 "$bridge_pid" 2>/dev/null && kill -0 "$server_pid" 2>/dev/null && kill -0 "$ingress_pid" 2>/dev/null && { [ -z "$relay_pid" ] || kill -0 "$relay_pid" 2>/dev/null; } && gosu postgres pg_ctl -D "$root/db" status >/dev/null 2>&1; do
            sleep 5 &
            wait $!
        done
        echo 'FAIL: persistent service stopped'
        exit 1
    fi
    kill -0 "$server_pid" 2>/dev/null || break
    sleep 2
done
echo 'FAIL: native server health check'
exit 1
