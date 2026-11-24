#!/bin/sh
set -eu
umask 077
root=/data/nod-native-v1
mkdir -p "$root"
chmod 0711 "$root"
server_pid=
socket=$(mktemp -d /tmp/nod-pg.XXXXXX)
chown postgres:postgres "$socket"
cleanup() {
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
export NOD_DATA_ROOT="$root/nod" NOD_AUTH_TOKEN="$token" NOD_VAULT_KEY="$vault"
export DATABASE_URL="postgresql://nod:$password@127.0.0.1:5432/nod"
export DOCKER_HOST=tcp://127.0.0.1:2375 WORKSPACE_CONTAINER=nod-workspace-unavailable BROWSER_CONTAINER=nod-browser-unavailable
export HOME=/home/node
gosu node node --import tsx src/server/index.ts > "$root/server.log" 2>&1 &
server_pid=$!
for attempt in $(seq 1 90); do
    if gosu node node /app/healthcheck.mjs >/dev/null 2>&1; then
        echo NOD_NATIVE_SERVER_HEALTH_OK
        echo 'PASS: native Nod and PostgreSQL running persistently on loopback'
        while kill -0 "$server_pid" 2>/dev/null && gosu postgres pg_ctl -D "$root/db" status >/dev/null 2>&1; do
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
