FROM debian:trixie-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends util-linux iproute2 iptables passwd podman uidmap busybox-static \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home probe \
    && grep -q '^probe:' /etc/subuid \
    && grep -q '^probe:' /etc/subgid \
    && install -d -m 0700 -o probe -g probe /home/probe/runtime \
    && mkdir -p /tmp/nod-probe-rootfs/bin \
    && cp "$(command -v busybox)" /tmp/nod-probe-rootfs/bin/busybox \
    && tar -C /tmp/nod-probe-rootfs -cf /usr/local/share/nod-probe-rootfs.tar . \
    && rm -r /tmp/nod-probe-rootfs

COPY run.sh /usr/local/bin/nod-preflight
RUN sh -n /usr/local/bin/nod-preflight && chmod 0755 /usr/local/bin/nod-preflight

ENTRYPOINT ["/usr/local/bin/nod-preflight"]
