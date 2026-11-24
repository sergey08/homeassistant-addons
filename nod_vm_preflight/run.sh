#!/bin/sh
set -eu

work=$(mktemp -d)
trap 'exit 0' TERM INT
trap 'rm -rf -- "$work"' EXIT
mkdir -p "$work/root/bin" "$work/root/dev"
cp /bin/busybox "$work/root/bin/busybox"
cat > "$work/root/init" <<'GUEST'
#!/bin/busybox sh
/bin/busybox echo NOD_VM_GUEST_BOOTED
/bin/busybox poweroff -f
GUEST
chmod 0755 "$work/root/init"
(cd "$work/root" && find . -print | cpio -o -H newc) > "$work/initramfs.cpio"
set -- /boot/vmlinuz-*
timeout 120 qemu-system-x86_64 -accel tcg -m 256 -smp 1 -display none -serial stdio \
    -monitor none -nic none -no-reboot -kernel "$1" -initrd "$work/initramfs.cpio" \
    -append 'console=ttyS0 quiet rdinit=/init panic=1' > "$work/guest.log" 2>&1 || true
tail -n 20 "$work/guest.log"
if grep -q '^NOD_VM_GUEST_BOOTED[[:space:]]* "$work/guest.log"; then
    printf '%s\n' 'PASS: QEMU booted a Linux guest under software emulation.'
else
    printf '%s\n' 'FAIL: Linux guest boot marker missing.'
fi
sleep infinity &
idle_pid=$!
trap 'kill "$idle_pid" 2>/dev/null || true; exit 0' TERM INT
wait "$idle_pid"
 "$work/guest.log"; then
    printf '%s\n' 'PASS: QEMU booted a Linux guest under software emulation.'
else
    printf '%s\n' 'FAIL: Linux guest boot marker missing.'
fi
sleep infinity &
idle_pid=$!
trap 'kill "$idle_pid" 2>/dev/null || true; exit 0' TERM INT
wait "$idle_pid"
