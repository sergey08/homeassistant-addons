# Upstream is a FROM scratch image: it contains no shell or jq.
# Copy its statically linked Go binary into a minimal Alpine runtime.
FROM ghcr.io/lexfrei/mcp-raker@sha256:cdfbb9b4ead2b3f8a253eb55c1996a69cfdbc17088cc111b7d265d8b71f7090e AS upstream
# Pin vendor binary independently of any runtime GitHub availability.
# For DEV5, automatic provisioning is limited to amd64 until the official
# aarch64 artifact can be independently validated and pinned.
FROM alpine:3.22 AS tunnel_vendor
RUN apk add --no-cache ca-certificates curl python3
RUN set -eu; \
    curl --fail --location --silent --show-error --retry 3 --max-time 120 \
      'https://github.com/openai/tunnel-client/releases/download/v0.0.19/tunnel-client-v0.0.19-linux-amd64.zip' \
      -o /tmp/tunnel-client.zip; \
    echo '9ee9448592345a9dd1517fb79791ab54d24f051142eb92bcbe8cd355effc9142  /tmp/tunnel-client.zip' | sha256sum -c -; \
    python3 -c 'import zipfile,pathlib; z=zipfile.ZipFile("/tmp/tunnel-client.zip"); a=[x for x in z.infolist() if pathlib.PurePosixPath(x.filename).name=="tunnel-client" and not x.is_dir()]; assert len(a)==1 and a[0].file_size<90000000; pathlib.Path("/tmp/tunnel-client").write_bytes(z.read(a[0]))'; \
    chmod 755 /tmp/tunnel-client

FROM alpine:3.22
RUN apk add --no-cache ca-certificates jq python3 su-exec
COPY --from=upstream /mcp-raker /usr/local/bin/mcp-raker
COPY --from=tunnel_vendor /tmp/tunnel-client /opt/moonraker-mcp/vendor/tunnel-client
COPY run.sh /run.sh
COPY tunnel_runtime.py /opt/moonraker-mcp/tunnel_runtime.py
COPY tunnel_provision.py /opt/moonraker-mcp/tunnel_provision.py
COPY tunnel_autosetup.py /opt/moonraker-mcp/tunnel_autosetup.py
COPY gateway.py tool_policy.py moonraker_files.py moonraker_status.py read_only_allowlist.json /opt/moonraker-mcp/
RUN chmod 755 /run.sh && mkdir -p /data && chown 65534:65534 /data
# HA Supervisor keeps /data/options.json readable only by root. The small
# launcher reads options as root and drops privileges for network services.
# Ensure the launcher can read Supervisor-protected /data/options.json.
# run.sh drops privileges to 65534:65534 for the long-lived services.
USER root
ENTRYPOINT ["/run.sh"]
