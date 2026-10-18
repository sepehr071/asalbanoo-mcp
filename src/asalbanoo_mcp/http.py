"""Shared async HTTP client for asalbanooshop.com.

Every tool goes through `rest` (WordPress REST JSON), `ajax` (admin-ajax HTML fragments) or
`get_page` (server-rendered HTML). `_send` caps concurrency, solves the site's HTTP 418 cookie
challenge, retries timeouts, dropped connections, 429 and 5xx (never 403) with jittered backoff, and turns HTTP
failures into `ToolError` messages the model can act on. The wire format is a Chrome impersonation (curl_cffi).
"""

from __future__ import annotations

import asyncio
import os
import random
import re
import time
from collections.abc import Awaitable, Callable
from typing import Any

import httpx
from httpx_curl_cffi import AsyncCurlTransport
from mcp.server.mcpserver.exceptions import ToolError

BASE = "https://asalbanooshop.com"

# User-Agent, sec-ch-ua and TLS come from the impersonated Chrome profile (see _get_client).
# The site's own JS calls are same-origin fetches; get_page overrides these with navigation values.
HEADERS = {
    "Accept": "*/*",
    "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.8",
    "Referer": f"{BASE}/",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "priority": "u=1, i",
}
PAGE_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "priority": "u=0, i",
}

MAX_CONCURRENCY = 2
JITTER = (0.15, 0.6)  # seconds before each upstream call
MAX_RETRIES = 2
MAX_RETRY_WAIT = 10  # cap for Retry-After and backoff, seconds
RETRY_DELAY = 0.5
CHALLENGE = re.compile(r"_dgjsc=([a-f0-9]{32}:[0-9]{14})")

_transport: httpx.AsyncBaseTransport | None = None
_client: httpx.AsyncClient | None = None
_limit: asyncio.Semaphore | None = None
_proxy_index = 0
_retired: set[asyncio.Task] = set()
_browser_lock: asyncio.Lock | None = None
_cleared: tuple[httpx.AsyncClient, float] | None = None
_cache: dict[Any, tuple[float, Any]] = {}


class _XhrTransport(AsyncCurlTransport):
    """The Chrome profile sends navigation-only headers; a None value makes curl drop them (API calls are XHR)."""

    def _create_request_params(self, req: httpx.Request) -> dict[str, Any]:
        p = super()._create_request_params(req)
        p["headers"] = [*p["headers"], (b"upgrade-insecure-requests", None), (b"sec-fetch-user", None)]
        return p


class ApiError(ToolError):
    """A failed upstream call. `status` is the HTTP status, or None for network errors."""

    def __init__(self, message: str, status: int | None = None, retry_after: float | None = None):
        super().__init__(message)
        self.status = status
        self.retry_after = retry_after


def set_transport(transport: httpx.AsyncBaseTransport | None) -> None:
    """Swap the transport (tests use httpx.MockTransport). Drops the current client."""
    global _transport, _client, _limit, _proxy_index, _browser_lock, _cleared
    _transport, _client, _limit, _proxy_index, _browser_lock, _cleared = transport, None, None, 0, None, None
    _cache.clear()


async def cached(key: Any, ttl: float, make: Callable[[], Awaitable[Any]]) -> Any:
    """Return make()'s result, reused for `ttl` seconds per key. Only for results nobody mutates."""
    hit = _cache.get(key)
    if hit and time.monotonic() - hit[0] < ttl:
        return hit[1]
    value = await make()
    _cache[key] = (time.monotonic(), value)
    return value


def _proxies() -> list[str]:
    """ASALBANOO_MCP_PROXY: one proxy URL, or a comma-separated list used one at a time."""
    return [p.strip() for p in os.environ.get("ASALBANOO_MCP_PROXY", "").split(",") if p.strip()]


# A bare HTML 403 is the WAF's normal refusal (e.g. /wp-json/wp/v2/users); only a bot-check page needs a browser.
_CHALLENGE_PAGE = re.compile(r"just a moment|captcha|challenge|arvan|attention required|enable javascript", re.I)


