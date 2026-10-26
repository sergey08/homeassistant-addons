# Build the upstream protocol implementation from a pinned revision.
ARG BUILD_FROM=python:3.13-slim
FROM node:22-bookworm-slim AS livesync-build
RUN apt-get update && apt-get install -y --no-install-recommends git python3 make g++ ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /upstream
RUN git clone https://github.com/vrtmrz/obsidian-livesync.git . \
    && git checkout e4d47f4f1d73d7c5b0635ff7068ff7da994eb731
RUN npm ci && npm run build -w self-hosted-livesync-cli \
    && test -s src/apps/cli/dist/index.cjs

FROM $BUILD_FROM
WORKDIR /app
# Node 22 is required by the official CLI. The local CLI database is isolated.
RUN apt-get update && apt-get install -y --no-install-recommends libstdc++6 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=livesync-build /usr/local/bin/node /usr/local/bin/node
COPY --from=livesync-build /upstream/src/apps/cli/dist /opt/livesync-cli/dist
COPY --from=livesync-build /upstream/node_modules /opt/livesync-cli/node_modules
RUN mkdir -p /data/livesync-client \
    && test -s /opt/livesync-cli/dist/index.cjs \
    && node --version \
    && node /opt/livesync-cli/dist/index.cjs --help >/dev/null
RUN pip install --no-cache-dir flask==3.1.1 Markdown==3.8.2 gunicorn==23.0.0 cryptography==46.0.3
COPY server.py livesync_plain.py livesync_crypto.py livesync_metadata.py livesync_write_preflight.py couchdb_cas.py livesync_cli_bridge.py /app/
EXPOSE 8099
CMD ["sh", "-c", "mkdir -p /data/livesync-client && chmod 700 /data/livesync-client && exec gunicorn --bind 0.0.0.0:8099 --workers 1 --threads 4 --access-logfile - server:app"]
