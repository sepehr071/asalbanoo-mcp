import pytest
from conftest import fixture

pytestmark = pytest.mark.anyio


async def test_ab_shop_info_faq(client, api):
    api["/wp-json/wp/v2/pages"] = fixture("faq.json")
    out = (await client.call_tool("ab_shop_info", {"topic": "faq"})).structured_content
    assert out["title"] == "سوالات متداول" and out["url"] == "https://asalbanooshop.com/faq/"
    assert [f["question"] for f in out["faq"]] == [
        "از چه طریقی میتونید مشاوره بگیرید؟",
        "آیا محصولات فروشگاه عسل بانو اصل هستند؟",
        "محصولات چند روزه به دست مشتری ها میرسند؟",
    ]
    delivery = out["faq"][2]["answer"]
    assert "پست پیشتاز" in delivery and "[" not in delivery and "<" not in delivery
    assert api.params()["slug"] == "faq"


async def test_ab_shop_info_text_page(client, api):
    api["/wp-json/wp/v2/pages"] = fixture("contact.json")
    out = (await client.call_tool("ab_shop_info", {"topic": "contact"})).structured_content
    assert "faq" not in out and "بندرعباس" in out["text"] and "vc_" not in out["text"]
    assert api.params()["slug"] == "contact-us"
    api["/wp-json/wp/v2/pages"] = []
    result = await client.call_tool("ab_shop_info", {"topic": "terms"})
    assert result.is_error and "not found" in result.content[0].text


async def test_ab_blog_posts(client, api):
    api["/wp-json/wp/v2/posts"] = fixture("posts.json")
    out = (await client.call_tool("ab_blog_posts", {"query": "ضد آفتاب", "limit": 3})).structured_content
    assert out["posts"][0] == {
        "id": 791485,
        "title": "آبرسان ویشی بهتره یا کلینیک؟ مقایسه تخصصی براساس نوع پوست",
        "date": "2026-10-03",
        "summary": out["posts"][0]["summary"],
        "url": "https://asalbanooshop.com/vichy-vs-clinique-moisturizer/",
    }
    assert out["posts"][0]["summary"].startswith("اگر پوستتان") and "vc_" not in out["posts"][0]["summary"]
    assert api.params() == {"per_page": "3", "page": "1", "_fields": "id,date,link,title,excerpt", "search": "ضد آفتاب"}


async def test_ab_blog_post(client, api):
    api["/wp-json/wp/v2/posts/791485"] = fixture("post_791485.json")
    out = (await client.call_tool("ab_blog_post", {"post_id": 791485, "max_chars": 500})).structured_content
    assert out["title"] == "آبرسان ویشی بهتره یا کلینیک؟ مقایسه تخصصی براساس نوع پوست"
    assert len(out["text"]) == 500 and out["truncated"] and "vc_" not in out["text"]
    assert out["product_links"] == [
        "https://asalbanooshop.com/product/vichy-mineral-89-fortifying-and-plumping-daily-booster-50ml/"
    ]
    assert out["category_slugs"] == ["moisturizing"]


async def test_ab_blog_post_unknown_id(client, api):
    result = await client.call_tool("ab_blog_post", {"post_id": 1})
    assert result.is_error and "No blog post 1" in result.content[0].text
