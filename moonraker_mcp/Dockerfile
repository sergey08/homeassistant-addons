# DEV12 development preview: audited source-built tunnel candidate.
# Redistribution and real end-to-end tunnel acceptance remain gated.
# DEV12 multi-architecture (amd64/arm64); upstream source and toolchain pinned.
# Never fetch the moving 'master' branch for a production add-on build.
FROM --platform=$BUILDPLATFORM docker.io/library/golang:1.27.3-alpine@sha256:d200d2dd76b03a99b52651fd1325aff7dcd35422c35c01bac56571b0507f3deb AS upstream_build
ARG TARGETARCH
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
# Security override for pinned upstream: Trivy reported CVE-2026-78661
# in golang.org/x/net v0.60.0; require fixed v0.62.0 explicitly.
# go mod verify and unit tests below fail the image build on incompatibility.
RUN set -eu; \
    go get golang.org/x/net@v0.62.0; \
    go mod download; go mod verify; \
    mkdir -p /tmp/dependency-provenance; \
    git diff -- go.mod go.sum > /tmp/dependency-provenance/mcp-raker-dependencies.patch; \
    { printf 'repository=https://github.com/lexfrei/mcp-raker\n'; \
      printf 'upstream_commit=%s\n' "$UPSTREAM_COMMIT"; \
      printf 'security_override=golang.org/x/net@v0.62.0\n'; \
      printf 'resolved_x_net='; go list -m golang.org/x/net; } > /tmp/dependency-provenance/mcp-raker-upstream.txt; \
    (cd /tmp/dependency-provenance && sha256sum mcp-raker-dependencies.patch mcp-raker-upstream.txt > mcp-raker-provenance.sha256)
RUN CGO_ENABLED=0 go test ./...
RUN CGO_ENABLED=0 GOOS=linux GOARCH=$TARGETARCH go build \
    -trimpath -ldflags "-s -w -X main.version=0.2.0-patched-dev12 -X main.revision=f01636bec21a21cfc5f9ee84dc68dad7d44d6dd9" \
    -o /tmp/mcp-raker ./cmd/mcp-raker
FROM scratch AS upstream
COPY --from=upstream_build /tmp/mcp-raker /mcp-raker
# Experimental source-built tunnel-client, NOT an OpenAI release binary.
# Source is pinned to official OpenAI tag v0.0.20 commit.
FROM --platform=$BUILDPLATFORM docker.io/library/golang:1.27.3-alpine@sha256:d200d2dd76b03a99b52651fd1325aff7dcd35422c35c01bac56571b0507f3deb AS tunnel_vendor
ARG TARGETARCH
ARG OPENAI_SOURCE_COMMIT=c2144b0904980bcbae2636cdca4f4167e9818e0b
RUN apk add --no-cache ca-certificates git
WORKDIR /tunnel-source
RUN set -eu; git init .; git remote add origin https://github.com/openai/tunnel-client.git; \
    git fetch --depth=1 origin "$OPENAI_SOURCE_COMMIT"; \
    test "$(git rev-parse FETCH_HEAD)" = "$OPENAI_SOURCE_COMMIT"; \
    git checkout --detach FETCH_HEAD; \
    test "$(git rev-parse HEAD)" = "$OPENAI_SOURCE_COMMIT"
# Override the independently reported CVE-2026-78661 vulnerability.
RUN set -eu; \
    go get golang.org/x/net@v0.62.0; \
    go mod download; go mod verify; \
    mkdir -p /tmp/dependency-provenance; \
    git diff -- go.mod go.sum > /tmp/dependency-provenance/tunnel-client-dependencies.patch; \
    { printf 'repository=https://github.com/openai/tunnel-client\n'; \
      printf 'upstream_commit=%s\n' "$OPENAI_SOURCE_COMMIT"; \
      printf 'security_override=golang.org/x/net@v0.62.0\n'; \
      printf 'resolved_x_net='; go list -m golang.org/x/net; } > /tmp/dependency-provenance/tunnel-client-upstream.txt; \
    (cd /tmp/dependency-provenance && sha256sum tunnel-client-dependencies.patch tunnel-client-upstream.txt > tunnel-client-provenance.sha256)
RUN CGO_ENABLED=0 GOOS=linux GOARCH=$TARGETARCH go build -trimpath -buildvcs=false \
    -ldflags "-s -w -X github.com/openai/tunnel-client/pkg/version.GitSHA=c2144b0904980bcbae2636cdca4f4167e9818e0b" \
    -o /tmp/tunnel-client ./cmd/client

FROM docker.io/library/alpine:3.22@sha256:bfe7ceb9f09ec0566c48fb93356e45a47a00be5a1dd14fa5b909e7709c66b034
RUN apk add --no-cache ca-certificates jq python3 su-exec
COPY --from=upstream /mcp-raker /usr/local/bin/mcp-raker
COPY --from=tunnel_vendor /tmp/tunnel-client /opt/moonraker-mcp/vendor/tunnel-client
# Ship reproducible dependency deltas and exact pinned upstream commit references.
# These are public go.mod/go.sum diffs, never runtime credentials or settings.
COPY --from=upstream_build /tmp/dependency-provenance/ /usr/share/doc/moonraker-mcp/provenance/
COPY --from=tunnel_vendor /tmp/dependency-provenance/ /usr/share/doc/moonraker-mcp/provenance/
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
