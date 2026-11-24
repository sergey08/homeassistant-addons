#!/bin/sh
set -eu
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT
mkdir -p "$work/init/bin" "$work/init/dev" "$work/init/newroot" "$work/init/modules"
cp /bin/busybox "$work/init/bin/busybox"
set -- /boot/vmlinuz-*
kernel=$1
version=${kernel##*/vmlinuz-}
modprobe --set-version "$version" --show-depends virtio_pci virtio_blk ext4 --all | awk '!seen[$0]++' | (
    index=0
    while read -r action module; do
        [ "$action" = insmod ] || continue
        index=$((index + 1))
        dest=$(printf '%s/init/modules/%03d-%s' "$work" "$index" "$(basename "$module" | sed -E 's/\.(zst|xz|gz)$//')")
        case "$module" in
            *.zst) zstd -dc "$module" > "$dest";;
            *.xz) xz -dc "$module" > "$dest";;
            *.gz) gzip -dc "$module" > "$dest";;
            *) cp "$module" "$dest";;
        esac
    done
)
cat > "$work/init/init" <<'INIT'
#!/bin/busybox sh
set -eu
b=/bin/busybox
"$b" mount -t devtmpfs devtmpfs /dev
for m in /modules/*.ko; do
    [ -f "$m" ] || continue
    "$b" echo "Loading $m"
    "$b" insmod "$m"
done
for n in 1 2 3 4 5; do [ ! -b /dev/vda ] || break; "$b" sleep 1; done
"$b" mount -t ext4 /dev/vda /newroot
"$b" mount --move /dev /newroot/dev
exec "$b" switch_root /newroot /usr/local/bin/nod-engine-init
INIT
chmod 0755 "$work/init/init"
(cd "$work/init" && find . -print | cpio -o -H newc) > "$work/init.cpio"
mkdir -p /data
if [ "${1:-}" = --bundle ]; then
    [ "$#" = 2 ]
    disk=/data/nod-real-import-v1.raw
    # Never replace a previous disk automatically.
    if [ ! -e "$disk" ]; then
        available=$(df -Pk /data | awk 'END {print $4}')
        [ "$available" -ge 62914560 ] || { echo 'FAIL: insufficient free space (60 GiB required)'; exit 1; }
        mkdir -p "$work/bundle"
        python3 /usr/local/bin/nod-unpack-bundle.py "$2" "$work/bundle"
        # Build the disk directly on the persistent filesystem, with atomic publication.
        tmpdisk=$(mktemp /data/nod-import.XXXXXX)
        trap 'rm -rf -- "$work"; rm -f -- "$tmpdisk"' EXIT
        mkdir -p "$work/root"
        cp -a /opt/nod-guest-root/. "$work/root/"
        mkdir -p "$work/root/opt/nod-bundle"
        cp -a "$work/bundle/." "$work/root/opt/nod-bundle/"
        truncate -s 50G "$tmpdisk"
        mke2fs -q -F -t ext4 -d "$work/root" "$tmpdisk"
        mv "$tmpdisk" "$disk"
    fi
    echo NOD_REAL_IMAGE_IMPORT_START
    timeout -k 15s 1800s qemu-system-x86_64 -accel tcg,thread=single -cpu max -m 4096 -smp 1 -display none -serial stdio -monitor none -nic none -no-reboot -kernel "$kernel" -initrd "$work/init.cpio" -drive "file=$disk,format=raw,if=virtio" -append 'console=ttyS0 quiet rdinit=/init panic=1 nod_bundle=1' > "$work/guest.log" 2>&1 || { tail -n 80 "$work/guest.log"; echo 'FAIL: image import VM'; exit 1; }
    tail -n 80 "$work/guest.log"
    grep -Eq '^NOD_REAL_IMAGES_OK[[:space:]]*/data/nod-compose-probe-v3.raw
if [ ! -e "$disk" ]; then
    truncate -s 3G "$work/guest.raw"
    mke2fs -q -F -t ext4 -d /opt/nod-guest-root "$work/guest.raw"
    mv "$work/guest.raw" "$disk"
fi
network='user,model=virtio-net-pci,restrict=on,hostfwd=tcp:127.0.0.1:14310-10.0.2.15:4310'
online=0
tls_marker=NOD_CONTAINER_TLS_OFFLINE
if [ "${NOD_PROBE_ONLINE:-1}" = 1 ]; then
    network="$network,guestfwd=tcp:10.0.2.100:443-cmd:/usr/bin/socat STDIO TCP:1.1.1.1:443"
    online=1
    tls_marker=NOD_CONTAINER_TLS_OK
