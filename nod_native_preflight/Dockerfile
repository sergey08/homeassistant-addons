FROM node:24.21.0-bookworm-slim@sha256:d6aa754f16b3197301076f047b5def2f02ea1dbbc2ca920407d46d7ec7f87b20 AS build
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
RUN git init && git remote add origin https://github.com/n8n-io/nod.git && git fetch --depth=1 origin 6670bc233b6b7dddaa75b25b89b4a89f0e92bcac && git checkout --detach FETCH_HEAD && test "$(git rev-parse HEAD)" = 6670bc233b6b7dddaa75b25b89b4a89f0e92bcac
COPY patch-embedded-ui.mjs /tmp/patch-embedded-ui.mjs
RUN node /tmp/patch-embedded-ui.mjs
RUN corepack enable && pnpm install --frozen-lockfile && pnpm exec vite build && pnpm prune --prod && pnpm store prune

FROM node:24.21.0-bookworm-slim@sha256:d6aa754f16b3197301076f047b5def2f02ea1dbbc2ca920407d46d7ec7f87b20 AS node
FROM docker:29.8.2-cli@sha256:35cfcf893c20f2931f4909151b5407aaaeab711277de7ce8b8f521f095d54c32 AS docker
FROM postgres:17-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends openssl ca-certificates && rm -rf /var/lib/apt/lists/* && groupadd -g 1000 node && useradd -m -u 1000 -g 1000 node && groupadd -g 1001 nodrelay && useradd -M -u 1001 -g 1001 -s /usr/sbin/nologin nodrelay
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=docker /usr/local/bin/docker /usr/local/bin/docker
WORKDIR /app
COPY --from=build --chown=node:node /app/package.json ./
COPY --from=build --chown=node:node /app/node_modules ./node_modules
COPY --from=build --chown=node:node /app/src ./src
COPY --from=build --chown=node:node /app/dist ./dist
COPY --from=build --chown=node:node /app/docs/src/content/docs ./docs/src/content/docs
COPY --from=build /app/deployment/self-host/healthcheck.mjs ./healthcheck.mjs
COPY --from=build /app/LICENSE /usr/share/doc/nod/LICENSE
COPY ingress.mjs /app/ingress.mjs
COPY https-relay.mjs relay-config.mjs relay-start.mjs /app/
RUN node --check /app/ingress.mjs && node --check /app/https-relay.mjs && node --check /app/relay-config.mjs && node --check /app/relay-start.mjs
COPY run.sh /usr/local/bin/nod-native-preflight
RUN chmod 0755 /usr/local/bin/nod-native-preflight && sh -n /usr/local/bin/nod-native-preflight && node --version && postgres --version
ENTRYPOINT ["/usr/local/bin/nod-native-preflight"]
