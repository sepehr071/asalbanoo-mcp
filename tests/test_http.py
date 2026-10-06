import httpx
import pytest
from conftest import fixture

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


async def test_dropped_connection_is_retried_once(client, api):
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
    assert len(api.calls) == 2


async def test_timeout_is_not_retried(client, api):
    def slow(request):
        raise httpx.ReadTimeout("timed out", request=request)

    api["woodmart_quick_view"] = slow
    result = await client.call_tool("ab_product", {"product_id": 6963})
    assert result.is_error and "did not answer in time" in result.content[0].text and len(api.calls) == 1


@pytest.mark.parametrize(
    ("status", "text"),
    [(404, "HTTP 404"), (429, "rate limiting"), (500, "server error (HTTP 500)"), (403, "blocked")],
)
async def test_http_errors_are_actionable(client, api, status, text):
    api["woodmart_quick_view"] = lambda r: httpx.Response(status)
    result = await client.call_tool("ab_product", {"product_id": 6963})
    assert result.is_error and text in result.content[0].text


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
    assert "Chrome" in sent.headers["User-Agent"] and "python" not in sent.headers["User-Agent"].lower()
