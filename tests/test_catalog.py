import httpx
import pytest
from conftest import fixture

pytestmark = pytest.mark.anyio


async def test_ab_search(client, api):
    api["/"] = fixture("search.html")
    result = await client.call_tool("ab_search", {"query": "شامپو", "sort": "cheapest", "limit": 20})
    out = result.structured_content
    assert out["total"] == 112 and out["last_page"] == 6 and len(out["products"]) == 6
    assert out["products"][3] == {
        "id": 22190,
        "title": "شامپو ضد شوره خشک و ملایم کاندید",
        "final_price": 503820,
        "price": 559800,
        "discount_pct": 10,
        "in_stock": True,
        "rating": 5.0,
        "variable": False,
        "url": "https://asalbanooshop.com/product/candid-anti-dandruff-shampoo/",
    }
    assert api.params() == {
        "s": "شامپو",
        "post_type": "product",
        "orderby": "price",
        "stock_status": "instock",
        "per_page": "20",
    }


async def test_ab_search_page_and_filters(client, api):
    api["/page/3/"] = fixture("search.html")
    args = {"query": "شامپو", "in_stock_only": False, "min_price": 100000, "max_price": 500000, "page": 3}
    await client.call_tool("ab_search", args)
    sent = api.params()
    assert "stock_status" not in sent and "orderby" not in sent
    assert (sent["min_price"], sent["max_price"], sent["per_page"]) == ("100000", "500000", "15")


async def test_ab_search_out_of_stock_card(client, api):
    api["/"] = fixture("search.html").replace("product-grid-item product", "product-grid-item outofstock product", 1)
    out = (await client.call_tool("ab_search", {"query": "شامپو", "in_stock_only": False})).structured_content
    assert [p["in_stock"] for p in out["products"]][:2] == [False, True]


async def test_ab_search_all_sold_out(client, api):
    def handler(request):
        stocked = "stock_status" in request.url.params
        body = '<p class="woocommerce-info">nothing</p>' if stocked else fixture("search.html")
        return httpx.Response(200, content=body.encode())

    api["/"] = handler
    out = (await client.call_tool("ab_search", {"query": "cerave"})).structured_content
    assert (out["total"], out["products"], out["out_of_stock_matches"]) == (0, [], 112)
    assert "in_stock_only=false" in out["note"] and api.params()["per_page"] == "1"


async def test_ab_search_past_last_page(client, api):
    result = await client.call_tool("ab_search", {"query": "شامپو", "page": 9})
    assert result.is_error and "past the last page" in result.content[0].text


async def test_ab_search_validation(client, api):
    result = await client.call_tool("ab_search", {"query": "x"})
    assert result.is_error and not api.calls
    result = await client.call_tool("ab_search", {"query": "شامپو", "min_price": 5, "max_price": 1})
    assert result.is_error and "min_price" in result.content[0].text and not api.calls


async def test_ab_find_cheapest(client, api):
    api["/"] = fixture("search.html")
    out = (await client.call_tool("ab_find_cheapest", {"query": "شامپو ضد شوره"})).structured_content
    # the eyelid shampoo and other non-matching titles are dropped; cheapest first
    assert [(o["id"], o["final_price"]) for o in out["offers"]] == [(22190, 503820), (22183, 559800)]
    assert out["scanned"] == 6 and out["total_matches"] == 112 and out["complete"] is False
    sent = api.params()
    assert (sent["orderby"], sent["stock_status"], sent["per_page"]) == ("price", "instock", "150")
    out = (await client.call_tool("ab_find_cheapest", {"query": "شامپو", "limit": 2})).structured_content
    assert [o["final_price"] for o in out["offers"]] == [115000, 459800]


async def test_ab_browse(client, api):
    api["/product-category/hair-shampoo/page/2/"] = fixture("category.html")
    args = {
        "category": "hair-shampoo",
        "sort": "most_expensive",
        "on_sale_only": True,
        "filters": {"bulk": ["250-میلی-لیتر", "300ml"]},
        "page": 2,
        "limit": 10,
    }
    out = (await client.call_tool("ab_browse", args)).structured_content
    assert out["title"] == "شامپو shampoo" and out["total"] == 54 and out["last_page"] == 4
    assert [p["id"] for p in out["products"]] == [22200, 22195, 22190, 738980, 22183]
    assert api.params() == {
        "orderby": "price-desc",
        "stock_status": "instock,onsale",
        "filter_bulk": "250-میلی-لیتر,300ml",
        "query_type_bulk": "or",
        "per_page": "10",
    }


