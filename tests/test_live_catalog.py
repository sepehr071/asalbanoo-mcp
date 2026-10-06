import pytest

pytestmark = [pytest.mark.anyio, pytest.mark.live]


async def call(client, name, args):
    result = await client.call_tool(name, args)
    assert not result.is_error, result.content[0].text
    return result.structured_content


async def test_ab_search(client):
    data = await call(client, "ab_search", {"query": "شامپو", "sort": "cheapest", "limit": 10})
    assert data["total"] > 50 and len(data["products"]) == 10
    prices = [p["final_price"] for p in data["products"]]
    assert all(p["in_stock"] for p in data["products"]) and prices == sorted(prices) and prices[0] > 0


async def test_ab_find_cheapest(client):
    data = await call(client, "ab_find_cheapest", {"query": "ضد آفتاب", "limit": 10})
    prices = [o["final_price"] for o in data["offers"]]
    assert prices and prices == sorted(prices) and prices[0] > 0
    assert all("آفتاب" in o["title"] for o in data["offers"])


async def test_ab_browse(client):
    args = {"category": "hair-shampoo", "sort": "cheapest", "min_price": 1000000, "max_price": 3000000, "limit": 12}
    data = await call(client, "ab_browse", args)
    prices = [p["final_price"] for p in data["products"]]
    assert prices and prices == sorted(prices) and all(1000000 <= p <= 3000000 for p in prices)
    assert data["title"] and data["total"] >= len(prices)


async def test_ab_browse_brand_in_category(client):
    data = await call(client, "ab_browse", {"brand": "candid", "category": "hair-shampoo", "in_stock_only": False})
    assert data["products"] and all("کاندید" in p["title"] for p in data["products"])


async def test_ab_filters(client):
    data = await call(client, "ab_filters", {"category": "hair-shampoo"})
    bulk = next(g for g in data["filters"] if g["attribute"] == "bulk")
    assert bulk["options"] and all(o["count"] > 0 for o in bulk["options"])


async def test_ab_categories(client):
    data = await call(client, "ab_categories", {})
    assert len(data["categories"]) > 50 and any(c["slug"] == "hair-shampoo" for c in data["categories"])


async def test_ab_brands(client):
    data = await call(client, "ab_brands", {"query": "graph"})
    assert data["brands"][0]["slug"] == "graph" and data["brands"][0]["count"] > 10


async def test_ab_deals(client):
    data = await call(client, "ab_deals", {"limit": 10})
    pcts = [d["discount_pct"] for d in data["deals"]]
    assert pcts and pcts == sorted(pcts, reverse=True) and all(p > 0 for p in pcts)
    assert all(d["in_stock"] for d in data["deals"])


async def test_ab_search_sold_out_brand(client):
    data = await call(client, "ab_search", {"query": "cerave"})
    assert data["total"] > 0 or data["out_of_stock_matches"] > 0  # all of CeraVe was sold out in 2026-10