def _is_challenge(r: httpx.Response) -> bool:
    """A bot-check page: 403/429/503 with an HTML body that carries a known challenge marker."""
    return (
        r.status_code in (403, 429, 503)
        and "html" in r.headers.get("content-type", "") + r.text[:20].lower()
        and bool(_CHALLENGE_PAGE.search(r.text[:5000]))
    )


def _next_proxy(client: httpx.AsyncClient) -> None:
    """Sticky pool: move to the next proxy after a block or connect error; the next call rebuilds the client.

    Only the client that failed may rotate: a slower request that failed on an old client must not skip a good proxy.
    The old client is closed late because other requests may still be using it.
    """
    global _client, _limit, _proxy_index
    if len(_proxies()) < 2 or client is not _client:
        return
    _client, _limit, _proxy_index = None, None, _proxy_index + 1
    t = asyncio.create_task(_close_later(client))
    _retired.add(t)
    t.add_done_callback(_retired.discard)


async def _close_later(client: httpx.AsyncClient) -> None:
    await asyncio.sleep(40)  # longer than the 30 s request timeout
    await client.aclose()


def _get_client() -> tuple[httpx.AsyncClient, asyncio.Semaphore]:
    global _client, _limit
    if _client is None:
        # Direct connections work; a system proxy is only used when the user opts in with ASALBANOO_MCP_PROXY.
        # curl_cffi presents Chrome's TLS/HTTP2 fingerprint and default headers; cookies and redirects stay with
        # httpx. The proxy goes to the transport (a client-level proxy would be ignored once a transport is given).
        proxies = _proxies()
        _client = httpx.AsyncClient(
            transport=_transport
            or _XhrTransport(
                impersonate="chrome",
                default_headers=True,
                proxy=proxies[_proxy_index % len(proxies)] if proxies else None,
                max_connections=2 * MAX_CONCURRENCY,
            ),
            headers=HEADERS,
            timeout=30,
            limits=httpx.Limits(max_connections=2 * MAX_CONCURRENCY),
            follow_redirects=True,
            trust_env=False,
        )
        _limit = asyncio.Semaphore(MAX_CONCURRENCY)
    assert _limit is not None
    return _client, _limit


async def rest(route: str, params: dict[str, Any] | None = None) -> tuple[Any, int | None]:
    """GET /wp-json/<route>; returns (parsed body, X-WP-Total header or None)."""
    r = await _send("GET", f"{BASE}/wp-json/{route}", params=params, headers={"Accept": "application/json"})
    try:
        data = r.json()
    except ValueError as e:
        raise ApiError(f"asalbanooshop.com returned a non-JSON response for {route} (HTTP {r.status_code}).") from e
    total = r.headers.get("X-WP-Total")
    return data, int(total) if total and total.isdigit() else None


