"""Exercise the Obsidian integration against a disposable Home Assistant Core."""

import asyncio
import json
import logging
from pathlib import Path
import shutil
import socket
from tempfile import TemporaryDirectory
from unittest.mock import patch

from ifaddr import Adapter, IP

from aiohttp import ClientSession
from homeassistant import config_entries, loader
from homeassistant.bootstrap import async_load_base_functionality, async_process_ha_core_config
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.setup import async_setup_component

DOMAIN = "obsidian_mcp"
TOKEN = "a-local-test-token-that-is-not-a-secret"
HEADERS = {"Accept": "application/json, text/event-stream"}
INITIALIZE = {
    "protocolVersion": "2025-06-18",
    "capabilities": {},
    "clientInfo": {"name": "integration-smoke", "version": "1"},
}


async def request(client, endpoint, method, params, headers=HEADERS):
    async with client.post(endpoint, headers=headers, json={
        "jsonrpc": "2.0", "id": 1, "method": method, "params": params
    }) as response:
        if response.status != 200:
            return response.status, None
        return response.status, await response.json()


async def call_tool(client, endpoint, name, arguments, headers=HEADERS):
    status, payload = await request(
        client, endpoint, "tools/call", {"name": name, "arguments": arguments}, headers
    )
    assert status == 200 and "result" in payload, payload
    return payload["result"]


async def smoke(config, port):
    hass = HomeAssistant(str(config))
    loader.async_setup(hass)
    hass.config.skip_pip = True
    endpoint = f"http://127.0.0.1:{port}/api/obsidian_mcp/mcp"
    ha_config = {"http": {"server_host": "127.0.0.1", "server_port": port}}

    try:
        hass.config_entries = config_entries.ConfigEntries(hass, ha_config)
        await loader.async_get_custom_components(hass)
        assert await async_load_base_functionality(hass)
        await async_process_ha_core_config(hass, {})
        # Some CI sandboxes disallow enumerating network interfaces. The HTTP
        # server and all MCP traffic still use a real loopback socket.
        loopback = Adapter("lo", "lo", [IP("127.0.0.1", 8, "lo")])
        with patch("ifaddr.get_adapters", return_value=[loopback]):
            assert await async_setup_component(hass, "http", ha_config)
        await hass.async_start()
        flow = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
        assert flow["type"] is FlowResultType.FORM, flow
        values = {
            "storage_mode": "livesync",
            "enable_livesync": False,
            "livesync_interval": 60,
            "enable_tunnel": False,
            "enable_remote_mcp": False,
        }
        created = await hass.config_entries.flow.async_configure(flow["flow_id"], values)
        assert created["type"] is FlowResultType.CREATE_ENTRY, created
        await hass.async_block_till_done()
        entry = created["result"]
        assert entry.state.value == "loaded", entry.state
        runtime = entry.runtime_data
        assert runtime.url.startswith("http://127.0.0.1:")

        async with ClientSession() as client:
            assert (await request(client, endpoint, "initialize", INITIALIZE))[0] == 404
            status, reply = await request(client, runtime.url, "initialize", INITIALIZE)
            assert status == 200 and reply["result"]["serverInfo"]["name"] == "Obsidian HA", reply

            reconfigure = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": "reconfigure", "entry_id": entry.entry_id}
            )
            changed = await hass.config_entries.flow.async_configure(reconfigure["flow_id"], {
                **values, "enable_remote_mcp": True, "remote_mcp_api_key": TOKEN
            })
            assert changed["type"] is FlowResultType.ABORT, changed
            await hass.async_block_till_done()
            assert runtime.url is None and entry.runtime_data.url

            assert (await request(client, endpoint, "initialize", INITIALIZE))[0] == 401
            assert (await request(client, endpoint, "initialize", INITIALIZE, {
                **HEADERS, "Authorization": "Bearer incorrect"
            }))[0] == 401
            auth = {**HEADERS, "Authorization": f"Bearer {TOKEN}"}
            assert (await request(client, endpoint, "initialize", INITIALIZE, {
                **auth, "Origin": "https://example.org"
            }))[0] == 403
            status, reply = await request(client, endpoint, "tools/list", {}, auth)
            assert status == 200 and {tool["name"] for tool in reply["result"]["tools"]} == {
                "list_notes", "search_notes", "read_note", "read_note_with_revision",
                "note_revision", "write_note", "append_note", "rename_note", "delete_note",
            }, reply

            written = await call_tool(
                client, endpoint, "write_note", {"name": "Example.md", "content": "# Example"}, auth
            )
            assert not written.get("isError"), written
            revision = await call_tool(
                client, endpoint, "read_note_with_revision", {"name": "Example.md"}, auth
            )
            info = revision.get("structuredContent") or json.loads(revision["content"][0]["text"])
            assert info["content"] == "# Example", revision
            stale = await call_tool(client, endpoint, "append_note", {
                "name": "Example.md", "content": " altered", "expected_sha256": "stale"
            }, auth)
            assert stale["isError"], stale
            appended = await call_tool(client, endpoint, "append_note", {
                "name": "Example.md", "content": " changed", "expected_sha256": info["sha256"]
            }, auth)
            assert not appended.get("isError"), appended
            moved = await call_tool(client, endpoint, "rename_note", {
                "source": "Example.md", "destination": "Folder/Example.md"
            }, auth)
            assert not moved.get("isError"), moved
            deleted = await call_tool(client, endpoint, "delete_note", {"name": "Folder/Example.md"}, auth)
            assert not deleted.get("isError"), deleted
            trash = config / DOMAIN / "mcp-trash" / "deleted"
            assert next(trash.glob("*/Folder/Example.md")).read_text() == "# Example changed"

            assert await hass.config_entries.async_unload(entry.entry_id)
            assert (await request(client, endpoint, "initialize", INITIALIZE, auth))[0] == 404
    finally:
        await hass.async_stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    with TemporaryDirectory(prefix="obsidian-mcp-") as temporary:
        config = Path(temporary)
        source = Path(__file__).resolve().parents[1] / "custom_components" / DOMAIN
        shutil.copytree(source, config / "custom_components" / DOMAIN)
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        asyncio.run(smoke(config, port))
        print("Obsidian MCP integration smoke test passed.")
