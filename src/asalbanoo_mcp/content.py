"""Shop policies (delivery, returns, wallet) and the skin/hair care blog."""

from __future__ import annotations

import html
import re
from typing import Annotated, Any, Literal
from urllib.parse import unquote

from pydantic import Field

from .catalog import _text
from .http import BASE, ApiError, rest
from .registry import tool

PAGES = {"faq": "faq", "terms": "terms-and-conditions", "about": "about-us", "contact": "contact-us"}


@tool("Shop policies and FAQ")
async def ab_shop_info(
    topic: Annotated[
        Literal["faq", "terms", "about", "contact"],
        Field(
            description="'faq' (delivery times, shipping, originality, wallet, returns), 'terms' (cancellation, "
            "returns, delivery rules), 'about' (the shop, branches), 'contact' (phone, address, hours)."
        ),
    ] = "faq",
) -> dict[str, Any]:
    """Read one of the shop's policy pages as plain text: FAQ as question/answer pairs, other pages as text.

    Use for "how long does delivery take", "do you ship with Tipax", "can I return it", "where
    is the shop". Summary (2026-10): outside Bandar Abbas only Post Pishtaz, 7-10 working days;
    Bandar Abbas courier next day if ordered before 13:00, fee paid by the customer; no published
    shipping fee or free-shipping threshold (shown only at checkout).
    """
    data, _ = await rest("wp/v2/pages", {"slug": PAGES[topic], "_fields": "link,title,modified,content"})
    if not data:
        raise ApiError(f"The {topic} page was not found on asalbanooshop.com.")
    page = data[0]
    body = html.unescape(page["content"]["rendered"])
    toggles = re.findall(r'\[vc_toggle title=["”″](.*?)["”″][^\]]*\](.*?)\[/vc_toggle\]', body, re.S)
    out: dict[str, Any] = {
        "title": _text(page["title"]["rendered"]),
        "updated": (page.get("modified") or "")[:10] or None,
        "url": BASE + page["link"] if page["link"].startswith("/") else page["link"],
    }
    if toggles:
        out["faq"] = [{"question": _text(q), "answer": _plain(a)} for q, a in toggles]
    else:
        out["text"] = _plain(body)[:8000]
    return out


@tool("Blog posts and care guides")
async def ab_blog_posts(
    query: Annotated[
        str | None,
        Field(min_length=2, max_length=100, description="Optional keyword, e.g. 'ضد آفتاب' or 'پوست چرب'."),
    ] = None,
    page: Annotated[int, Field(ge=1, le=100, description="Page number, from 1, newest first.")] = 1,
    limit: Annotated[int, Field(ge=1, le=30, description="Posts per page.")] = 10,
) -> dict[str, Any]:
    """List Asal Banoo blog posts (skin and hair care guides, routines, "X vs Y" comparisons), newest first.

    Use for advice questions ("best moisturizer for oily skin", "Vichy or Clinique?"): find a
    matching post, then read it with ab_blog_post.
    """
    params: dict[str, Any] = {"per_page": limit, "page": page, "_fields": "id,date,link,title,excerpt"}
    if query:
        params["search"] = query.strip()
    try:
        data, total = await rest("wp/v2/posts", params)
    except ApiError as e:
        if page > 1 and "400" in str(e):  # WordPress answers 400 rest_post_invalid_page_number
            raise ApiError(f"Page {page} is past the last page of posts.") from e
        raise
    return {
        "total": total,
        "page": page,
        "posts": [
            {
                "id": p["id"],
                "title": _text(p["title"]["rendered"]),
                "date": p["date"][:10],
                "summary": _plain(p["excerpt"]["rendered"])[:250],
                "url": BASE + p["link"],
            }
            for p in data
        ],
    }


@tool("Read a blog post")
async def ab_blog_post(
    post_id: Annotated[int, Field(ge=1, le=100_000_000, description="Post id from ab_blog_posts, e.g. 791485.")],
    max_chars: Annotated[int, Field(ge=500, le=20000, description="Cut the text after this many characters.")] = 6000,
) -> dict[str, Any]:
    """Read one blog post as plain text, plus the products and categories it links to.

    Use after ab_blog_posts to answer care questions from the shop's own guides. Linked products
    can be looked up with ab_search (by name) and categories browsed with ab_browse (slug).
    """
    try:
        data, _ = await rest(f"wp/v2/posts/{post_id}", {"_fields": "id,date,link,title,content"})
    except ApiError as e:
        if "404" in str(e):
            raise ApiError(f"No blog post {post_id}; get ids from ab_blog_posts.") from e
        raise
    body = data["content"]["rendered"]
    text = _plain(body)
    links = [
        unquote(u) for u in re.findall(r'href="(?:https://asalbanooshop\.com)?(/product(?:-category)?/[^"#?]+)', body)
    ]
    return {
        "id": data["id"],
        "title": _text(data["title"]["rendered"]),
        "date": data["date"][:10],
        "url": BASE + data["link"],
        "text": text[:max_chars],
        "truncated": len(text) > max_chars,
        "product_links": list(dict.fromkeys(BASE + u for u in links if u.startswith("/product/")))[:20],
        "category_slugs": list(
            dict.fromkeys(u.rstrip("/").rsplit("/", 1)[-1] for u in links if u.startswith("/product-category/"))
        )[:20],
    }


def _plain(fragment: str) -> str:
    """WordPress HTML with WPBakery shortcodes ([vc_row], [vc_column_text ...]) as plain text, one line per block."""
    text = re.sub(r"\[/?vc_[^\]]*\]", " ", html.unescape(fragment))
    text = re.sub(r"<br\s*/?>|</(?:p|li|h\d|div|tr)>", "\n", text)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    return "\n".join(line for line in (re.sub(r"[ \t\xa0]+", " ", x).strip() for x in text.splitlines()) if line)
