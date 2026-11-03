ARG BUILD_FROM=ghcr.io/lexfrei/mcp-raker:latest
FROM ${BUILD_FROM}
COPY run.sh /run.sh
USER root
RUN chmod 755 /run.sh
ENTRYPOINT ["/run.sh"]
