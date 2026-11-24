FROM debian:trixie-slim AS guest
RUN apt-get update && apt-get install -y --no-install-recommends docker.io docker-cli docker-compose busybox-static iproute2 kmod curl ca-certificates && rm -rf /var/lib/apt/lists/*
COPY guest-init.sh /usr/local/bin/nod-engine-init
RUN command -v docker && docker --version && docker compose version && command -v dockerd && sh -n /usr/local/bin/nod-engine-init && chmod 0755 /usr/local/bin/nod-engine-init && mkdir -p /dev /proc /sys /run /tmp

FROM debian:trixie-slim
RUN apt-get update \
    && apt-get install -y --no-install-recommends qemu-system-x86 linux-image-amd64 busybox-static cpio gzip kmod xz-utils zstd curl ca-certificates socat e2fsprogs python3 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=guest / /opt/nod-guest-root/
RUN mkdir -p /opt/nod-guest-root/lib/modules && cp -a /lib/modules/. /opt/nod-guest-root/lib/modules/
COPY guest-engine.sh /usr/local/bin/nod-engine-probe
RUN sh -n /usr/local/bin/nod-engine-probe && chmod 0755 /usr/local/bin/nod-engine-probe
COPY unpack-bundle.py /usr/local/bin/nod-unpack-bundle.py
RUN python3 -m py_compile /usr/local/bin/nod-unpack-bundle.py
COPY stage-bundle.py /usr/local/bin/nod-stage-bundle.py
RUN python3 -m py_compile /usr/local/bin/nod-stage-bundle.py
COPY run.sh /usr/local/bin/nod-vm-preflight
RUN sh -n /usr/local/bin/nod-vm-preflight && chmod 0755 /usr/local/bin/nod-vm-preflight
ENTRYPOINT ["/usr/local/bin/nod-vm-preflight"]
