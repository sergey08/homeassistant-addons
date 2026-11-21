#!/usr/bin/env bash
# Run the packaged CLI in the unmodified Core image against an isolated CouchDB.
set -euo pipefail
bundle=$(realpath "$1")
data=$(mktemp -d)
cleanup() {
    docker logs obsidian-livesync-smoke 2>&1 | tail -50 || true
    docker logs obsidian-couchdb 2>&1 | tail -20 || true
    docker rm -f obsidian-livesync-smoke obsidian-couchdb >/dev/null 2>&1 || true
    docker network rm obsidian-livesync-ci >/dev/null 2>&1 || true
    rm -r -- "$data"
}
trap cleanup EXIT

mkdir "$data/vault" "$data/db"
printf '# LiveSync integration smoke test\n' > "$data/vault/integration.md"
cat > "$data/settings.json" <<'JSON'
{"couchDB_URI":"http://obsidian-couchdb:5984","couchDB_USER":"testadmin","couchDB_PASSWORD":"ci-password","couchDB_DBNAME":"obsidian-ci","encrypt":false,"isConfigured":true}
JSON

docker network create obsidian-livesync-ci
couchdb=$(docker run -d --name obsidian-couchdb --network obsidian-livesync-ci \
    -p 127.0.0.1::5984 -e COUCHDB_USER=testadmin -e COUCHDB_PASSWORD=ci-password couchdb:3.4)
couch="http://$(docker port "$couchdb" 5984/tcp)"
curl -fsS --retry 25 --retry-all-errors --retry-delay 2 --max-time 3 "$couch/_up"
curl -fsS -u testadmin:ci-password -H 'Content-Type: application/json' \
    --data '{"action":"enable_single_node","bind_address":"0.0.0.0","username":"testadmin","password":"ci-password","port":5984}' \
    "$couch/_cluster_setup"
curl -fsS -u testadmin:ci-password -X PUT "$couch/obsidian-ci"

docker run -d --name obsidian-livesync-smoke --network obsidian-livesync-ci \
    --user "$(id -u):$(id -g)" -e HOME=/fixtures -e LIVESYNC_DB_PATH=/fixtures/db -v "$data:/fixtures" -v "$bundle:/config/obsidian_mcp:ro" \
    --entrypoint /config/obsidian_mcp/bin/livesync-cli ghcr.io/home-assistant/home-assistant:2026.9.4 \
    --settings /fixtures/settings.json --vault /fixtures/vault --interval 30
for attempt in $(seq 1 45); do
    if curl -fsS -u testadmin:ci-password "$couch/obsidian-ci/_all_docs?include_docs=true" | grep -Fiq 'integration.md'; then
        exit 0
    fi
    if [ "$(docker inspect -f '{{.State.Running}}' obsidian-livesync-smoke)" != true ]; then
        exit 1
    fi
    sleep 2
done
curl -fsS -u testadmin:ci-password "$couch/obsidian-ci/_all_docs?include_docs=true"
exit 1
