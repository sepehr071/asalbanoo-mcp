"""Finding products: search, cheapest offers, category / brand listings, filters, categories, brands, deals."""

from __future__ import annotations

import asyncio
import html
import re
from typing import Annotated, Any, Literal
from urllib.parse import unquote

from pydantic import Field

from .http import BASE, ApiError, get_page, rest
from .registry import tool

Query = Annotated[
    str,
    Field(
        min_length=2,
        max_length=100,
        description="Product name or keyword, Persian or English, e.g. 'شامپو ضد شوره' or 'la roche posay'.",
    ),
]
CategorySlug = Annotated[
    str | None,
    Field(
        pattern=r"^[a-z0-9-]{2,60}$",
        description="Category slug from ab_categories, e.g. 'hair-shampoo' or 'sunscreen'.",
    ),
]
BrandSlug = Annotated[
    str | None,
    Field(pattern=r"^[a-z0-9-]{2,60}$", description="Brand slug from ab_brands, e.g. 'graph' or 'la-roche-posay'."),
]
Sort = Annotated[
    Literal["default", "cheapest", "most_expensive", "newest", "popular", "top_rated"],
    Field(description="Order of the listing. 'default' puts in-stock items first (relevance for a search)."),
]
MinPrice = Annotated[int | None, Field(ge=0, description="Minimum current price in Toman, e.g. 1000000.")]
MaxPrice = Annotated[int | None, Field(ge=1, description="Maximum current price in Toman, e.g. 2000000.")]
InStockOnly = Annotated[bool, Field(description="Only items that can be ordered now.")]
Page = Annotated[int, Field(ge=1, le=200, description="Page number, from 1.")]
Limit = Annotated[int, Field(ge=1, le=60, description="Products per page.")]

SORTS = {
    "default": None,
    "cheapest": "price",
    "most_expensive": "price-desc",
    "newest": "date",
    "popular": "popularity",
    "top_rated": "rating",
}


@tool("Search products")
async def ab_search(
    query: Query,
    sort: Sort = "default",
    in_stock_only: InStockOnly = True,
    min_price: MinPrice = None,
    max_price: MaxPrice = None,
    page: Page = 1,
    limit: Limit = 15,
) -> dict[str, Any]:
    """Search Asal Banoo products by keyword: price, discount, stock and rating of each match.

    Use first for "price of X" / "do you have X". Matching is broad (title and description),
    so check titles. For the cheapest match use ab_find_cheapest; to list a whole category or
    brand use ab_browse; full details and variants (sizes/colors) of one product: ab_product.
    When nothing in stock matches, out_of_stock_matches counts the sold-out ones.
    """
    params = {"s": query.strip(), "post_type": "product"}
    found = await _listing("/", params, sort, in_stock_only, False, min_price, max_price, None, page, limit)
    if in_stock_only and not found["total"] and page == 1:
        # Nothing in stock: say whether the shop carries it at all (e.g. all of 'cerave' is sold out).
        sold_out = await _listing("/", params, sort, False, False, min_price, max_price, None, 1, 1)
        if sold_out["total"]:
            found["out_of_stock_matches"] = sold_out["total"]
            found["note"] = "Nothing in stock; retry with in_stock_only=false to see the sold-out matches."
    return found


