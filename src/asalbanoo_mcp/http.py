"""Shared async HTTP client for asalbanooshop.com.

Every tool goes through `rest` (WordPress REST JSON), `ajax` (admin-ajax HTML fragments) or
`get_page` (server-rendered HTML). `_send` caps concurrency, solves the site's HTTP 418 cookie
challenge, retries once when the server drops the connection, and turns HTTP failures into
`ToolError` messages the model can act on.
"""

from __future__ import annotations

import asyncio
import os
import re
from typing import Any

import httpx
from mcp.server.mcpserver.exceptions import ToolError

BASE = "https://asalbanooshop.com"

HEADERS = {
    # A python/httpx User-Agent gets HTTP 403 from the WAF; a browser one works.
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/140.0.0.0 Safari/537.36",
}

MAX_CONCURRENCY = 4
CHALLENGE = re.compile(r"_dgjsc=([a-f0-9]{32}:[0-9]{14})")

_transport: httpx.AsyncBaseTransport | None = None
_client: httpx.AsyncClient | None = None
_limit: asyncio.Semaphore | None = None


class ApiError(ToolError):
    """A failed upstream call."""


def set_transport(transport: httpx.AsyncBaseTransport | None) -> None:
    """Swap the transport (tests use httpx.MockTransport). Drops the current client."""
    global _transport, _client, _limit
    _transport, _client, _limit = transport, None, None


def _get_client() -> tuple[httpx.AsyncClient, asyncio.Semaphore]:
    global _client, _limit
    if _client is None:
        # Direct connections work; a system proxy is only used when the user opts in
        # with ASALBANOO_MCP_PROXY.
        _client = httpx.AsyncClient(
            transport=_transport,
            headers=HEADERS,
            timeout=30,
            follow_redirects=True,
            trust_env=False,
            proxy=os.environ.get("ASALBANOO_MCP_PROXY") or None,
        )
        _limit = asyncio.Semaphore(MAX_CONCURRENCY)
    assert _limit is not None
    return _client, _limit


async def rest(route: str, params: dict[str, Any] | None = None) -> tuple[Any, int | None]:
    """GET /wp-json/<route>; returns (parsed body, X-WP-Total header or None)."""
    r = await _send("GET", f"{BASE}/wp-json/{route}", params=params)
    try:
        data = r.json()
    except ValueError as e:
        raise ApiError(f"asalbanooshop.com returned a non-JSON response for {route} (HTTP {r.status_code}).") from e
    total = r.headers.get("X-WP-Total")
    return data, int(total) if total and total.isdigit() else None


async def ajax(action: str, params: dict[str, Any]) -> str:
    """GET /wp-admin/admin-ajax.php?action=<action> and return the body text."""
    r = await _send("GET", f"{BASE}/wp-admin/admin-ajax.php", params={"action": action, **params})
    return r.content.decode("utf-8", "replace")


async def get_page(path: str, params: dict[str, Any] | None = None) -> tuple[str, str]:
    """GET a site page; returns (final URL after redirects, HTML)."""
    r = await _send("GET", f"{BASE}{path}", params=params)
    # Cached pages come without a charset header; they are always UTF-8.
    return str(r.url), r.content.decode("utf-8", "replace")


async def _send(method: str, url: str, **kwargs: Any) -> httpx.Response:
    client, limit = _get_client()
    for attempt in (1, 2, 3):
        try:
            async with limit:
                r = await client.request(method, url, **kwargs)
        except httpx.TimeoutException as e:
            raise ApiError("asalbanooshop.com did not answer in time. Try again in a moment.") from e
        except httpx.TransportError as e:
            # The server sometimes closes a keep-alive connection; a second try works.
            if attempt >= 2:
                raise ApiError(
                    f"Could not reach asalbanooshop.com ({type(e).__name__}). Check the internet connection, "
                    "or set ASALBANOO_MCP_PROXY."
                ) from e
            continue
        # HTTP 418 = bot challenge: a JS page that sets the _dgjsc cookie (valid about 2 h) and reloads.
        m = CHALLENGE.search(r.text) if r.status_code == 418 else None
        if not m or attempt == 3:
            break
        client.cookies.set("_dgjsc", m.group(1), domain="asalbanooshop.com", path="/")
    if r.status_code >= 400:
        raise ApiError(_status_message(r))
    return r


def _status_message(r: httpx.Response) -> str:
    code = r.status_code
    if code == 418:
        return "asalbanooshop.com kept answering with its bot challenge (HTTP 418). Try again in a moment."
    if code == 403:
        return "asalbanooshop.com blocked the request (HTTP 403). Turn off VPN/proxy or set ASALBANOO_MCP_PROXY."
    if code == 404:
        return "Not found on asalbanooshop.com (HTTP 404). Check the product id, category or brand slug."
    if code == 429:
        return "asalbanooshop.com is rate limiting requests (HTTP 429). Wait a minute before retrying."
    if code >= 500:
        return f"asalbanooshop.com had a server error (HTTP {code}). Try again later."
    try:  # WordPress REST errors: {"code": "rest_invalid_param", "message": "..."}
        detail = r.json().get("message")
    except (ValueError, AttributeError):
        detail = None
    return f"asalbanooshop.com rejected the request (HTTP {code}){': ' + str(detail)[:300] if detail else '.'}"
