#!/bin/sh
# Experimental CI-only guard. Never run in the host network namespace.
set -eu
export XTABLES_LOCKFILE=/tmp/nod-browser-xtables.lock
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
  for range in 0.0.0.0/8 10.0.0.0/8 100.64.0.0/10 127.0.0.0/8 169.254.0.0/16 172.16.0.0/12 192.0.0.0/24 192.0.2.0/24 192.88.99.0/24 192.168.0.0/16 198.18.0.0/15 198.51.100.0/24 203.0.113.0/24 224.0.0.0/3; do
    printf '%s\n' "-A OUTPUT -d $range -j REJECT"
  done
  for dns in 1.1.1.1 8.8.8.8; do
    printf '%s\n' "-A OUTPUT -d $dns -p udp --dport 53 -j ACCEPT" "-A OUTPUT -d $dns -p tcp --dport 53 -j ACCEPT"
  done
  printf '%s\n' '-A OUTPUT -p tcp -m multiport --dports 80,443 -j ACCEPT' 'COMMIT'
} | iptables-restore --wait 10
# Root configures only this disposable container's firewall, then drops privileges.
# No browser process starts if either firewall failed.
exec setpriv --reuid=1000 --regid=1000 --clear-groups --no-new-privs --bounding-set=-all --inh-caps=-all --ambient-caps=-all node /app/worker.mjs