@tool("Find cheapest product")
async def ab_find_cheapest(
    query: Query,
    match_all_words: Annotated[
        bool, Field(description="Keep only titles that contain every word of the query.")
    ] = True,
    scan: Annotated[
        int, Field(ge=20, le=300, description="How many in-stock search results to scan, cheapest first.")
    ] = 150,
    limit: Annotated[int, Field(ge=1, le=50, description="Max offers to return.")] = 15,
) -> dict[str, Any]:
    """Find the cheapest in-stock products for a keyword, one flat list sorted by current price (Toman).

    Use when the user wants the lowest price for X. The site's search also matches descriptions,
    so by default only titles containing every query word are kept. Variable products (several
    sizes/colors) are listed at their cheapest variant: check ab_product for the size you need.
    complete=false means more in-stock matches lie past `scanned`: raise scan.
    """
    params = {"s": query.strip(), "post_type": "product"}
    found = await _listing("/", params, "cheapest", True, False, None, None, None, 1, scan)
    words = _norm(query).split()
    offers = [
        p
        for p in found["products"]
        if p["final_price"] and (not match_all_words or all(w in _norm(p["title"]) for w in words))
    ]
    offers.sort(key=lambda p: p["final_price"])
    return {
        "scanned": len(found["products"]),
        "total_matches": found["total"],
        "complete": len(found["products"]) >= (found["total"] or 0),
        "offers": offers[:limit],
    }


@tool("Browse a category or brand")
async def ab_browse(
    category: CategorySlug = None,
    brand: BrandSlug = None,
    sort: Sort = "default",
    in_stock_only: InStockOnly = True,
    on_sale_only: Annotated[bool, Field(description="Only discounted items.")] = False,
    min_price: MinPrice = None,
    max_price: MaxPrice = None,
    filters: Annotated[
        dict[
            Annotated[str, Field(pattern=r"^[a-z0-9-]{2,30}$")],
            list[Annotated[str, Field(min_length=1, max_length=80)]],
        ]
        | None,
        Field(
            max_length=5,
            description="Attribute filters from ab_filters: attribute -> values (any of them matches), "
            "e.g. {'bulk': ['250-میلی-لیتر'], 'hair': ['چرب']}.",
        ),
    ] = None,
    page: Page = 1,
    limit: Limit = 24,
) -> dict[str, Any]:
    """List the products of a category or brand (or the whole shop) with sorting, price range, stock and attribute filters.

    Use for "cheapest shampoo for oily hair", "Graph brushes under 800,000 Toman", "newest
    sunscreens". Pass a category slug (ab_categories), a brand slug (ab_brands), both, or neither
    (whole shop). Attribute filters (volume, hair/skin type, gender, origin) come from ab_filters.
    Variable products show their cheapest variant as final_price and max_price as the top of the
    range. Details: ab_product; reviews: ab_reviews.
    """
    path = f"/product-category/{category}/" if category else f"/brand/{brand}/" if brand else "/shop/"
    params: dict[str, Any] = {}
    if category and brand:
        path, params = f"/brand/{brand}/", {"product_cat": category}
    return await _listing(path, params, sort, in_stock_only, on_sale_only, min_price, max_price, filters, page, limit)


@tool("Filters of a category or brand")
async def ab_filters(
    category: CategorySlug = None,
    brand: BrandSlug = None,
) -> dict[str, Any]:
    """List the attribute filters of a category or brand listing (volume, hair type, skin type, gender, origin...)
    with each value's product count.

    Use before ab_browse when the user wants a size or a type inside a category: pass
    {attribute: [value, ...]} as ab_browse's filters. Counts cover in-stock items.
    """
    path = f"/product-category/{category}/" if category else f"/brand/{brand}/" if brand else "/shop/"
    url, doc = await get_page(path, {"stock_status": "instock"})
    groups = []
    for name, body in re.findall(
        r'<div id="woocommerce_layered_nav-\d+"[^>]*><h5 class="widget-title">(.*?)</h5>(.*?)</ul>', doc, re.S
    ):
        options = [
            {"value": unquote(html.unescape(value)), "name": _text(label), "count": int(count)}
            for value, label, count in re.findall(
                r'filter_[a-z0-9-]+=([^&"]+)[^"]*"[^>]*>(.*?)</a>\s*<span class="count">\((\d+)\)', body, re.S
            )
        ]
        attr = _first(r"filter_([a-z0-9-]+)=", body)
        if attr and options:
            groups.append({"group": _text(name), "attribute": attr, "options": options})
    return {"title": _text(_first(r"<h1[^>]*>(.*?)</h1>", doc)) or None, "url": url, "filters": groups}


