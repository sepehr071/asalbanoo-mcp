"""One product: details with variants, stock and price; customer reviews with the shop's answers."""

from __future__ import annotations

import html
import json
import re
from typing import Annotated, Any

from pydantic import Field

from .catalog import _first, _text, price_info
from .http import ApiError, ajax, get_page
from .registry import tool

ProductId = Annotated[
    int, Field(ge=1, le=100_000_000, description="Asal Banoo product id from ab_search / ab_browse, e.g. 6963.")
]


@tool("Product details")
async def ab_product(product_id: ProductId) -> dict[str, Any]:
    """Get one product's record: price and discount (Toman), stock (with the exact count when low),
    every variant (size/color) with its own price and stock, brand, categories, rating and key facts
    (volume, expiry, skin/hair type, origin).

    Use after ab_search / ab_browse when the user picks a product. Customer reviews: ab_reviews.
    """
    # Woodmart's quick view: 10 KB instead of the 170 KB product page, same price and stock markup.
    doc = await ajax("woodmart_quick_view", {"id": product_id})
    classes = _first(r'<div id="product-\d+" class="([^"]*)"', doc)
    if classes is None:
        raise ApiError(f"No product {product_id} on asalbanooshop.com. Get ids from ab_search or ab_browse.")
    rating = _first(r'<strong class="rating">([\d.]+)</strong>', doc)
    stock = _first(r'<p class="stock[^"]*">([^<]*)</p>', doc)
    # A hidden quantity box means one per order (last item in stock).
    max_qty = (
        "1" if re.search(r'type="hidden"[^>]*name="quantity"', doc) else _first(r'max="(\d+)"\s+name="quantity"', doc)
    )
    variants = _variants(doc)
    prices = price_info(_first(r'<p class="price">(.*?)</p>', doc) or "")
    if variants:
        # A range has no <del>: take the badge's "up to" discount and the cheapest variant's regular price.
        cheapest = min((v for v in variants if v["final_price"]), key=lambda v: v["final_price"], default=None)
        prices["discount_pct"] = max(v["discount_pct"] for v in variants)
        if cheapest:
            prices["price"] = cheapest["price"] or prices["price"]
        max_qty = None  # per variant
    return {
        "id": product_id,
        "title": _text(_first(r'<h1[^>]*class="product_title[^"]*"[^>]*>(.*?)</h1>', doc)),
        "brand": _text(_first(r"برند:</span>(.*?)</div>", doc)) or None,
        **prices,
        "in_stock": " instock " in f" {classes} ",
        "stock_status": stock.strip() if stock else None,
        # The quantity box's max: stock count or a per-order cap. None for variable products (per variant).
        "max_qty": int(max_qty) if max_qty else None,
        "on_sale": " sale " in f" {classes} ",
        "rating": float(rating) if rating else None,
        "review_count": int(_first(r'class="count">(\d+)<', doc) or 0),
        "categories": [_text(c) for c in re.findall(r'/product-category/[^"]*" rel="tag">(.*?)</a>', doc)],
        "facts": _facts(_first(r'short-description">(.*?)</div>\s*(?:<p class="stock|<form|<div)', doc) or ""),
        **({"variants": variants} if variants else {}),
        "url": _first(r'<a href="([^"]+)" class="view-details-btn"', doc),
    }


