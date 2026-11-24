#!/bin/sh
set -eu
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export DOCKER_HOST=unix:///run/docker.sock
export COMPOSE_ANSI=never
export COMPOSE_PROGRESS=plain
trap 'rc=$?; if [ "$rc" -ne 0 ]; then echo "NOD_GUEST_FAILURE=$rc"; tail -n 40 /tmp/dockerd.log || true; fi; /bin/busybox poweroff -f; while :; do sleep 60; done' EXIT
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t tmpfs tmpfs /run
mkdir -p /sys/fs/cgroup /run /tmp/nod-root/bin /dev/pts /dev/shm
mount -t cgroup2 cgroup2 /sys/fs/cgroup
mount -t devpts devpts /dev/pts
mount -t tmpfs tmpfs /dev/shm
modprobe bridge
modprobe veth
ip link set lo up
dockerd --host=unix:///run/docker.sock --storage-driver=vfs --iptables=false --ip6tables=false --bridge=none --ip-forward=false --ip-masq=false >/tmp/dockerd.log 2>&1 &
daemon_pid=$!
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
mkdir -p /tmp/nod-compose
cat > /tmp/nod-compose/compose.yaml <<'YAML'
services:
  server:
    image: nod-probe:local
    pull_policy: never
    command: ["/bin/busybox", "httpd", "-f", "-p", "8080", "-h", "/www"]
    volumes:
      - probe_data:/www
    networks: [private]
  client:
    image: nod-probe:local
    pull_policy: never
    networks: [private]
    command: ["/bin/busybox", "true"]
volumes:
  probe_data:
networks:
  private:
    internal: true
YAML
cd /tmp/nod-compose
docker compose version
docker compose run --rm --no-deps server /bin/busybox sh -c 'if [ -f /www/index.html ]; then grep -Fxq NOD_COMPOSE_PERSIST_V1 /www/index.html || exit 1; echo NOD_COMPOSE_VOLUME_READ; else echo NOD_COMPOSE_PERSIST_V1 > /www/index.html; sync; echo NOD_COMPOSE_VOLUME_WRITTEN; fi'
docker compose up -d server
for n in $(seq 1 10); do
    if docker compose run --rm --no-deps client /bin/busybox wget -q -O - http://server:8080/ > /tmp/response; then break; fi
    sleep 1
done
grep -Fxq NOD_COMPOSE_PERSIST_V1 /tmp/response
echo NOD_COMPOSE_NETWORK_OK
docker compose down --timeout 2
kill -TERM "$daemon_pid"
wait "$daemon_pid" || true
sync
echo NOD_COMPOSE_PROBE_OK
exit 0
