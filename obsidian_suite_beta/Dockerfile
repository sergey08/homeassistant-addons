FROM ghcr.io/vrtmrz/livesync-cli:1.0.39-cli
ARG BUILD_VERSION=0.2.7-beta.1
ARG BUILD_ARCH
LABEL io.hass.version="${BUILD_VERSION}" io.hass.type="app" io.hass.arch="${BUILD_ARCH}"
USER root
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-venv ca-certificates \
  && rm -rf /var/lib/apt/lists/*
RUN python3 -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir "mcp==1.30.0" "uvicorn==0.54.0"
COPY server.py /opt/obsidian/server.py
COPY supervisor.py /opt/obsidian/supervisor.py
COPY vault_selection.py /opt/obsidian/vault_selection.py
COPY shared_vault_preflight.py /opt/obsidian/shared_vault_preflight.py
COPY prepare_shared_vault.py /opt/obsidian/prepare_shared_vault.py
COPY preflight.py /opt/obsidian/preflight.py
COPY onboarding.py /opt/obsidian/onboarding.py
COPY settings_import.py /opt/obsidian/settings_import.py
COPY couchdb_check.py /opt/obsidian/couchdb_check.py
COPY tunnel_key.py /opt/obsidian/tunnel_key.py
COPY tunnel_installer.py /opt/obsidian/tunnel_installer.py
ENTRYPOINT ["/opt/venv/bin/python", "/opt/obsidian/supervisor.py"]
