import asyncio
import sys

import httpx
import pytest
from conftest import fixture

from asalbanoo_mcp import http

pytestmark = pytest.mark.anyio

CHALLENGE = '<html><script>const challenge = "_dgjsc=0123456789abcdef0123456789abcdef:20261006020000";</script></html>'


async def test_all_tools_are_read_only(client):
    tools = (await client.list_tools()).tools
    assert len(tools) == 12
    for t in tools:
        assert t.name.startswith("ab_"), t.name
        assert t.annotations.read_only_hint is True and t.annotations.destructive_hint is False, t.name
        assert t.description and t.title, t.name


async def test_bot_challenge_is_solved(client, api):
    def guarded(request):
        if "_dgjsc=0123456789abcdef0123456789abcdef:20261006020000" not in request.headers.get("cookie", ""):
            return httpx.Response(418, text=CHALLENGE)
        return httpx.Response(200, content=fixture("quick_view_6963.html").encode())

    api["woodmart_quick_view"] = guarded
    result = await client.call_tool("ab_product", {"product_id": 6963})
    assert not result.is_error and len(api.calls) == 2
    await client.call_tool("ab_product", {"product_id": 6963})
    assert len(api.calls) == 3  # the cookie is kept for later requests


async def test_challenge_that_never_clears(client, api):
    api["woodmart_quick_view"] = lambda r: httpx.Response(418, text=CHALLENGE)
    result = await client.call_tool("ab_product", {"product_id": 6963})
    assert result.is_error and "bot challenge (HTTP 418)" in result.content[0].text and len(api.calls) == 3


async def test_dropped_connection_is_retried(client, api):
    attempts = []

    def flaky(request):
        attempts.append(request)
        if len(attempts) == 1:
            raise httpx.RemoteProtocolError("Server disconnected without sending a response.", request=request)
        return httpx.Response(200, content=fixture("quick_view_6963.html").encode())

    api["woodmart_quick_view"] = flaky
    result = await client.call_tool("ab_product", {"product_id": 6963})
    assert not result.is_error and len(attempts) == 2


async def test_network_error_after_retry(client, api):
    def down(request):
        raise httpx.ConnectError("[SSL: UNEXPECTED_EOF_WHILE_READING]", request=request)

    api["woodmart_quick_view"] = down
    result = await client.call_tool("ab_product", {"product_id": 6963})
    assert result.is_error and "Could not reach asalbanooshop.com (ConnectError)" in result.content[0].text
    assert len(api.calls) == 3


async def test_timeout_is_retried_twice(client, api):
    def slow(request):
        raise httpx.ReadTimeout("timed out", request=request)

    api["woodmart_quick_view"] = slow
    result = await client.call_tool("ab_product", {"product_id": 6963})
    assert result.is_error and "did not answer in time" in result.content[0].text and len(api.calls) == 3


@pytest.mark.parametrize(
    ("status", "text"),
    [(404, "HTTP 404"), (429, "rate limiting"), (500, "server error (HTTP 500)"), (403, "blocked")],
)
async def test_http_errors_are_actionable(client, api, status, text):
    api["woodmart_quick_view"] = lambda r: httpx.Response(status)
    result = await client.call_tool("ab_product", {"product_id": 6963})
    assert result.is_error and text in result.content[0].text


async def test_rate_limit_is_retried_once(client, api):
    answers = iter([429, 200])
    api["/wp-json/wp/v2/posts"] = lambda r: httpx.Response(next(answers), json=[])
    out = (await client.call_tool("ab_blog_posts", {})).structured_content
    assert out["posts"] == [] and len(api.calls) == 2


async def test_categories_and_brands_are_cached(client, api):
    api["/wp-json/wp/v2/product_cat"] = []
    api["/wp-json/wp/v2/pwb-brand"] = []
    for _ in range(2):
        await client.call_tool("ab_categories", {})
        await client.call_tool("ab_brands", {})
    assert len(api.calls) == 1 + 3


async def test_rest_error_message_is_passed_on(client, api):
    api["/wp-json/wp/v2/posts"] = lambda r: httpx.Response(
        400, json={"code": "rest_invalid_param", "message": "Invalid parameter(s): per_page"}
    )
    result = await client.call_tool("ab_blog_posts", {})
    assert result.is_error and "Invalid parameter(s): per_page" in result.content[0].text

    api["/wp-json/wp/v2/posts"] = lambda r: httpx.Response(200, text="<html>oops</html>")
    result = await client.call_tool("ab_blog_posts", {})
    assert result.is_error and "non-JSON" in result.content[0].text


async def test_request_format(client, api):
    api["woodmart_quick_view"] = fixture("quick_view_6963.html")
    await client.call_tool("ab_product", {"product_id": 6963})
    sent = api.calls[0]
    assert sent.url.path == "/wp-admin/admin-ajax.php" and api.params() == {
        "action": "woodmart_quick_view",
        "id": "6963",
    }
    # The User-Agent comes from the impersonated Chrome profile, not from the client.
    assert (
        sent.headers["Referer"] == "https://asalbanooshop.com/" and sent.headers["X-Requested-With"] == "XMLHttpRequest"
    )
    assert sent.headers["Accept-Language"].startswith("fa-IR") and sent.headers["sec-fetch-mode"] == "cors"


