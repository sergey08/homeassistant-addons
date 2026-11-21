# Reuse the official CLI bundle and rebuild its runtime dependencies for HA Core's Alpine base.
FROM ghcr.io/vrtmrz/livesync-cli:1.0.39-cli AS upstream

FROM node:22-alpine3.23 AS runtime
RUN apk add --no-cache git python3 make g++
WORKDIR /source
RUN git init --quiet \
    && git fetch --depth=1 https://github.com/vrtmrz/obsidian-livesync.git 11edc6edef6291dd90ad10e33cf726ee5f7f82e0 \
    && git checkout --quiet --detach FETCH_HEAD \
    && npm ci --omit=dev --workspace self-hosted-livesync-cli --no-audit --no-fund \
    && npm rebuild leveldown --build-from-source
RUN mkdir -p /bundle/bin /bundle/livesync-runtime \
    && cp /usr/local/bin/node /bundle/livesync-runtime/node \
    && wget -qO /bundle/livesync-runtime/LICENSE.node "https://raw.githubusercontent.com/nodejs/node/$(node -v)/LICENSE" \
    && cp LICENSE /bundle/livesync-runtime/LICENSE.livesync \
    && mv node_modules /bundle/livesync-runtime/
COPY --from=upstream /app/dist /bundle/livesync-runtime/dist
COPY --chmod=755 livesync-cli /bundle/bin/livesync-cli

FROM scratch AS bundle
COPY --from=runtime /bundle/ /
