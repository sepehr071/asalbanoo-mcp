"""MCP server entry point: registers every read-only Asal Banoo tool."""

import logging

from mcp.server import MCPServer
from mcp.types import ToolAnnotations

from . import __version__, catalog, content, product  # noqa: F401  (imports register the tools)
from .registry import TOOLS

INSTRUCTIONS = """\
Unofficial, read-only access to Asal Banoo (asalbanooshop.com, عسل بانو), an Iranian online shop
for skin care, make-up, hair care and perfume with physical branches in Bandar Abbas. Asal Banoo
sells its own stock (no third-party sellers). Nothing here can log in, add to a cart, order or
post reviews.

Workflow:
1. Find products: ab_search (keyword; sort, stock and price filters) or ab_find_cheapest
   (cheapest in-stock matches whose title has every query word).
2. Browse with sort / price range / filters: ab_browse with a category slug (ab_categories)
   and/or a brand slug (ab_brands); volume, hair/skin type, gender and origin filters come from
   ab_filters.
3. One product: ab_product (price, discount, stock and exact count when low, every size/color
   variant with its own price, brand, rating, key facts), ab_reviews (customer reviews and
   questions with the shop's answers).
4. Deals: ab_deals (discounted in-stock items, biggest discount first).
5. Delivery, returns, wallet, branches: ab_shop_info. Care advice and comparisons: ab_blog_posts,
   then ab_blog_post.

Conventions: all prices are Toman (the site's JSON-LD is Rial; it is not used for prices).
final_price is what the customer pays, price is before discount, discount_pct is an int.
Variable products (several sizes/colors) list their cheapest variant as final_price and the top
of the range as max_price; ab_product gives each variant. Ratings are 1-5, null when there are no
reviews. Product ids are numbers like 6963; category and brand slugs are Latin ('hair-shampoo',
'graph'). Persian queries match best ('شامپو', 'ضد آفتاب'); search also matches descriptions,
so check titles. Delivery: outside Bandar Abbas only Post Pishtaz (7-10 working days); in Bandar
Abbas by courier, next day when ordered before 13:00. The shipping fee is shown only at checkout
(not published), so true cost = sum(final_price x qty) + an unknown shipping fee.
"""

READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=True)

mcp = MCPServer(
    "asalbanoo-mcp",
    title="Asal Banoo",
    instructions=INSTRUCTIONS,
    version=__version__,
    website_url="https://github.com/sepehr071/asalbanoo-mcp",
)

for fn, title in TOOLS:
    mcp.add_tool(fn, title=title, annotations=READ_ONLY)


def main() -> None:
    logging.getLogger("httpx").setLevel(logging.WARNING)  # one INFO line per request floods client logs
    mcp.run()


if __name__ == "__main__":
    main()
