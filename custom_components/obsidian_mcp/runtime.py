"""MCP transport and optional LiveSync and secure tunnel processes."""

import asyncio
from contextlib import AsyncExitStack, contextmanager
from dataclasses import dataclass
import logging
import os
from pathlib import Path
import socket

from aiohttp import ClientSession, DummyCookieJar
import uvicorn

from .server import create_app
from .vault_selection import select_storage

_LOGGER = logging.getLogger(__name__)


def require_file(path: Path, *, executable: bool = False) -> Path:
    """Validate a privately provisioned file before use."""
    mode = os.X_OK if executable else os.R_OK
    if not path.is_file() or not os.access(path, mode):
        raise ValueError(f"Required file unavailable: {path.name}")
    return path


@dataclass(frozen=True)
class Storage:
    """Resolved storage and service prerequisites."""

    base: Path
    vault: Path
    trash: Path
    sync: bool

    @classmethod
    def check(cls, base: Path, options: dict) -> "Storage":
        """Validate configuration without creating files."""
        _, vault, sync = select_storage(options, base / "vault")
        trash = base / "mcp-trash"
        for folder in (base, vault, trash):
            if folder.is_symlink() or (folder.exists() and not folder.is_dir()):
                raise ValueError(f"Invalid directory: {folder.name}")
        if vault.exists() and not os.access(vault, os.R_OK | os.W_OK | os.X_OK):
            raise ValueError("Vault is not writable")
        if options.get("enable_remote_mcp") and len(options.get("remote_mcp_api_key", "")) < 32:
            raise ValueError("Remote MCP requires a key of at least 32 characters")
        if sync:
            require_file(base / "bin/livesync-cli", executable=True)
            require_file(base / "settings/livesync-operativo.json")
        if options.get("enable_tunnel"):
            if not options.get("tunnel_id", "").strip().startswith("tunnel_"):
                raise ValueError("Missing tunnel ID")
            require_file(base / "tunnel/bin/tunnel-client", executable=True)
            require_file(base / "tunnel/api-key")
        return cls(base, vault, trash, sync)

    def prepare(self, options: dict) -> None:
        """Prepare private folders for the enabled components."""
        self.base.mkdir(mode=0o700, parents=True, exist_ok=True)
        if self.vault == self.base / "vault":
            self.vault.mkdir(mode=0o700, exist_ok=True)
        self.trash.mkdir(mode=0o700, exist_ok=True)
        if self.sync:
            (self.base / "livesync-db").mkdir(mode=0o700, exist_ok=True)
        if options.get("enable_tunnel"):
            (self.base / "tunnel/run").mkdir(mode=0o700, exist_ok=True)


class LoopbackServer(uvicorn.Server):
    """Serve privately without replacing Home Assistant's signal handlers."""

    @contextmanager
    def capture_signals(self):
        yield


class Runtime:
    """Own the transport and background processes for one config entry."""

    def __init__(self, storage: Storage, options: dict) -> None:
        self.storage = storage
        self.options = options
        self.url: str | None = None
        self.client: ClientSession | None = None
        self.resources = AsyncExitStack()
        self.processes: dict[str, asyncio.subprocess.Process] = {}

    async def start(self) -> None:
        """Start the private MCP server before launching optional clients."""
        try:
            await self._start_mcp()
            if self.options.get("enable_remote_mcp"):
                self.client = await self.resources.enter_async_context(
                    ClientSession(cookie_jar=DummyCookieJar())
                )
            base = self.storage.base
            if self.storage.sync:
                await self._start_process(
                    "LiveSync",
                    str(base / "bin/livesync-cli"),
                    "--settings", str(base / "settings/livesync-operativo.json"),
                    "--vault", str(self.storage.vault),
                    "--interval", str(self.options.get("livesync_interval", 60)),
                    env={**os.environ, "LIVESYNC_DB_PATH": str(base / "livesync-db")},
                )
            if self.options.get("enable_tunnel"):
                await self._start_process(
                    "OpenAI tunnel",
                    str(base / "tunnel/bin/tunnel-client"), "run",
                    "--control-plane.tunnel-id", self.options["tunnel_id"].strip(),
                    "--control-plane.api-key", f"file:{base / 'tunnel/api-key'}",
                    "--mcp.server-url", f"channel=main,url={self.url}",
                    "--health.listen-addr", "127.0.0.1:0",
                    "--health.url-file", str(base / "tunnel/run/health.url"),
                )
        except BaseException:
            await self.stop()
            raise

    async def _start_mcp(self) -> None:
        sock = socket.socket()
        self.resources.callback(sock.close)
        sock.bind(("127.0.0.1", 0))
        sock.setblocking(False)
        app = create_app(self.storage.vault, self.storage.trash)
        server = LoopbackServer(uvicorn.Config(
            app,
            lifespan="on",
            ws="none",
            http="h11",
            access_log=False,
            log_config=None,
            proxy_headers=False,
            timeout_graceful_shutdown=5,
        ))
        task = asyncio.create_task(server.serve(sockets=[sock]))

        async def shutdown():
            server.should_exit = True
            if task.done():
                await asyncio.gather(task, return_exceptions=True)
            else:
                try:
                    await asyncio.wait_for(task, timeout=10)
                except TimeoutError:
                    _LOGGER.warning("Obsidian MCP HTTP server shutdown timed out")

        self.resources.push_async_callback(shutdown)
        async with asyncio.timeout(10):
            while not server.started:
                if task.done():
                    await task
                    raise RuntimeError("MCP listener stopped before startup")
                await asyncio.sleep(0.05)
        self.url = f"http://127.0.0.1:{sock.getsockname()[1]}/mcp"

    async def _start_process(self, name: str, *argv: str, env=None) -> None:
        # Do not pass Supervisor credentials or other HA-specific secrets to children.
        source = os.environ if env is None else env
        child_env = {
            key: source[key]
            for key in (
                "PATH", "LANG", "LC_ALL", "TZ", "SSL_CERT_FILE",
                "SSL_CERT_DIR", "NODE_EXTRA_CA_CERTS", "LIVESYNC_DB_PATH",
            )
            if key in source
        }
        child_env["HOME"] = str(self.storage.base)
        proc = await asyncio.create_subprocess_exec(
            *argv, cwd=self.storage.base, env=child_env,
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
        )
        self.processes[name] = proc

        async def watch():
            code = await proc.wait()
            _LOGGER.error("Obsidian MCP %s exited with code %d", name, code)

        watcher = asyncio.create_task(watch())

        async def shutdown():
            watcher.cancel()
            await asyncio.gather(watcher, return_exceptions=True)
            if proc.returncode is None:
                try:
                    proc.terminate()
                except ProcessLookupError:
                    pass
                try:
                    await asyncio.wait_for(proc.wait(), timeout=5)
                except TimeoutError:
                    try:
                        proc.kill()
                    except ProcessLookupError:
                        pass
                    await proc.wait()

        self.resources.push_async_callback(shutdown)

    async def stop(self) -> None:
        """Close the listener and stop every owned process."""
        self.url = None
        self.client = None
        await self.resources.aclose()
