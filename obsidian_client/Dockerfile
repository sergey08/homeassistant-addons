# Build the upstream protocol implementation from a pinned revision.
ARG BUILD_FROM=python:3.13-slim
FROM node:22-bookworm-slim AS livesync-build
RUN apt-get update && apt-get install -y --no-install-recommends git python3 make g++ ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /upstream
RUN git clone https://github.com/vrtmrz/obsidian-livesync.git . \
    && git checkout e4d47f4f1d73d7c5b0635ff7068ff7da994eb731
# The pinned upstream CLI currently returns only success/failure for most
# replication errors. Emit bounded status/reason tokens, never exception text.
RUN python3 - <<'PY'
from pathlib import Path
p = Path("src/apps/cli/commands/runCommand.ts")
s = p.read_text()
needle = '            const recoveryHint = result.status === "failed" ? result.recoveryHint : undefined;'
assert s.count(needle) == 1, "upstream sync implementation changed"
patch = needle + """
            // HA diagnostics: fixed-format tokens, no URLs or document content.
            const safeToken = (value: unknown): string =>
                typeof value === "string" && /^[A-Za-z0-9_-]{1,64}$/.test(value)
                    ? value : "unspecified";
            writeStderrLine(
                standardIo,
                `[HA_SYNC_STATUS] status=${safeToken(result.status)} reason=${safeToken(recoveryHint?.reason)} fields=${Object.keys(result).filter(k => /^[A-Za-z][A-Za-z0-9]{0,30}$/.test(k)).slice(0,12).join(",") || "none"}`
            );
"""
s = s.replace(needle, patch)
fetch_needle = '            writeStderrLine(standardIo, "[Error] Fetch failed:", error);'
assert s.count(fetch_needle) == 1, "upstream fetch implementation changed"
fetch_patch = """            // Only report bounded error class/code, never exception message.
            const fetchToken = (value: unknown): string =>
                typeof value === "string" && /^[A-Za-z0-9_-]{1,40}$/.test(value)
                    ? value : "unspecified";
            const fetchError = error instanceof Error ? error : undefined;
            const fetchCode = error && typeof error === "object" && "code" in error
                ? (error as {code?: unknown}).code : undefined;
            // Only fixed categories, never expose exception messages.
            const message = fetchError?.message || "";
            const cause = fetchError?.cause;
            const causeName = cause instanceof Error ? cause.name : "unspecified";
            const detail = /cannot read properties of (undefined|null)/i.test(message)
                ? "null_property" : /is not a function/i.test(message) ? "not_function"
                : /fetch failed|network/i.test(message) ? "network"
                : /decrypt|encrypt|passphrase/i.test(message) ? "encryption"
                : /invalid url|failed to parse url/i.test(message) ? "invalid_url"
                : /cannot read properties|cannot set properties|undefined|null/i.test(message) ? "undefined_value"
                : /not iterable|not async iterable|cannot destructure/i.test(message) ? "invalid_structure"
                : /cannot convert|invalid argument|expected .* (string|object)/i.test(message) ? "invalid_argument"
                : /database is closed|database closed|database is destroyed/i.test(message) ? "database_closed"
                : /permission denied|access denied|eacces/i.test(message) ? "permission"
                : "other";
            const stack = fetchError?.stack || "";
            const topFrame = stack.split("\\n").slice(1).find(line => /^\\s*at\\s+/.test(line)) || "";
            const origin = /replicat|couchdb|pouchdb/i.test(topFrame) ? "replication"
                : /storage|vault|filesystem/i.test(topFrame) ? "storage"
                : /encrypt|crypt|decrypt/i.test(topFrame) ? "crypto"
                : /setting|config/i.test(topFrame) ? "settings"
                : /rebuilder|rebuildLocal|fetchLocal/i.test(topFrame) ? "rebuilder"
                : "unknown";
            writeStderrLine(standardIo,
                `[HA_FETCH_FAILURE] type=${fetchToken(fetchError?.name)} code=${fetchToken(fetchCode)} detail=${detail} cause=${fetchToken(causeName)} origin=${origin}`);
"""
s = s.replace(fetch_needle, fetch_patch + fetch_needle)
p.write_text(s)
PY
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
