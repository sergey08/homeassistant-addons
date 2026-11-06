# DEV11 patched upstream: source pinned by Git commit and Go builder by digest.
# Never fetch the moving 'master' branch for a production add-on build.
FROM docker.io/library/golang:1.27.3-alpine@sha256:d200d2dd76b03a99b52651fd1325aff7dcd35422c35c01bac56571b0507f3deb AS upstream_build
RUN apk add --no-cache ca-certificates git
ARG UPSTREAM_COMMIT=f01636bec21a21cfc5f9ee84dc68dad7d44d6dd9
WORKDIR /src
RUN set -eu; \
    git init .; \
    git remote add origin https://github.com/lexfrei/mcp-raker.git; \
    git fetch --depth=1 origin "$UPSTREAM_COMMIT"; \
    test "$(git rev-parse FETCH_HEAD)" = "$UPSTREAM_COMMIT"; \
    git checkout --detach FETCH_HEAD; \
    test "$(git rev-parse HEAD)" = "$UPSTREAM_COMMIT"
RUN go mod download && go mod verify
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go test ./...
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build \
    -trimpath -ldflags "-s -w -X main.version=0.2.0-patched-dev11 -X main.revision=f01636bec21a21cfc5f9ee84dc68dad7d44d6dd9" \
    -o /tmp/mcp-raker ./cmd/mcp-raker
FROM scratch AS upstream
COPY --from=upstream_build /tmp/mcp-raker /mcp-raker
# Pin vendor binary independently of any runtime GitHub availability.
# For DEV5, automatic provisioning is limited to amd64 until the official
# aarch64 artifact can be independently validated and pinned.
FROM docker.io/library/alpine:3.22@sha256:bfe7ceb9f09ec0566c48fb93356e45a47a00be5a1dd14fa5b909e7709c66b034 AS tunnel_vendor
RUN apk add --no-cache ca-certificates curl python3
RUN set -eu; \
    curl --fail --location --silent --show-error --retry 3 --max-time 120 \
      'https://github.com/openai/tunnel-client/releases/download/v0.0.19/tunnel-client-v0.0.19-linux-amd64.zip' \
      -o /tmp/tunnel-client.zip; \
    echo '9ee9448592345a9dd1517fb79791ab54d24f051142eb92bcbe8cd355effc9142  /tmp/tunnel-client.zip' | sha256sum -c -; \
    python3 -c 'import zipfile,pathlib; z=zipfile.ZipFile("/tmp/tunnel-client.zip"); a=[x for x in z.infolist() if pathlib.PurePosixPath(x.filename).name=="tunnel-client" and not x.is_dir()]; assert len(a)==1 and a[0].file_size<90000000; pathlib.Path("/tmp/tunnel-client").write_bytes(z.read(a[0]))'; \
    chmod 755 /tmp/tunnel-client

FROM docker.io/library/alpine:3.22@sha256:bfe7ceb9f09ec0566c48fb93356e45a47a00be5a1dd14fa5b909e7709c66b034
RUN apk add --no-cache ca-certificates jq python3 su-exec
COPY --from=upstream /mcp-raker /usr/local/bin/mcp-raker
COPY --from=tunnel_vendor /tmp/tunnel-client /opt/moonraker-mcp/vendor/tunnel-client
COPY run.sh /run.sh
COPY tunnel_runtime.py /opt/moonraker-mcp/tunnel_runtime.py
COPY tunnel_provision.py /opt/moonraker-mcp/tunnel_provision.py
COPY tunnel_autosetup.py /opt/moonraker-mcp/tunnel_autosetup.py
# Bundle upstream copyright/license notices with redistributed ELF binaries.
COPY licenses/ /usr/share/doc/moonraker-mcp/licenses/
COPY gateway.py tool_policy.py moonraker_files.py moonraker_status.py read_only_allowlist.json /opt/moonraker-mcp/
RUN chmod 755 /run.sh && mkdir -p /data && chown 65534:65534 /data
# HA Supervisor keeps /data/options.json readable only by root. The small
# launcher reads options as root and drops privileges for network services.
# Ensure the launcher can read Supervisor-protected /data/options.json.
# run.sh drops privileges to 65534:65534 for the long-lived services.
USER root
ENTRYPOINT ["/run.sh"]
