import pytest

pytestmark = [pytest.mark.anyio, pytest.mark.live]


async def call(client, name, args):
    result = await client.call_tool(name, args)
    assert not result.is_error, result.content[0].text
    return result.structured_content


async def test_ab_product(client):
    data = await call(client, "ab_product", {"product_id": 756311})
    assert data["brand"] and data["final_price"] > 0 and data["facts"]
    assert len(data["variants"]) >= 2 and all(v["final_price"] > 0 and v["options"] for v in data["variants"])


async def test_ab_reviews(client):
    data = await call(client, "ab_reviews", {"product_id": 6963})
    assert data["count"] >= 5 and 1 <= data["average"] <= 5
    assert all(r["rating"] is None or 1 <= r["rating"] <= 5 for r in data["reviews"])
    assert any(r["replies"] for r in data["reviews"])
