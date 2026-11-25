#!/bin/sh
# Dedicated app network namespace only. Never use host networking.
set -eu
export XTABLES_LOCKFILE=/tmp/nod-browser-xtables.lock
# Refuse unexpected networking; this is a secondary check, not a substitute
# for Supervisor's host_network: false setting.
[ "$(ls /sys/class/net | sort | tr '\n' ' ')" = 'eth0 lo ' ] || { echo 'FAIL: unexpected browser network interfaces'; exit 1; }
[ -d /data ] && [ ! -L /data ] || { echo 'FAIL: invalid private data directory'; exit 1; }
chown 0:0 /data
chmod 0711 /data
[ ! -L /data/browser ] || exit 1
mkdir -p /data/browser
chown 1000:1000 /data/browser
chmod 0700 /data/browser
mkdir -p /run/nod-browser
chown 1000:1000 /run/nod-browser
chmod 0750 /run/nod-browser
peer=$(node /app/prepare-config.mjs) || exit 1
worker_pid=
gateway_pid=
cleanup() {
    [ -z "$gateway_pid" ] || kill "$gateway_pid" 2>/dev/null || true
    [ -z "$worker_pid" ] || kill "$worker_pid" 2>/dev/null || true
    [ -z "$gateway_pid" ] || wait "$gateway_pid" 2>/dev/null || true
    [ -z "$worker_pid" ] || wait "$worker_pid" 2>/dev/null || true
    rm -rf /run/nod-browser-gateway
}
trap cleanup EXIT
trap 'exit 0' TERM INT
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
  printf '%s\n' '*filter' ':INPUT DROP [0:0]' ':FORWARD DROP [0:0]' ':OUTPUT DROP [0:0]' '-A INPUT -i lo -j ACCEPT' '-A OUTPUT -o lo -j ACCEPT' '-A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT'
  if [ -n "$peer" ]; then
    printf '%s\n' "-A INPUT -s $peer/32 -p tcp --dport 9592 -m conntrack --ctstate NEW,ESTABLISHED -j ACCEPT" "-A OUTPUT -d $peer/32 -p tcp --sport 9592 -m conntrack --ctstate ESTABLISHED -j ACCEPT"
  fi
  for range in 0.0.0.0/8 10.0.0.0/8 100.64.0.0/10 127.0.0.0/8 169.254.0.0/16 172.16.0.0/12 192.0.0.0/24 192.0.2.0/24 192.88.99.0/24 192.168.0.0/16 198.18.0.0/15 198.51.100.0/24 203.0.113.0/24 224.0.0.0/3; do
    printf '%s\n' "-A OUTPUT -d $range -j DROP"
  done
  for dns in 1.1.1.1 8.8.8.8; do
    printf '%s\n' "-A OUTPUT -d $dns -p udp --dport 53 -j ACCEPT" "-A OUTPUT -d $dns -p tcp --dport 53 -j ACCEPT"
  done
  printf '%s\n' '-A OUTPUT -p tcp --dport 80 -j ACCEPT' '-A OUTPUT -p tcp --dport 443 -j ACCEPT' 'COMMIT'
} | iptables-restore --wait 10
# Root configures only this app container's firewall, then drops privileges.
# No browser process starts if either firewall failed.
echo NOD_BROWSER_FIREWALL_READY
env -i PATH=/usr/local/bin:/usr/bin:/bin HOME=/home/node LANG=C.UTF-8 setpriv --reuid=1000 --regid=1000 --clear-groups --no-new-privs --bounding-set=-all --inh-caps=-all --ambient-caps=-all node /app/worker.mjs &
worker_pid=$!
worker_ready() {
    setpriv --reuid=1000 --regid=1000 --clear-groups --no-new-privs --bounding-set=-all --inh-caps=-all --ambient-caps=-all test -S /run/nod-browser/control.sock
}
for attempt in $(seq 1 30); do
    if worker_ready; then break; fi
    kill -0 "$worker_pid" 2>/dev/null || exit 1
    sleep 1
done
worker_ready || { echo 'FAIL: worker socket unavailable'; exit 1; }
echo NOD_BROWSER_WORKER_READY
if [ -n "$peer" ]; then
    env -i PATH=/usr/local/bin:/usr/bin:/bin setpriv --reuid=1001 --regid=1000 --clear-groups --no-new-privs --bounding-set=-all --inh-caps=-all --ambient-caps=-all node /app/transport.mjs gateway /run/nod-browser-gateway/settings.json &
    gateway_pid=$!
fi
while kill -0 "$worker_pid" 2>/dev/null && { [ -z "$gateway_pid" ] || kill -0 "$gateway_pid" 2>/dev/null; }; do
    sleep 2 &
    wait $!
done
echo 'FAIL: browser service stopped'
exit 1