async def test_page_requests_look_like_navigation(client, api):
    api["/shop/"] = "<html></html>"
    await http.get_page("/shop/")
    assert api.calls[0].headers["sec-fetch-mode"] == "navigate" and "X-Requested-With" not in api.calls[0].headers


def test_is_challenge():
    html = {"content-type": "text/html"}
    assert http._is_challenge(httpx.Response(403, text="<html>Just a moment...</html>", headers=html))
    assert http._is_challenge(httpx.Response(503, text="<!doctype html><title>ArvanCloud</title>"))
    assert not http._is_challenge(httpx.Response(403, text="<html>Access Denied</html>", headers=html))
    assert not http._is_challenge(httpx.Response(403, json={"code": "rest_forbidden"}))
    assert not http._is_challenge(httpx.Response(200, text="<html></html>", headers=html))


async def test_proxy_list_rotates_on_connect_error(monkeypatch, api):
    monkeypatch.setenv("ASALBANOO_MCP_PROXY", "http://p1:1, http://p2:2")
    assert http._proxies() == ["http://p1:1", "http://p2:2"]

    def boom(request):
        raise httpx.ConnectError("down", request=request)

    api["/wp-json/wp/v2/posts"] = boom
    http._get_client()
    with pytest.raises(http.ApiError):
        await http.rest("wp/v2/posts")
    assert http._proxy_index >= 1


async def test_stale_client_does_not_rotate(monkeypatch, api):
    monkeypatch.setenv("ASALBANOO_MCP_PROXY", "http://p1:1, http://p2:2")
    old, _ = http._get_client()
    http._next_proxy(old)
    new, _ = http._get_client()
    assert http._proxy_index == 1 and new is not old
    http._next_proxy(old)  # a late failure on the retired client must not skip the proxy now in use
    assert http._proxy_index == 1 and http._client is new


async def test_challenge_cleared_by_browser_once(monkeypatch, api):
    runs = []

    async def fake_browser(proxy):
        runs.append(proxy)
        await asyncio.sleep(0.01)
        return [{"name": "clearance", "value": "ok", "domain": "asalbanooshop.com", "path": "/"}]

    monkeypatch.setattr(http, "_browser_cookies", fake_browser)

    def guarded(request):
        if request.headers.get("cookie", "").find("clearance=ok") < 0:
            return httpx.Response(403, text="<html>Just a moment</html>", headers={"content-type": "text/html"})
        return httpx.Response(200, json=[])

    api["/wp-json/wp/v2/posts"] = guarded
    await asyncio.gather(http.rest("wp/v2/posts", {"a": 1}), http.rest("wp/v2/posts", {"a": 2}))
    assert len(runs) == 1  # the second caller reused the cookies the first one fetched

    api["/wp-json/wp/v2/pages"] = lambda r: httpx.Response(403, text="<html>Just a moment</html>")
    with pytest.raises(http.ApiError) as e:  # still blocked after the one retry: final
        await http.rest("wp/v2/pages")
    assert e.value.status == 403 and sum(r.url.path.endswith("/pages") for r in api.calls) == 2


async def test_503_challenge_goes_to_browser_not_retry(monkeypatch, api):
    runs = []

    async def fake_browser(proxy):
        runs.append(proxy)
        return []

    monkeypatch.setattr(http, "_browser_cookies", fake_browser)
    api["/wp-json/wp/v2/posts"] = lambda r: httpx.Response(
        503, text="<html>Just a moment</html>", headers={"content-type": "text/html"}
    )
    with pytest.raises(http.ApiError):
        await http.rest("wp/v2/posts")
    assert len(runs) == 1 and len(api.calls) == 2


async def test_bare_403_does_not_launch_a_browser(monkeypatch, api):
    monkeypatch.setitem(sys.modules, "patchright.async_api", None)
    api["/wp-json/wp/v2/users"] = lambda r: httpx.Response(403, text="<html>Access Denied</html>")
    with pytest.raises(http.ApiError, match="HTTP 403") as e:
        await http.rest("wp/v2/users")
    assert len(api.calls) == 1 and e.value.status == 403


async def test_challenge_without_patchright(monkeypatch, api):
    monkeypatch.setitem(sys.modules, "patchright.async_api", None)  # makes the import fail
    api["/wp-json/wp/v2/posts"] = lambda r: httpx.Response(403, text="<html>Just a moment</html>")
    with pytest.raises(http.ApiError, match=r"asalbanoo-mcp\[browser\].*patchright install chromium"):
        await http.rest("wp/v2/posts")


async def test_retry_after_is_honoured_and_capped(monkeypatch, api):
    waits = []

    async def fake_sleep(s):
        waits.append(s)

    monkeypatch.setattr(http.asyncio, "sleep", fake_sleep)
    hits = []

    def limited(request):
        hits.append(1)
        if len(hits) == 1:
            return httpx.Response(429, headers={"Retry-After": "3"})
        if len(hits) == 2:
            return httpx.Response(503, headers={"Retry-After": "999"})
        return httpx.Response(200, json=[])

    api["/wp-json/wp/v2/posts"] = limited
    await http.rest("wp/v2/posts")
    assert 3 in waits and http.MAX_RETRY_WAIT in waits
