import pytest

pytestmark = [pytest.mark.anyio, pytest.mark.live]


async def call(client, name, args):
    result = await client.call_tool(name, args)
    assert not result.is_error, result.content[0].text
    return result.structured_content


async def test_ab_shop_info(client):
    data = await call(client, "ab_shop_info", {"topic": "faq"})
    assert len(data["faq"]) >= 5 and any("پیشتاز" in f["answer"] for f in data["faq"])


async def test_ab_blog_posts(client):
    data = await call(client, "ab_blog_posts", {"query": "ضد آفتاب", "limit": 5})
    assert data["total"] > 10 and len(data["posts"]) == 5


async def test_ab_blog_post(client):
    posts = (await call(client, "ab_blog_posts", {"limit": 1}))["posts"]
    data = await call(client, "ab_blog_post", {"post_id": posts[0]["id"]})
    assert data["title"] and len(data["text"]) > 200 and "[vc_" not in data["text"]
