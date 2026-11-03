# Upstream is a FROM scratch image: it contains no shell or jq.
# Copy its statically linked Go binary into a minimal Alpine runtime.
FROM ghcr.io/lexfrei/mcp-raker@sha256:cdfbb9b4ead2b3f8a253eb55c1996a69cfdbc17088cc111b7d265d8b71f7090e AS upstream
FROM alpine:3.22
RUN apk add --no-cache ca-certificates jq python3
COPY --from=upstream /mcp-raker /usr/local/bin/mcp-raker
COPY run.sh /run.sh
COPY gateway.py tool_policy.py read_only_allowlist.json /opt/moonraker-mcp/
RUN chmod 755 /run.sh && mkdir -p /data && chown 65534:65534 /data
USER 65534:65534
ENTRYPOINT ["/run.sh"]
