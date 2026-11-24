FROM debian:trixie-slim
RUN apt-get update \
    && apt-get install -y --no-install-recommends qemu-system-x86 linux-image-amd64 busybox-static cpio gzip \
    && rm -rf /var/lib/apt/lists/*
COPY run.sh /usr/local/bin/nod-vm-preflight
RUN sh -n /usr/local/bin/nod-vm-preflight && chmod 0755 /usr/local/bin/nod-vm-preflight
ENTRYPOINT ["/usr/local/bin/nod-vm-preflight"]
