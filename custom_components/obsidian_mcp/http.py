"""Forward authenticated Streamable HTTP requests to the private MCP server."""

import asyncio
from hmac import compare_digest

from aiohttp import ClientError, ClientTimeout, web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from .const import DOMAIN

MAX_BODY = 8 * 1024 * 1024
REQUEST_HEADERS = ("Accept", "Content-Type", "MCP-Protocol-Version", "Mcp-Session-Id", "Last-Event-ID")
RESPONSE_HEADERS = ("Content-Type", "MCP-Protocol-Version", "Mcp-Session-Id", "Retry-After")


class MCPView(HomeAssistantView):
    """Expose optional Bearer authentication on the Home Assistant HTTP listener."""

    url = "/api/obsidian_mcp/mcp"
    name = "api:obsidian_mcp:mcp"
    requires_auth = False

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    async def post(self, request: web.Request) -> web.StreamResponse:
        return await self._forward(request)

    get = delete = post

    async def _forward(self, request: web.Request) -> web.StreamResponse:
        runtime = self.hass.data.get(DOMAIN)
        if not runtime or not runtime.url or runtime.client is None:
            raise web.HTTPNotFound()

        client, url = runtime.client, runtime.url

        # A browser-originated request is never required by the server-to-server clients.
        if "Origin" in request.headers:
            raise web.HTTPForbidden()
        scheme, _, token = request.headers.get("Authorization", "").partition(" ")
        expected = runtime.options["remote_mcp_api_key"]
        if scheme.lower() != "bearer" or not compare_digest(token.encode(), expected.encode()):
            raise web.HTTPUnauthorized(headers={"WWW-Authenticate": 'Bearer realm="Obsidian MCP"'})

        payload = bytearray()
        async for chunk in request.content.iter_chunked(65536):
            payload.extend(chunk)
            if len(payload) > MAX_BODY:
                raise web.HTTPRequestEntityTooLarge(max_size=MAX_BODY, actual_size=len(payload))

        headers = {key: request.headers[key] for key in REQUEST_HEADERS if key in request.headers}
        response = None
        try:
            async with client.request(
                request.method,
                url,
                data=bytes(payload) if payload else None,
                headers=headers,
                allow_redirects=False,
                timeout=ClientTimeout(total=None, connect=5, sock_read=120),
            ) as upstream:
                result_headers = {
                    key: upstream.headers[key]
                    for key in RESPONSE_HEADERS
                    if key in upstream.headers
                }
                result_headers["Cache-Control"] = "no-store"
                response = web.StreamResponse(status=upstream.status, headers=result_headers)
                await response.prepare(request)
                async for chunk in upstream.content.iter_any():
                    await response.write(chunk)
                await response.write_eof()
        except (ClientError, asyncio.TimeoutError):
            if response is None or not response.prepared:
                raise web.HTTPBadGateway() from None
            response.force_close()
        return response