@tool("List categories")
async def ab_categories(
    query: Annotated[
        str | None,
        Field(min_length=2, description="Optional filter on the Persian name or slug, e.g. 'شامپو' or 'sun'."),
    ] = None,
) -> dict[str, Any]:
    """List Asal Banoo's product categories (about 70: skin, make-up, hair, perfume, kids) with slugs and counts.

    Use to get a category slug for ab_browse / ab_filters. parent is the id of the parent
    category (0 = top level); count includes out-of-stock products.
    """
    data, _ = await rest("wp/v2/product_cat", {"per_page": 100, "_fields": "id,name,slug,parent,count"})
    categories = [
        {"id": c["id"], "name": html.unescape(c["name"]), "slug": c["slug"], "parent": c["parent"], "count": c["count"]}
        for c in data
    ]
    if query:
        q = _norm(query)
        categories = [c for c in categories if q in _norm(c["name"]) or q in c["slug"]]
    return {"categories": sorted(categories, key=lambda c: -c["count"])}


@tool("List brands")
async def ab_brands(
    query: Annotated[
        str | None,
        Field(min_length=2, description="Optional filter on the Persian name or Latin slug, e.g. 'graph' or 'ویشی'."),
    ] = None,
    limit: Annotated[int, Field(ge=1, le=300, description="Max brands, biggest first.")] = 100,
) -> dict[str, Any]:
    """List the brands Asal Banoo sells (about 250) with their slugs and product counts, biggest first.

    Use to get the brand slug for ab_browse / ab_filters. Persian spellings vary; the Latin slug
    usually matches better ('vichy', 'cerave', 'la-roche-posay').
    """
    pages = await asyncio.gather(
        *(
            rest("wp/v2/pwb-brand", {"per_page": 100, "page": p, "_fields": "name,slug,count"})
            for p in (1, 2, 3)  # ponytail: 246 brands in 2026-10; add a page when it passes 300
        )
    )
    brands = [
        {"slug": b["slug"], "name": html.unescape(b["name"]), "count": b["count"]} for data, _ in pages for b in data
    ]
    if query:
        q = _norm(query)
        brands = [b for b in brands if q in _norm(b["name"]) or q.replace(" ", "-") in b["slug"]]
    brands.sort(key=lambda b: -b["count"])
    return {"total": len(brands), "brands": brands[:limit]}


@tool("Current deals")
async def ab_deals(
    category: CategorySlug = None,
    limit: Annotated[int, Field(ge=1, le=100, description="Max deals to return.")] = 30,
) -> dict[str, Any]:
    """List the discounted in-stock products right now, biggest discount first (the site's "تخفیفات" page).

    Use for "what's on sale" / "discounted sunscreens". Optionally limit to one category slug
    from ab_categories. Most discounts are 10%.
    """
    path = f"/product-category/{category}/" if category else "/shop/"
    found = await _listing(path, {}, "default", True, True, None, None, None, 1, 300)
    deals = sorted(found["products"], key=lambda p: (-p["discount_pct"], p["final_price"] or 0))
    return {"count": len(deals), "deals": deals[:limit]}


