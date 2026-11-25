#!/bin/sh
# Offline by default. Optional authenticated fixed-command probe, no general execution.
set -eu
export XTABLES_LOCKFILE=/tmp/nod-workspace-xtables.lock
[ "$(ls /sys/class/net | sort | tr '\n' ' ')" = 'eth0 lo ' ] || { echo 'FAIL: unexpected workspace network interfaces'; exit 1; }
rm -rf /run/nod-workspace-gateway /run/nod-workspace
peer=$(node /app/prepare-config.mjs) || exit 1
ip6tables-restore --wait 10 <<'RULES'
*filter
:INPUT DROP [0:0]
:FORWARD DROP [0:0]
:OUTPUT DROP [0:0]
-A INPUT -i lo -j ACCEPT
-A OUTPUT -o lo -j ACCEPT
COMMIT
RULES
{
    printf '%s\n' '*filter' ':INPUT DROP [0:0]' ':FORWARD DROP [0:0]' ':OUTPUT DROP [0:0]' '-A INPUT -i lo -j ACCEPT' '-A OUTPUT -o lo -j ACCEPT'
    if [ -n "$peer" ]; then
        printf '%s\n' "-A INPUT -s $peer/32 -p tcp --dport 9593 -m conntrack --ctstate NEW,ESTABLISHED -j ACCEPT" "-A OUTPUT -d $peer/32 -p tcp --sport 9593 -m conntrack --ctstate ESTABLISHED -j ACCEPT"
    fi
    printf '%s\n' COMMIT
} | iptables-restore --wait 10
echo NOD_WORKSPACE_OFFLINE_FIREWALL_READY
[ -d /data ] && [ ! -L /data ] || exit 1
chown 0:0 /data
chmod 0711 /data
if [ -e /data/options.json ]; then
    [ -f /data/options.json ] && [ ! -L /data/options.json ] || exit 1
    chown 0:0 /data/options.json
    chmod 0600 /data/options.json
fi
for dir in /data/workspaces /data/workspace-home; do
    [ ! -L "$dir" ] || exit 1
    mkdir -p "$dir"
    chown 1000:1000 "$dir"
    chmod 0700 "$dir"
done
if [ -L /workspace ]; then
    [ "$(readlink /workspace)" = /data/workspaces ] || exit 1
else
    [ -d /workspace ] || exit 1
    rmdir /workspace
    ln -s /data/workspaces /workspace
fi
[ -d /home/node ] && [ ! -L /home/node ] || exit 1
# Preserve the image home; use a separate private persistent HOME.
cd /workspace
as_worker() {
    env -i PATH=/opt/nod-artifacts/bin:/usr/local/bin:/usr/bin:/bin HOME=/data/workspace-home LANG=C.UTF-8 setpriv --reuid=1000 --regid=1000 --clear-groups --no-new-privs --bounding-set=-all --inh-caps=-all --ambient-caps=-all "$@"
}
if [ -z "$peer" ]; then
    exec env -i PATH=/opt/nod-artifacts/bin:/usr/local/bin:/usr/bin:/bin HOME=/data/workspace-home LANG=C.UTF-8 setpriv --reuid=1000 --regid=1000 --clear-groups --no-new-privs --bounding-set=-all --inh-caps=-all --ambient-caps=-all /opt/nod-artifacts/bin/python /opt/nod-workspace-selftest.py
fi
as_worker /opt/nod-artifacts/bin/python /opt/nod-workspace-selftest.py --once
mkdir -m 0750 /run/nod-workspace
chown 1000:1000 /run/nod-workspace
worker_pid=
gateway_pid=
cleanup() {
    [ -z "$gateway_pid" ] || kill "$gateway_pid" 2>/dev/null || true
    [ -z "$worker_pid" ] || kill "$worker_pid" 2>/dev/null || true
    [ -z "$gateway_pid" ] || wait "$gateway_pid" 2>/dev/null || true
    [ -z "$worker_pid" ] || wait "$worker_pid" 2>/dev/null || true
    rm -rf /run/nod-workspace-gateway /run/nod-workspace
}
trap cleanup EXIT
trap 'exit 0' TERM INT
env -i PATH=/opt/nod-artifacts/bin:/usr/local/bin:/usr/bin:/bin HOME=/data/workspace-home LANG=C.UTF-8 setpriv --reuid=1000 --regid=1000 --clear-groups --no-new-privs --bounding-set=-all --inh-caps=-all --ambient-caps=-all node /app/probe-worker.mjs &
worker_pid=$!
for i in $(seq 1 15); do
    if as_worker test -S /run/nod-workspace/control.sock; then break; fi
    kill -0 "$worker_pid" || exit 1
    sleep 1
done
as_worker test -S /run/nod-workspace/control.sock || exit 1
env -i PATH=/usr/local/bin:/usr/bin:/bin setpriv --reuid=1001 --regid=1000 --clear-groups --no-new-privs --bounding-set=-all --inh-caps=-all --ambient-caps=-all node /app/transport.mjs gateway /run/nod-workspace-gateway/settings.json &
gateway_pid=$!
while kill -0 "$worker_pid" && kill -0 "$gateway_pid"; do
    sleep 2 & wait $!
done
exit 1
