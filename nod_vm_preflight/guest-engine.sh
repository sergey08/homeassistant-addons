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
        dest=$(printf '%s/init/modules/%03d.ko' "$work" "$index")
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
for m in /modules/*.ko; do [ ! -f "$m" ] || "$b" insmod "$m"; done
for n in 1 2 3 4 5; do [ ! -b /dev/vda ] || break; "$b" sleep 1; done
"$b" mount -t ext4 /dev/vda /newroot
"$b" mount --move /dev /newroot/dev
exec "$b" switch_root /newroot /usr/local/bin/nod-engine-init
INIT
chmod 0755 "$work/init/init"
(cd "$work/init" && find . -print | cpio -o -H newc) > "$work/init.cpio"
truncate -s 3G "$work/guest.raw"
mke2fs -q -F -t ext4 -d /opt/nod-guest-root "$work/guest.raw"
timeout 240 qemu-system-x86_64 -accel tcg -m 2048 -smp 2 -display none -serial stdio -monitor none -nic none -no-reboot -kernel "$kernel" -initrd "$work/init.cpio" -drive "file=$work/guest.raw,format=raw,if=virtio" -append 'console=ttyS0 quiet rdinit=/init panic=1' > "$work/guest.log" 2>&1 || true
tail -n 80 "$work/guest.log"
grep -Eq '^NOD_GUEST_CONTAINER_OK[[:space:]]*$' "$work/guest.log" || { echo 'FAIL: guest container engine probe'; exit 1; }
echo 'NOD_ENGINE_PROBE_OK'
