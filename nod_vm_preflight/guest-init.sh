#!/bin/sh
set -eu
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export DOCKER_HOST=unix:///run/docker.sock
trap 'rc=$?; if [ "$rc" -ne 0 ]; then echo "NOD_GUEST_FAILURE=$rc"; tail -n 40 /tmp/dockerd.log || true; fi; /bin/busybox poweroff -f; while :; do sleep 60; done' EXIT
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t tmpfs tmpfs /run
mkdir -p /sys/fs/cgroup /run /tmp/nod-root/bin /dev/pts /dev/shm
mount -t cgroup2 cgroup2 /sys/fs/cgroup
mount -t devpts devpts /dev/pts
mount -t tmpfs tmpfs /dev/shm
ip link set lo up
dockerd --host=unix:///run/docker.sock --storage-driver=vfs --iptables=false --ip6tables=false --bridge=none --ip-forward=false --ip-masq=false >/tmp/dockerd.log 2>&1 &
for n in $(seq 1 60); do
    if docker version --format '{{.Server.Version}}' >/tmp/docker-version.log 2>&1; then break; fi
    sleep 1
done
if ! docker version --format '{{.Server.Version}}'; then cat /tmp/docker-version.log; exit 1; fi
printf "%s\n" NOD_GUEST_DOCKER_READY
cp /bin/busybox /tmp/nod-root/bin/busybox
tar -C /tmp/nod-root -cf /tmp/nod-root.tar .
docker import /tmp/nod-root.tar nod-probe:local >/dev/null
docker run --rm --network none nod-probe:local /bin/busybox echo NOD_GUEST_CONTAINER_OK
exit 0