@tool("Product reviews")
async def ab_reviews(
    product_id: ProductId,
    limit: Annotated[int, Field(ge=1, le=100, description="Max reviews to return, newest first.")] = 20,
) -> dict[str, Any]:
    """Read customers' reviews and questions about a product (1-5 stars, newest first) with the shop's answers.

    Use as a quality check before recommending a product, or to see the shop's skin/hair advice
    (staff often answer questions with a recommended product or category). rating is null for
    a question without stars; verified_buyer marks a confirmed purchase. Dates are Jalali (1405-07-13).
    """
    try:
        _, doc = await get_page("/", {"post_type": "product", "p": product_id})
    except ApiError as e:
        if "404" in str(e):
            raise ApiError(f"No product {product_id} on asalbanooshop.com. Get ids from ab_search or ab_browse.") from e
        raise
    product = next((x for x in _json_ld(doc) if x.get("@type") == "Product"), None)
    if product is None:
        raise ApiError(f"No product {product_id} on asalbanooshop.com. Get ids from ab_search or ab_browse.")
    section = _first(r'<div id="reviews"(.*?)<div id="review_form_wrapper"', doc) or ""
    reviews: list[dict[str, Any]] = []
    # Each <li> is a review (depth-1) or a reply (depth-2+). Its class also holds the customer's
    # mobile number (comment-author-09...): never read the class beyond the depth.
    for depth, body in re.findall(
        r'<li class="(?:review|comment)\b[^"]*\bdepth-(\d+)"[^>]*>(.*?)(?=<li class="(?:review|comment)\b|</ol>|$)',
        section,
        re.S,
    ):
        item = {
            "author": _text(_first(r'woocommerce-review__author">(.*?)</strong>', body)),
            "date": (_first(r'<time[^>]*datetime="([^"]+)"', body) or "")[:10] or None,
            "text": _text(_first(r'<div class="description">(.*?)</div>', body)),
        }
        if depth == "1":
            stars = _first(r'<strong class="rating">(\d)</strong>', body)
            reviews.append(
                {
                    **item,
                    "rating": int(stars) if stars else None,
                    "verified_buyer": "wcpb-badge" in body,
                    "replies": [],
                }
            )
        elif reviews:
            reviews[-1]["replies"].append(item)
    agg = product.get("aggregateRating") or {}
    rated = [r["rating"] for r in reviews if r["rating"]]
    return {
        "title": product.get("name"),
        "count": len(reviews),
        "average": float(agg["ratingValue"]) if agg.get("ratingValue") else None,
        "star_counts": {str(s): rated.count(s) for s in range(5, 0, -1)},
        "reviews": reviews[:limit],
    }


def _variants(doc: str) -> list[dict[str, Any]]:
    """Variants of a variable product from data-product_variations (Toman), with readable option names."""
    raw = _first(r'data-product_variations="([^"]*)"', doc)
    if not raw or raw == "false":
        return []
    names = {k: _text(v) for k, v in re.findall(r'<label for="([^"]+)">(.*?)</label>', doc, re.S)}
    labels: dict[str, dict[str, str]] = {}
    for attr, options in re.findall(r'<select[^>]*name="attribute_([^"]+)"[^>]*>(.*?)</select>', doc, re.S):
        labels[attr] = {v: _text(t) for v, t in re.findall(r'<option value="([^"]+)"[^>]*>(.*?)</option>', options)}
    variants = []
    for v in json.loads(html.unescape(raw)):
        price, final = v.get("display_regular_price"), v.get("display_price")
        options = {}
        for key, value in (v.get("attributes") or {}).items():
            attr = key.removeprefix("attribute_")
            options[names.get(attr, attr)] = labels.get(attr, {}).get(value, value) or "any"
        variants.append(
            {
                "variation_id": v.get("variation_id"),
                "options": options,
                "final_price": final,
                "price": price,
                "discount_pct": round(100 * (price - final) / price) if price and final and price > final else 0,
                "in_stock": bool(v.get("is_in_stock")),
                "stock_status": _text(v.get("availability_html")) or None,
                "max_qty": v.get("max_qty") or None,
                "barcode": _first(r"(\d{8,14})", v.get("barcode_field") or ""),
            }
        )
    return variants


def _facts(fragment: str) -> list[str]:
    """Short-description bullets ('حجم: 250 میلی لیتر', 'کشور مبدا برند: فرانسه') as plain lines."""
    lines = [_text(x) for x in re.findall(r"<(?:li|p|h\d)[^>]*>(.*?)</(?:li|p|h\d)>", fragment, re.S)]
    return [x for x in lines if x][:20]


def _json_ld(doc: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for block in re.findall(r"<script[^>]*application/ld\+json[^>]*>(.*?)</script>", doc, re.S):
        try:
            data = json.loads(block)
        except ValueError:
            continue
        for x in data if isinstance(data, list) else [data]:
            if isinstance(x, dict):
                items += x.get("@graph") or [x]
    return [x for x in items if isinstance(x, dict)]
