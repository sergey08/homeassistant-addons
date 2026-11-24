#!/bin/sh
set -eu
umask 077
root=$(mktemp -d /tmp/nod-native.XXXXXX)
chmod 0711 "$root"
server_pid=
cleanup() {
    if [ -n "$server_pid" ]; then
        kill "$server_pid" 2>/dev/null || true
        wait "$server_pid" 2>/dev/null || true
    fi
    gosu postgres pg_ctl -D "$root/db" -m fast -w stop >/dev/null 2>&1 || true
    rm -rf -- "$root"
}
trap cleanup EXIT
trap 'exit 0' TERM INT
mkdir "$root/db" "$root/socket" "$root/nod"
chown postgres:postgres "$root/db" "$root/socket"
chown node:node "$root/nod"
chmod 0700 "$root/db" "$root/socket" "$root/nod"
password=$(openssl rand -hex 32)
gosu postgres initdb -D "$root/db" --auth-local=peer --auth-host=scram-sha-256 -U postgres >/dev/null
gosu postgres pg_ctl -D "$root/db" -o "-h 127.0.0.1 -p 5432 -k $root/socket" -w start >/dev/null
printf "CREATE ROLE nod LOGIN PASSWORD '%s';\nCREATE DATABASE nod OWNER nod;\n" "$password" | gosu postgres psql -h "$root/socket" -U postgres -v ON_ERROR_STOP=1 -q postgres
echo NOD_NATIVE_POSTGRES_OK
export NODE_ENV=production NOD_ENVIRONMENT=production NOD_HOST=127.0.0.1 PORT=4310 NOD_PUBLIC_URL=http://localhost:4310
export NOD_DATA_ROOT="$root/nod" NOD_AUTH_TOKEN="$(openssl rand -hex 32)" NOD_VAULT_KEY="$(openssl rand -base64 32)"
export DATABASE_URL="postgresql://nod:$password@127.0.0.1:5432/nod"
export DOCKER_HOST=tcp://127.0.0.1:2375 WORKSPACE_CONTAINER=nod-workspace-unavailable BROWSER_CONTAINER=nod-browser-unavailable
export HOME=/home/node
gosu node node --import tsx src/server/index.ts > "$root/server.log" 2>&1 &
server_pid=$!
for attempt in $(seq 1 90); do
    if gosu node node /app/healthcheck.mjs >/dev/null 2>&1; then
        echo NOD_NATIVE_SERVER_HEALTH_OK
        cleanup
        trap - EXIT
        echo 'PASS: native Nod and PostgreSQL; no VM or host Docker socket'
        sleep infinity &
        wait $!
        exit 0
    fi
    kill -0 "$server_pid" 2>/dev/null || break
    sleep 2
done
echo 'FAIL: native server health check'
exit 1
