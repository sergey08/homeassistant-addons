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

if [ "${1:-}" = "--engine" ]; then
    export XDG_RUNTIME_DIR=/home/probe/runtime
    podman --storage-driver=vfs import /usr/local/share/nod-probe-rootfs.tar localhost/nod-preflight:probe
    podman --storage-driver=vfs run --rm --pull=never --network=none --cgroups=disabled \
        --cap-drop=all localhost/nod-preflight:probe /bin/busybox echo NOD_ENGINE_OK
    exit 0
fi

if [ "${1:-}" = "--probe" ]; then
    isolation_check
    exit 0
fi

printf '%s\n' 'Nod isolation preflight (unprivileged user and private network namespace)'
if [ -S /var/run/docker.sock ] || [ -S /run/docker.sock ]; then
    printf '%s\n' 'FAIL: host Docker socket is visible. Probe skipped.'
elif su -s /bin/sh probe -c '/usr/local/bin/nod-preflight --probe'; then
    printf '%s\n' 'PASS: a non-root process created a private network namespace and installed IPv4 filtering rules.'
    if timeout 90 su -s /bin/sh probe -c '/usr/local/bin/nod-preflight --engine'; then
        printf '%s\n' 'PASS: rootless Podman launched an offline OCI container.'
    else
        printf '%s\n' 'FAIL: rootless Podman could not launch the OCI container. See the error above.'
    fi
else
    printf '%s\n' 'FAIL: the unprivileged namespace or IPv4 filtering operation failed. See the error above.'
fi

printf '%s\n' 'Probe finished. Stop this app after reading the log.'
sleep infinity &
idle_pid=$!
trap 'kill "$idle_pid" 2>/dev/null || true; exit 0' TERM INT
wait "$idle_pid"
