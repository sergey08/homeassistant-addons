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
if grep -qw nod_bundle=1 /proc/cmdline; then
    cd /opt/nod-bundle
    docker image load --input images.tar.gz
    count=0
    for kind in server browser workspace; do
        line=$(awk -v prefix="nod-$kind:bundle-" 'index($1,prefix)==1 {print}' images.txt)
        [ "$(printf '%s\n' "$line" | wc -l)" = 1 ]
        read -r reference config target <<EOF
$line
EOF
        actual=$(docker image inspect --format '{{.Id}} {{.Os}}/{{.Architecture}} {{index .Config.Labels "org.opencontainers.image.revision"}}' "$reference")
        rev=6670bc233b6b7dddaa75b25b89b4a89f0e92bcac
        [ "$actual" = "$config linux/amd64 $rev" ] || [ "$actual" = "$target linux/amd64 $rev" ]
        echo "NOD_IMAGE_VERIFIED=$kind"
        count=$((count+1))
    done
    [ "$count" = 3 ]
    kill -TERM "$daemon_pid"
    wait "$daemon_pid" || true
    sync
    echo NOD_REAL_IMAGES_OK
    exit 0
fi
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
# Exercise the production-facing HTTP transport without exposing a host port.
modprobe virtio_net
iface=
for dev in /sys/class/net/*; do
    case "${dev##*/}" in eth*|en*) iface=${dev##*/};; esac
done
[ -n "$iface" ]
ip link set "$iface" up
ip addr add 10.0.2.15/24 dev "$iface"
# A fixed relay tests TLS from a disposable container, not unrestricted routing.
if grep -qw nod_online=1 /proc/cmdline; then
    mkdir -p /tmp/nod-tls/bin /tmp/nod-tls/usr/bin /tmp/nod-tls/etc/ssl/certs
    cp /usr/bin/curl /tmp/nod-tls/usr/bin/
    cp /etc/ssl/certs/ca-certificates.crt /tmp/nod-tls/etc/ssl/certs/
    ldd /usr/bin/curl | awk '{for(i=1;i<=NF;i++) if ($i ~ /^\//) print $i}' | sort -u | while read -r lib; do
        mkdir -p "/tmp/nod-tls$(dirname "$lib")"
        cp -L "$lib" "/tmp/nod-tls$lib"
    done
    tar -C /tmp/nod-tls -cf /tmp/nod-tls.tar .
    docker import /tmp/nod-tls.tar nod-tls-probe:local >/dev/null
    docker run --rm --network host nod-tls-probe:local /usr/bin/curl --noproxy '*' --fail --silent --show-error --max-time 20 --resolve cloudflare-dns.com:443:10.0.2.100 -H 'accept: application/dns-json' 'https://cloudflare-dns.com/dns-query?name=example.com&type=A' > /tmp/nod-doh.json
    grep -Eq '"Status"[[:space:]]*:[[:space:]]*0' /tmp/nod-doh.json
    grep -q '"Answer"' /tmp/nod-doh.json
    echo NOD_CONTAINER_TLS_OK
else
    echo NOD_CONTAINER_TLS_OFFLINE
fi
mkdir -p /tmp/nod-http
printf '%s\n' NOD_HTTP_TRANSPORT_V1 > /tmp/nod-http/index.html
docker run -d --name nod-http-probe --network host -v /tmp/nod-http:/www:ro nod-probe:local /bin/busybox httpd -f -p 10.0.2.15:4310 -h /www >/dev/null
echo NOD_HTTP_GUEST_READY
sleep 25
docker rm -f nod-http-probe >/dev/null
docker compose down --timeout 2
kill -TERM "$daemon_pid"
wait "$daemon_pid" || true
sync
echo NOD_COMPOSE_PROBE_OK
exit 0
