FROM node:24.21.0-bookworm-slim@sha256:d6aa754f16b3197301076f047b5def2f02ea1dbbc2ca920407d46d7ec7f87b20 AS upstream
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /src
ARG NOD_UPSTREAM_REV=6670bc233b6b7dddaa75b25b89b4a89f0e92bcac
RUN git init && git remote add origin https://github.com/n8n-io/nod.git && git fetch --depth=1 origin "$NOD_UPSTREAM_REV" && git checkout --detach FETCH_HEAD && test "$(git rev-parse HEAD)" = "$NOD_UPSTREAM_REV"

FROM node:24.21.0-bookworm-slim@sha256:d6aa754f16b3197301076f047b5def2f02ea1dbbc2ca920407d46d7ec7f87b20 AS build
WORKDIR /app
COPY --from=upstream /src/package.json /src/pnpm-lock.yaml /src/pnpm-workspace.yaml ./
COPY --from=upstream /src/patches ./patches
RUN corepack enable && pnpm install --frozen-lockfile && pnpm store prune
COPY --from=upstream /src/src ./src
RUN node_modules/.bin/esbuild src/providers/container-browser/worker.ts src/providers/container-browser/bridge.ts --bundle --platform=node --format=esm --outdir=/out --out-extension:.js=.mjs \
    && agent="node_modules/agent-browser/bin/agent-browser-linux-$(node -p process.arch)" \
    && install -D -m 555 "$agent" "/out/$agent" \
    && install -D -m 555 src/providers/container-browser/chromium.sh /out/src/providers/container-browser/chromium.sh

FROM node:24.21.0-bookworm-slim@sha256:d6aa754f16b3197301076f047b5def2f02ea1dbbc2ca920407d46d7ec7f87b20 AS browser
ARG NOD_RUNTIME_REFRESH
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium xvfb xauth xdotool ffmpeg fonts-liberation fonts-noto-core fonts-noto-cjk fonts-noto-color-emoji ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=build /out ./
COPY --from=upstream --chmod=555 /src/src/providers/container-browser/xvfb.sh /usr/local/bin/Xvfb
RUN mkdir /data && chown node:node /data && chmod 700 /data
USER node
CMD ["node", "/app/worker.mjs"]

FROM browser AS eval
COPY --from=build /app/package.json ./
COPY --from=build /app/node_modules ./node_modules

FROM browser

USER root
RUN apt-get update && apt-get install -y --no-install-recommends iptables util-linux && rm -rf /var/lib/apt/lists/*
COPY --from=upstream /src/LICENSE /usr/share/doc/nod/LICENSE
COPY --chmod=555 run.sh /app/ha-browser-run.sh
RUN sh -n /app/ha-browser-run.sh
ENTRYPOINT ["/app/ha-browser-run.sh"]
CMD []
