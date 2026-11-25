#!/bin/sh
# This first preflight is strictly offline. No listening socket or remote commands.
set -eu
export XTABLES_LOCKFILE=/tmp/nod-workspace-xtables.lock
[ "$(ls /sys/class/net | sort | tr '\n' ' ')" = 'eth0 lo ' ] || { echo 'FAIL: unexpected workspace network interfaces'; exit 1; }
for cmd in iptables-restore ip6tables-restore; do
    "$cmd" --wait 10 <<'RULES'
*filter
:INPUT DROP [0:0]
:FORWARD DROP [0:0]
:OUTPUT DROP [0:0]
-A INPUT -i lo -j ACCEPT
-A OUTPUT -o lo -j ACCEPT
COMMIT
RULES
done
echo NOD_WORKSPACE_OFFLINE_FIREWALL_READY
[ -d /data ] && [ ! -L /data ] || exit 1
chown 0:0 /data
chmod 0711 /data
for dir in /data/workspaces /data/workspace-home; do
    [ ! -L "$dir" ] || exit 1
    mkdir -p "$dir"
    chown 1000:1000 "$dir"
    chmod 0700 "$dir"
done
[ -d /workspace ] && [ ! -L /workspace ] || exit 1
rmdir /workspace
ln -s /data/workspaces /workspace
[ -d /home/node ] && [ ! -L /home/node ] || exit 1
# Preserve the image home; use a separate private persistent HOME.
cd /workspace
exec env -i PATH=/opt/nod-artifacts/bin:/usr/local/bin:/usr/bin:/bin HOME=/data/workspace-home LANG=C.UTF-8 setpriv --reuid=1000 --regid=1000 --clear-groups --no-new-privs --bounding-set=-all --inh-caps=-all --ambient-caps=-all /opt/nod-artifacts/bin/python /opt/nod-workspace-selftest.py