async def test_ab_browse_brand_category_and_shop(client, api):
    api["/brand/candid/"] = fixture("category.html")
    await client.call_tool("ab_browse", {"brand": "candid", "category": "hair-shampoo"})
    assert api.params()["product_cat"] == "hair-shampoo"
    api["/shop/"] = fixture("category.html")
    await client.call_tool("ab_browse", {"sort": "newest"})
    assert api.calls[-1].url.path == "/shop/" and api.params()["orderby"] == "date"
    result = await client.call_tool("ab_browse", {"brand": "../x"})
    assert result.is_error and len(api.calls) == 2


async def test_ab_browse_unknown_category(client, api):
    result = await client.call_tool("ab_browse", {"category": "nope-cat"})
    assert result.is_error and "HTTP 404" in result.content[0].text


async def test_ab_browse_variable_range(client, api):
    api["/shop/"] = fixture("deals.html")
    out = (await client.call_tool("ab_browse", {})).structured_content
    palette = next(p for p in out["products"] if p["id"] == 496343)
    assert (palette["final_price"], palette["max_price"], palette["discount_pct"]) == (1251000, 1390000, 10)
    assert palette["variable"] is True


async def test_ab_filters(client, api):
    api["/product-category/hair-shampoo/"] = fixture("category.html")
    out = (await client.call_tool("ab_filters", {"category": "hair-shampoo"})).structured_content
    assert [g["attribute"] for g in out["filters"]] == ["bulk", "hair", "gender"]
    bulk = out["filters"][0]
    assert bulk["group"] == "حجم"
    assert {"value": "250-میلی-لیتر", "name": "250 میلی لیتر", "count": 13} in bulk["options"]
    assert api.params() == {"stock_status": "instock"}


async def test_ab_categories(client, api):
    api["/wp-json/wp/v2/product_cat"] = fixture("categories.json")
    out = (await client.call_tool("ab_categories", {})).structured_content
    assert out["categories"][0] == {"id": 61, "name": "محصولات مو", "slug": "hair-products", "parent": 0, "count": 505}
    out = (await client.call_tool("ab_categories", {"query": "شامپو"})).structured_content
    assert out["categories"] == [{"id": 184, "name": "شامپو", "slug": "hair-shampoo", "parent": 61, "count": 180}]
    assert api.params()["per_page"] == "100"


async def test_ab_brands(client, api):
    brands = fixture("brands.json")

    def pages(request):
        return httpx.Response(200, json=brands if request.url.params["page"] == "1" else [])

    api["/wp-json/wp/v2/pwb-brand"] = pages
    out = (await client.call_tool("ab_brands", {"limit": 2})).structured_content
    assert out == {
        "total": 6,
        "brands": [
            {"slug": "graph", "name": "گراف", "count": 91},
            {"slug": "forever52", "name": "فور اور 52", "count": 71},
        ],
    }
    assert sorted(c.url.params["page"] for c in api.calls) == ["1", "2", "3"]
    out = (await client.call_tool("ab_brands", {"query": "ویتالیر"})).structured_content
    assert [b["slug"] for b in out["brands"]] == ["vitalayer"]


async def test_ab_deals(client, api):
    # one card made a 30% deal to check the ordering
    api["/shop/"] = "-30%".join(fixture("deals.html").rsplit("-10%", 1))  # last card: 7258
    out = (await client.call_tool("ab_deals", {"limit": 3})).structured_content
    assert out["count"] == 6
    assert [(d["id"], d["discount_pct"]) for d in out["deals"]] == [(7258, 30), (576314, 10), (428146, 10)]
    sent = api.params()
    assert (sent["stock_status"], sent["per_page"]) == ("instock,onsale", "300")
    api["/product-category/sunscreen/"] = fixture("deals.html")
    await client.call_tool("ab_deals", {"category": "sunscreen"})
    assert api.calls[-1].url.path == "/product-category/sunscreen/"
