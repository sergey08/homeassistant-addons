# Upstream is a FROM scratch image: it contains no shell or jq.
# Copy its statically linked Go binary into a minimal Alpine runtime.
FROM ghcr.io/lexfrei/mcp-raker:latest AS upstream
FROM alpine:3.22
RUN apk add --no-cache ca-certificates jq && \
    addgroup -g 65534 -S nobody 2>/dev/null || true
COPY --from=upstream /mcp-raker /usr/local/bin/mcp-raker
COPY run.sh /run.sh
RUN chmod 755 /run.sh && mkdir -p /data && chown 65534:65534 /data
USER 65534:65534
ENTRYPOINT ["/run.sh"]
