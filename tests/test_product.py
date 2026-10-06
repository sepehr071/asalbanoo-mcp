import json

import pytest
from conftest import fixture

pytestmark = pytest.mark.anyio


async def test_ab_product_simple(client, api):
    api["woodmart_quick_view"] = fixture("quick_view_6963.html")
    out = (await client.call_tool("ab_product", {"product_id": 6963})).structured_content
    assert out == {
        "id": 6963,
        "title": "کرم کنترل کننده چربی Pure System استادرم",
        "brand": "استادرم",
        "final_price": 10900000,
        "price": 10900000,
        "discount_pct": 0,
        "in_stock": True,
        "stock_status": "فقط 2 عدد در انبار موجود است",
        "max_qty": 2,
        "on_sale": False,
        "rating": 4.09,
        "review_count": 11,
        "categories": ["کنترل کننده چربی صورت", "محصولات پوستی"],
        "facts": [
            "خصوصیات:",
            "کنترل ترشح چربی",
            "جمع کننده منافذ",
            "یکدست کننده پوست",
            "موثر در کاهش جوش ها",
            "قابل استفاده به عنوان پرایمر",
            "حجم: 50 میلی لیتر",
            "تاریخ انقضا: 12 ماه پس از باز شدن درب محصول",
            "مناسب برای: پوست های مختلط و چرب",
            "کشور مبدا برند: فرانسه",
        ],
        "url": "https://asalbanooshop.com/product/esthederm-puresystempurecontrolcare/",
    }


async def test_ab_product_variants(client, api):
    api["woodmart_quick_view"] = fixture("quick_view_756311.html")
    out = (await client.call_tool("ab_product", {"product_id": 756311})).structured_content
    assert (out["final_price"], out["max_price"], out["max_qty"], out["in_stock"]) == (4700000, 6900000, None, True)
    assert out["variants"] == [
        {
            "variation_id": 756319,
            "options": {"حجم": "250 میلی لیتر"},
            "final_price": 4700000,
            "price": 4700000,
            "discount_pct": 0,
            "in_stock": True,
            "stock_status": "موجود",
            "max_qty": 4,
            "barcode": "8033286041544",
        },
        {
            "variation_id": 756320,
            "options": {"حجم": "1000 میلی لیتر"},
            "final_price": 6900000,
            "price": 6900000,
            "discount_pct": 0,
            "in_stock": True,
            "stock_status": "موجود",
            "max_qty": 5,
            "barcode": "8033286041537",
        },
    ]


async def test_ab_product_discount_and_out_of_stock(client, api):
    api["woodmart_quick_view"] = fixture("quick_view_641215.html")
    out = (await client.call_tool("ab_product", {"product_id": 641215})).structured_content
    assert (out["final_price"], out["price"], out["discount_pct"], out["on_sale"]) == (1692000, 1880000, 10, True)
    assert (out["rating"], out["review_count"], out["max_qty"]) == (3.0, 2, 16)
    api["woodmart_quick_view"] = fixture("quick_view_74450.html")
    out = (await client.call_tool("ab_product", {"product_id": 74450})).structured_content
    assert (out["in_stock"], out["stock_status"], out["final_price"]) == (False, "ناموجود", 79800)
    assert out["rating"] is None and out["review_count"] == 0 and "variants" not in out


async def test_ab_product_variable_discount(client, api):
    api["woodmart_quick_view"] = fixture("quick_view_738159.html")
    out = (await client.call_tool("ab_product", {"product_id": 738159})).structured_content
    assert (out["final_price"], out["price"], out["discount_pct"], out["max_price"]) == (960000, 2400000, 60, 5670000)
    assert out["on_sale"] and out["max_qty"] is None
    assert sorted(v["discount_pct"] for v in out["variants"]) == [30, 60]


async def test_ab_product_one_per_order(client, api):
    api["woodmart_quick_view"] = fixture("quick_view_464977.html")
    out = (await client.call_tool("ab_product", {"product_id": 464977})).structured_content
    assert (out["final_price"], out["max_qty"], out["in_stock"]) == (115000, 1, True)


async def test_ab_product_unknown_id(client, api):
    api["woodmart_quick_view"] = '<div class="mfp-with-anim wd-popup popup-quick-view"></div>'
    result = await client.call_tool("ab_product", {"product_id": 99999999})
    assert result.is_error and "ab_search" in result.content[0].text


async def test_ab_reviews(client, api):
    api["/"] = fixture("product_6963.html")
    out = (await client.call_tool("ab_reviews", {"product_id": 6963, "limit": 2})).structured_content
    assert out["title"] == "کرم کنترل کننده چربی Pure System استادرم"
    assert (out["count"], out["average"]) == (4, 4.09)
    assert out["star_counts"] == {"5": 2, "4": 2, "3": 0, "2": 0, "1": 0}
    first = out["reviews"][0]
    assert (first["author"], first["rating"], first["verified_buyer"], first["date"]) == (
        "آزاده حسین پور",
        4,
        True,
        "1405-07-13",
    )
    assert first["text"].startswith("خوبه اما مثل") and len(out["reviews"]) == 2
    assert first["replies"] == [
        {"author": "مشاور پوست و مو عسل بانو", "date": "1405-07-13", "text": "سلام وقت بخیر، با تشکر از نظرتون🙏🏼🌺"}
    ]
    assert "0900" not in json.dumps(out)  # reviewer classes hold mobile numbers: never leaked
    assert api.params() == {"post_type": "product", "p": "6963"}


async def test_ab_reviews_unknown_id(client, api):
    result = await client.call_tool("ab_reviews", {"product_id": 99999999})
    assert result.is_error and "No product 99999999" in result.content[0].text