async def _listing(
    path: str,
    params: dict[str, Any],
    sort: str,
    in_stock_only: bool,
    on_sale_only: bool,
    min_price: int | None,
    max_price: int | None,
    filters: dict[str, list[str]] | None,
    page: int,
    limit: int,
) -> dict[str, Any]:
    """One page of a WooCommerce listing (search, category, brand, shop) as product cards."""
    if min_price is not None and max_price is not None and min_price > max_price:
        raise ApiError("min_price must be <= max_price.")
    q = dict(params)
    if SORTS[sort]:
        q["orderby"] = SORTS[sort]
    # Without instock, price sorting starts with cheap discontinued items.
    status = [s for s, on in (("instock", in_stock_only), ("onsale", on_sale_only)) if on]
    if status:
        q["stock_status"] = ",".join(status)
    if min_price is not None:
        q["min_price"] = min_price
    if max_price is not None:
        q["max_price"] = max_price
    for attr, values in (filters or {}).items():
        q[f"filter_{attr}"], q[f"query_type_{attr}"] = ",".join(values), "or"
    q["per_page"] = limit
    if page > 1:
        path = f"{path}page/{page}/"
    try:
        _, doc = await get_page(path, q)
    except ApiError as e:
        if page > 1 and "404" in str(e):
            raise ApiError(f"Page {page} is past the last page of this listing.") from e
        raise
    total = _first(r"woocommerce-result-count[^>]*>[^<]*?([\d,]+)\s*نتیجه", doc)
    products = _cards(doc)
    return {
        "title": _text(_first(r"<h1[^>]*>(.*?)</h1>", doc)) or None,
        "total": int(total.replace(",", "")) if total else len(products),
        "page": page,
        "last_page": max([int(n) for n in re.findall(r'class="page-numbers"[^>]*>(\d+)<', doc)] + [page]),
        "products": products,
    }


def _cards(doc: str) -> list[dict[str, Any]]:
    """Product cards of a listing page. Prices on cards are Toman."""
    parts = re.split(r'<div class="product-grid-item([^"]*)"[^>]*data-id="(\d+)">', doc)
    cards = []
    for i in range(1, len(parts) - 2, 3):
        cls, pid, body = parts[i : i + 3]
        body = body.split("woocommerce-pagination", 1)[0]
        link = re.search(r'wd-entities-title"><a href="([^"]*)">(.*?)</a>', body, re.S)
        rating = _first(r'<strong class="rating">([\d.]+)</strong>', body)
        card = {
            "id": int(pid),
            "title": _text(link.group(2)) if link else "",
            **price_info(body.split('<span class="price">', 1)[1] if '<span class="price">' in body else "", body),
            "in_stock": "outofstock" not in cls,
            "rating": float(rating) if rating else None,
            "variable": "product_type_variable" in body,
            "url": BASE + link.group(1)
            if link and link.group(1).startswith("/")
            else (link.group(1) if link else None),
        }
        cards.append(card)
    return cards


def price_info(fragment: str, labels: str = "") -> dict[str, Any]:
    """Toman prices from WooCommerce price HTML: <del>regular</del> <ins>sale</ins>, or a 'min – max' range.

    final_price = what the customer pays (lowest variant for a range), price = before discount,
    discount_pct from the site's '-10%' badge in `labels` when present, else computed.
    """
    sale_part = fragment.split("</del>", 1)[-1]
    nums = [int(x.replace(",", "")) for x in re.findall(r"<bdi>([\d,]+)", sale_part)]
    regular = [int(x.replace(",", "")) for x in re.findall(r"<bdi>([\d,]+)", fragment.split("</del>", 1)[0])]
    if not nums:
        return {"final_price": None, "price": None, "discount_pct": 0}
    final = nums[0]
    price = regular[0] if "</del>" in fragment and regular else final
    badge = _first(r'class="onsale product-label">\s*-?(\d+)%', labels)
    out: dict[str, Any] = {
        "final_price": final,
        "price": price,
        "discount_pct": int(badge) if badge else round(100 * (price - final) / price) if price > final else 0,
    }
    if len(nums) > 1:  # variable product: cheapest - most expensive variant
        out["max_price"] = nums[-1]
    return out


def _first(pattern: str, text: str) -> str | None:
    m = re.search(pattern, text, re.S)
    return m.group(1) if m else None


def _text(fragment: str | None) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment or ""))).strip()


def _norm(s: str) -> str:
    """Match Persian text loosely: Arabic ي/ك as Persian, half-space as space, case-insensitive."""
    return re.sub(r"\s+", " ", s.replace("ي", "ی").replace("ك", "ک").replace("\u200c", " ")).strip().lower()