async def ajax(action: str, params: dict[str, Any]) -> str:
    """GET /wp-admin/admin-ajax.php?action=<action> and return the body text."""
    r = await _send(
        "GET",
        f"{BASE}/wp-admin/admin-ajax.php",
        params={"action": action, **params},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    return r.content.decode("utf-8", "replace")


async def get_page(path: str, params: dict[str, Any] | None = None) -> tuple[str, str]:
    """GET a site page; returns (final URL after redirects, HTML)."""
    r = await _send("GET", f"{BASE}{path}", params=params, headers=PAGE_HEADERS)
    # Cached pages come without a charset header; they are always UTF-8.
    return str(r.url), r.content.decode("utf-8", "replace")


async def _send(method: str, url: str, **kwargs: Any) -> httpx.Response:
    host = httpx.URL(BASE).host
    retries = solved = 0
    browsed = False
    while True:
        client, limit = _get_client()
        wait = None
        try:
            async with limit:
                await asyncio.sleep(random.uniform(*JITTER))
                r = await client.request(method, url, **kwargs)
        except httpx.TimeoutException as e:
            err = ApiError(f"{host} did not answer in time. Try again in a moment.")
            err.__cause__ = e
        except httpx.TransportError as e:
            # The server sometimes closes a keep-alive connection; a retry works.
            if isinstance(e, httpx.ConnectError | httpx.ProxyError):
                _next_proxy(client)
            err = ApiError(
                f"Could not reach {host} ({type(e).__name__}). Check the internet connection, or set ASALBANOO_MCP_PROXY."
            )
            err.__cause__ = e
        else:
            if (r.status_code == 429 or r.status_code >= 500) and not _is_challenge(r):
                err = ApiError(_status_message(r), r.status_code)
                wait = _retry_after(r)
            else:
                # HTTP 418 = bot challenge: a JS page that sets the _dgjsc cookie (valid about 2 h) and reloads.
                m = CHALLENGE.search(r.text) if r.status_code == 418 else None
                if m and solved < 2:
                    solved += 1
                    client.cookies.set("_dgjsc", m.group(1), domain=host, path="/")
                    continue
                if _is_challenge(r) and not browsed:
                    browsed = True
                    _next_proxy(client)
                    await _clear_challenge(_get_client()[0])
                    continue  # one retry; a second block is final
                if _is_challenge(r):
                    _next_proxy(client)
                if r.status_code >= 400:
                    raise ApiError(_status_message(r), r.status_code)
                return r
        if retries == MAX_RETRIES:
            raise err
        wait = wait if wait is not None else RETRY_DELAY * 2**retries * random.uniform(1, 1.5)
        retries += 1
        await asyncio.sleep(min(wait, MAX_RETRY_WAIT))


def _retry_after(r: httpx.Response) -> float | None:
    """Seconds from a numeric Retry-After on a 429/503, else None (HTTP-date form is ignored)."""
    v = r.headers.get("retry-after", "")
    return float(v) if r.status_code in (429, 503) and v.replace(".", "", 1).isdigit() else None


async def _browser_cookies(proxy: str | None) -> list[dict[str, Any]]:
    """Open the home page in headless patchright, wait for the challenge to clear, return the cookies."""
    try:
        from patchright.async_api import async_playwright
    except ImportError as e:
        raise ApiError(
            "asalbanooshop.com served a bot-check page. Install the browser extra "
            "(`pip install asalbanoo-mcp[browser]`, or `uvx --with patchright==1.63.0 asalbanoo-mcp`) "
            "and run `patchright install chromium`.",
            403,
        ) from e
    u = httpx.URL(proxy) if proxy else None
    opts = u and {"server": f"{u.scheme}://{u.host}:{u.port}", "username": u.username, "password": u.password}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, proxy=opts)
        try:
            page = await browser.new_page()
            await page.goto(BASE, wait_until="domcontentloaded", timeout=30_000)
            await page.wait_for_function(
                "!/just a moment|access denied|attention required|arvancloud/i.test(document.title)", timeout=30_000
            )
            return await browser.contexts[0].cookies()
        finally:
            await browser.close()


async def _clear_challenge(client: httpx.AsyncClient) -> None:
    """Rung 2: let a real browser pass the bot check once and share its cookies with the httpx jar."""
    global _browser_lock, _cleared
    _browser_lock = _browser_lock or asyncio.Lock()
    async with _browser_lock:  # one browser at a time; callers that waited reuse the cookies just fetched
        if _cleared and _cleared[0] is client and time.monotonic() - _cleared[1] < 30:
            return
        proxies = _proxies()
        try:
            cookies = await _browser_cookies(proxies[_proxy_index % len(proxies)] if proxies else None)
        except ApiError:
            raise
        except Exception as e:
            raise ApiError(
                f"asalbanooshop.com bot check was not cleared by the browser ({type(e).__name__}).", 403
            ) from e
        for c in cookies:
            client.cookies.set(c["name"], c["value"], domain=c["domain"], path=c["path"])
        _cleared = (client, time.monotonic())


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
