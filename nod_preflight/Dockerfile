FROM debian:trixie-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends util-linux iproute2 iptables passwd \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --no-create-home probe

COPY run.sh /usr/local/bin/nod-preflight
RUN sh -n /usr/local/bin/nod-preflight && chmod 0755 /usr/local/bin/nod-preflight

ENTRYPOINT ["/usr/local/bin/nod-preflight"]
