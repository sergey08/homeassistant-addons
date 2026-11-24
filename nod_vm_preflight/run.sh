#!/bin/sh
set -eu

work=$(mktemp -d)
trap 'exit 0' TERM INT
trap 'rm -rf -- "$work"' EXIT
mkdir -p "$work/root/bin" "$work/root/dev" "$work/root/modules" "$work/root/sys" "$work/root/proc" /data
cp /bin/busybox "$work/root/bin/busybox"
mkdir -p "$work/root/etc/ssl/certs" "$work/root/usr/bin"
cp /usr/bin/curl "$work/root/usr/bin/curl"
ldd /usr/bin/curl | awk '{for(i=1;i<=NF;i++) if ($i ~ /^\//) print $i}' | sort -u | while read -r lib; do
    mkdir -p "$work/root$(dirname "$lib")"
    cp -L "$lib" "$work/root$lib"
done
cp /etc/ssl/certs/ca-certificates.crt "$work/root/etc/ssl/certs/"

set -- /boot/vmlinuz-*
kernel=$1
modules=$(modprobe --set-version "${kernel##*/vmlinuz-}" --show-depends virtio_pci virtio_blk virtio_net --all)
printf '%s\n' "$modules" | awk '!seen[$0]++' | (
    index=0
    while read -r action module; do
        [ "$action" = insmod ] || continue
        index=$((index + 1))
        destination=$(printf '%s/root/modules/%03d.ko' "$work" "$index")
        case "$module" in
            *.zst) zstd -dc "$module" > "$destination" ;;
            *.xz) xz -dc "$module" > "$destination" ;;
            *.gz) gzip -dc "$module" > "$destination" ;;
            *) cp "$module" "$destination" ;;
        esac
    done
)
cat > "$work/root/init" <<'GUEST'
#!/bin/busybox sh
set -eu
b=/bin/busybox
"$b" mount -t devtmpfs devtmpfs /dev
for module in /modules/*.ko; do
    [ ! -f "$module" ] || "$b" insmod "$module"
done
for attempt in 1 2 3 4 5; do
    [ ! -b /dev/vda ] || break
    "$b" sleep 1
done
[ -b /dev/vda ]
marker=NOD_VM_PERSISTENCE_V1
if "$b" dd if=/dev/vda bs=1 count=$((${#marker} + 1)) 2>/dev/null | "$b" grep -Fxq "$marker"; then
    "$b" echo NOD_VM_DISK_READ
else
    "$b" printf '%s\n' "$marker" | "$b" dd of=/dev/vda conv=fsync
    "$b" echo NOD_VM_DISK_WRITTEN
fi
"$b" mount -t proc proc /proc
"$b" mount -t sysfs sysfs /sys
iface=
for attempt in 1 2 3 4 5; do
    for dev in /sys/class/net/*; do
        [ "${dev##*/}" = lo ] || iface=${dev##*/}
    done
    [ -z "$iface" ] || break
    "$b" sleep 1
done
[ -n "$iface" ]
"$b" ip link set "$iface" up
"$b" ip addr add 10.0.2.15/24 dev "$iface"
"$b" ip route add default via 10.0.2.2
"$b" ping -c 1 -W 3 10.0.2.2
"$b" echo NOD_VM_GATEWAY_OK
if "$b" grep -q nod_online=1 /proc/cmdline; then
    /usr/bin/curl --fail --silent --show-error --max-time 20 --noproxy '*' --resolve cloudflare-dns.com:443:10.0.2.100 -H 'accept: application/dns-json' 'https://cloudflare-dns.com/dns-query?name=example.com&type=A' > /dns.json
    "$b" grep -Eq '"Status"[[:space:]]*:[[:space:]]*0' /dns.json
    "$b" grep -q '"Answer"' /dns.json
    "$b" echo NOD_VM_DOH_HTTPS_OK
fi
"$b" poweroff -f
GUEST
chmod 0755 "$work/root/init"
(cd "$work/root" && find . -print | cpio -o -H newc) > "$work/initramfs.cpio"

disk=/data/nod-vm-probe.raw
if [ ! -e "$disk" ]; then
    truncate -s 8M "$disk"
fi
network='user,model=virtio-net-pci,restrict=on'
online=0
if [ "${NOD_PROBE_ONLINE:-1}" = 1 ]; then
    network="$network,guestfwd=tcp:10.0.2.100:443-cmd:/usr/bin/socat STDIO TCP:1.1.1.1:443"
    online=1
fi
for expected in 'NOD_VM_DISK_(WRITTEN|READ)' NOD_VM_DISK_READ; do
    timeout 120 qemu-system-x86_64 -accel tcg -m 256 -smp 1 -display none -serial stdio \
        -monitor none -nic "$network" -no-reboot -kernel "$kernel" -initrd "$work/initramfs.cpio" \
        -drive "file=$disk,format=raw,if=virtio" \
        -append "console=ttyS0 quiet rdinit=/init panic=1 nod_online=$online" > "$work/guest.log" 2>&1 || true
    tail -n 20 "$work/guest.log"
    if ! grep -Eq "^$expected[[:space:]]*$" "$work/guest.log" || ! grep -Eq "^NOD_VM_GATEWAY_OK[[:space:]]*$" "$work/guest.log"; then
        printf '%s\n' 'FAIL: Linux guest did not produce the expected disk and gateway markers.'
        exit 1
    fi
    if [ "$online" = 1 ] && ! grep -Eq "^NOD_VM_DOH_HTTPS_OK[[:space:]]*$" "$work/guest.log"; then
        echo 'FAIL: Restricted DNS-over-HTTPS probe failed.'
        exit 1
    fi
done
/usr/local/bin/nod-engine-probe
printf '%s\n' 'PASS: Linux guest recovered the disk marker after reboot and reached the restricted virtual gateway.'
sleep infinity &
idle_pid=$!
trap 'kill "$idle_pid" 2>/dev/null || true; exit 0' TERM INT
wait "$idle_pid"
