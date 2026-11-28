FROM node:24.21.0-bookworm-slim@sha256:d6aa754f16b3197301076f047b5def2f02ea1dbbc2ca920407d46d7ec7f87b20 AS upstream
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /src
RUN git init && git remote add origin https://github.com/n8n-io/nod.git && git fetch --depth=1 origin 8494bcf12030451ad1093f0579bba57caf34c1d9 && git checkout --detach FETCH_HEAD && test "$(git rev-parse HEAD)" = 8494bcf12030451ad1093f0579bba57caf34c1d9

COPY extract-upstream.mjs /tmp/extract-upstream.mjs
RUN node /tmp/extract-upstream.mjs /src /opt/nod-workspace-programs

FROM rust:1.100.0-bookworm@sha256:ade39a710ef85f3506cffcfec3e8a24ba090badef1dff2fb798f71d878833fea AS rtk
COPY --from=upstream /src/src/providers/docker/install-rtk.sh /tmp/install-rtk.sh
RUN sh /tmp/install-rtk.sh

FROM node:24.21.0-bookworm-slim@sha256:d6aa754f16b3197301076f047b5def2f02ea1dbbc2ca920407d46d7ec7f87b20
ARG NOD_RUNTIME_REFRESH
RUN apt-get update && apt-get install -y --no-install-recommends iptables python3 python-is-python3 python3-pip python3-venv python3-requests python3-bs4 pipx ffmpeg poppler-utils jq tesseract-ocr tesseract-ocr-eng tesseract-ocr-deu tesseract-ocr-por tesseract-ocr-spa tesseract-ocr-fra ca-certificates curl git unzip ripgrep libreoffice-writer-nogui libreoffice-calc-nogui libreoffice-impress-nogui fonts-liberation fonts-crosextra-carlito fonts-crosextra-caladea fonts-noto-core fonts-noto-cjk fonts-noto-color-emoji qpdf ghostscript zip xz-utils file sqlite3 tesseract-ocr-cat tesseract-ocr-ita tesseract-ocr-nld && rm -rf /var/lib/apt/lists/*
COPY --from=upstream /src/src/providers/docker/workspace-video.txt /tmp/workspace-video.txt
RUN python3 -m venv /opt/yt-dlp && /opt/yt-dlp/bin/pip install --no-cache-dir --require-hashes -r /tmp/workspace-video.txt && ln -s /opt/yt-dlp/bin/yt-dlp /usr/local/bin/yt-dlp
COPY --from=upstream --chmod=555 /src/src/providers/docker/save-video.py /usr/local/bin/save-video
COPY --from=upstream /src/src/providers/docker/workspace-artifacts.txt /tmp/workspace-artifacts.txt
RUN python3 -m venv --system-site-packages /opt/nod-artifacts && /opt/nod-artifacts/bin/pip install --no-cache-dir --require-hashes -r /tmp/workspace-artifacts.txt
COPY --from=rtk --chmod=555 /opt/rtk/bin/rtk /usr/local/bin/rtk
COPY --from=rtk /opt/rtk/LICENSE /usr/share/doc/rtk/LICENSE
RUN mkdir -p /workspace /home/node/.local/bin && chown -R node:node /workspace /home/node
RUN groupadd --gid 1002 nod-connected && useradd --uid 1002 --gid 1002 --create-home --shell /usr/sbin/nologin nod-connected && chmod 700 /home/nod-connected
COPY --from=upstream --chmod=555 /src/src/providers/docker/workspace-network.sh /usr/local/bin/nod-workspace-network
USER root
ENV LANG=C.UTF-8
ENV NPM_CONFIG_PREFIX=/home/node/.local
ENV PIPX_HOME=/home/node/.local/pipx
ENV PIPX_BIN_DIR=/home/node/.local/bin
ENV PATH=/opt/nod-artifacts/bin:/home/node/.local/bin:$PATH
WORKDIR /workspace

# HA preflight: optional fixed probe only; no host mounts.
RUN apt-get update && apt-get install -y --no-install-recommends util-linux && rm -rf /var/lib/apt/lists/*
COPY --from=upstream /src/LICENSE /usr/share/doc/nod/LICENSE
RUN groupadd -g 1001 nodgateway && useradd -M -u 1001 -g 1001 -s /usr/sbin/nologin nodgateway
COPY --from=upstream /opt/nod-workspace-programs /opt/nod-workspace-programs
COPY prepare-config.mjs resolve-server-peer.mjs transport.mjs probe-worker.mjs command-session.mjs resource-policy.mjs command-entry.py /app/
RUN node --check /app/resolve-server-peer.mjs && node --check /app/prepare-config.mjs && node --check /app/transport.mjs && node --check /app/probe-worker.mjs && node --check /app/command-session.mjs && node --check /app/resource-policy.mjs && python3 -m py_compile /app/command-entry.py /opt/nod-workspace-programs/command.py /opt/nod-workspace-programs/stop.py
COPY --chmod=555 run.sh /usr/local/bin/nod-ha-workspace-preflight
COPY --chmod=444 selftest.py /opt/nod-workspace-selftest.py
RUN sh -n /usr/local/bin/nod-ha-workspace-preflight
ENTRYPOINT ["/usr/local/bin/nod-ha-workspace-preflight"]
CMD []
