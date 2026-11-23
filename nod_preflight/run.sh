#!/bin/sh
set -eu

isolation_check() {
    unshare --user --map-root-user --net sh -eu -c '
        ip link set lo up
        iptables -w 2 -A OUTPUT -o lo -j ACCEPT
        iptables -w 2 -P OUTPUT DROP
        iptables -w 2 -C OUTPUT -o lo -j ACCEPT
        iptables -w 2 -S OUTPUT | grep -Fx -- "-P OUTPUT DROP"
    '
}

if [ "${1:-}" = "--probe" ]; then
    isolation_check
    exit 0
fi

printf '%s\n' 'Nod isolation preflight (unprivileged user and private network namespace)'
if [ -S /var/run/docker.sock ] || [ -S /run/docker.sock ]; then
    printf '%s\n' 'FAIL: host Docker socket is visible. Probe skipped.'
elif su -s /bin/sh probe -c '/usr/local/bin/nod-preflight --probe'; then
    printf '%s\n' 'PASS: a non-root process created a private network namespace and installed IPv4 filtering rules.'
    printf '%s\n' 'A complete rootless Nod deployment still needs validation.'
else
    printf '%s\n' 'FAIL: the unprivileged namespace or IPv4 filtering operation failed. See the error above.'
fi

printf '%s\n' 'Probe finished. Stop this app after reading the log.'
exec sleep infinity