fi
for expected in 'NOD_COMPOSE_VOLUME_(WRITTEN|READ)' NOD_COMPOSE_VOLUME_READ; do
    timeout -k 10s 240s qemu-system-x86_64 -accel tcg,thread=single -cpu max -m 2048 -smp 1 -display none -serial stdio -monitor none -nic "$network" -no-reboot -kernel "$kernel" -initrd "$work/init.cpio" -drive "file=$disk,format=raw,if=virtio" -append "console=ttyS0 quiet rdinit=/init panic=1 nod_online=$online" > "$work/guest.log" 2>&1 &
    vm_pid=$!
    http_ok=0
    for attempt in $(seq 1 180); do
        if curl --noproxy '*' --fail --silent --max-time 1 http://127.0.0.1:14310/ | grep -Fxq NOD_HTTP_TRANSPORT_V1; then
            http_ok=1
            break
        fi
        kill -0 "$vm_pid" 2>/dev/null || break
        sleep 1
    done
    wait "$vm_pid" || { tail -n 120 "$work/guest.log"; echo 'FAIL: guest exit status'; exit 1; }
    [ "$http_ok" = 1 ] || { tail -n 120 "$work/guest.log"; echo 'FAIL: private HTTP transport'; exit 1; }
    echo NOD_HTTP_TRANSPORT_OK
    tail -n 120 "$work/guest.log"
    for marker in NOD_GUEST_CONTAINER_OK NOD_COMPOSE_NETWORK_OK NOD_COMPOSE_PROBE_OK "$tls_marker" "$expected"; do
        grep -Eq "^$marker[[:space:]]*$" "$work/guest.log" || { echo "FAIL: missing $marker"; exit 1; }
    done
done
echo 'NOD_ENGINE_PROBE_OK'
 "$work/guest.log" || { echo 'FAIL: image verification'; exit 1; }
    exit 0
fi
disk=/data/nod-compose-probe-v3.raw
if [ ! -e "$disk" ]; then
    truncate -s 3G "$work/guest.raw"
    mke2fs -q -F -t ext4 -d /opt/nod-guest-root "$work/guest.raw"
    mv "$work/guest.raw" "$disk"
fi
network='user,model=virtio-net-pci,restrict=on,hostfwd=tcp:127.0.0.1:14310-10.0.2.15:4310'
online=0
tls_marker=NOD_CONTAINER_TLS_OFFLINE
if [ "${NOD_PROBE_ONLINE:-1}" = 1 ]; then
    network="$network,guestfwd=tcp:10.0.2.100:443-cmd:/usr/bin/socat STDIO TCP:1.1.1.1:443"
    online=1
    tls_marker=NOD_CONTAINER_TLS_OK
fi
for expected in 'NOD_COMPOSE_VOLUME_(WRITTEN|READ)' NOD_COMPOSE_VOLUME_READ; do
    timeout -k 10s 240s qemu-system-x86_64 -accel tcg,thread=single -cpu max -m 2048 -smp 1 -display none -serial stdio -monitor none -nic "$network" -no-reboot -kernel "$kernel" -initrd "$work/init.cpio" -drive "file=$disk,format=raw,if=virtio" -append "console=ttyS0 quiet rdinit=/init panic=1 nod_online=$online" > "$work/guest.log" 2>&1 &
    vm_pid=$!
    http_ok=0
    for attempt in $(seq 1 180); do
        if curl --noproxy '*' --fail --silent --max-time 1 http://127.0.0.1:14310/ | grep -Fxq NOD_HTTP_TRANSPORT_V1; then
            http_ok=1
            break
        fi
        kill -0 "$vm_pid" 2>/dev/null || break
        sleep 1
    done
    wait "$vm_pid" || { tail -n 120 "$work/guest.log"; echo 'FAIL: guest exit status'; exit 1; }
    [ "$http_ok" = 1 ] || { tail -n 120 "$work/guest.log"; echo 'FAIL: private HTTP transport'; exit 1; }
    echo NOD_HTTP_TRANSPORT_OK
    tail -n 120 "$work/guest.log"
    for marker in NOD_GUEST_CONTAINER_OK NOD_COMPOSE_NETWORK_OK NOD_COMPOSE_PROBE_OK "$tls_marker" "$expected"; do
        grep -Eq "^$marker[[:space:]]*$" "$work/guest.log" || { echo "FAIL: missing $marker"; exit 1; }
    done
done
echo 'NOD_ENGINE_PROBE_OK'
