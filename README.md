<!-- mcp-name: io.github.sepehr071/asalbanoo-mcp -->

<div align="center">

<img src="https://raw.githubusercontent.com/sepehr071/asalbanoo-mcp/main/.github/banner.png" alt="asalbanoo-mcp: unofficial Asal Banoo MCP server for Claude, Cursor and Copilot" width="100%">

# asalbanoo-mcp: Asal Banoo MCP server for AI agents

**Let your AI agent shop for cosmetics and skin care on Asal Banoo (عسل بانو).**<br>
An unofficial, read-only MCP server for [asalbanooshop.com](https://asalbanooshop.com), an Iranian online shop for skin care, hair care, make-up and perfume:<br>
search products, find the cheapest in-stock match, compare sizes and prices, read reviews and catch discounts, from Claude, Cursor or Copilot.

[![PyPI](https://img.shields.io/pypi/v/asalbanoo-mcp?color=2563eb)](https://pypi.org/project/asalbanoo-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/asalbanoo-mcp)](https://pypi.org/project/asalbanoo-mcp/)
[![CI](https://github.com/sepehr071/asalbanoo-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/sepehr071/asalbanoo-mcp/actions/workflows/ci.yml)
[![MCP Registry](https://img.shields.io/badge/MCP_Registry-io.github.sepehr071%2Fasalbanoo--mcp-7c3aed)](https://registry.modelcontextprotocol.io/?q=asalbanoo-mcp)
[![License: MIT](https://img.shields.io/badge/license-MIT-16a34a)](https://github.com/sepehr071/asalbanoo-mcp/blob/main/LICENSE)
[![mcpfarsi](https://mcpfarsi.ir/badge/asalbanoo.svg)](https://mcpfarsi.ir/servers/asalbanoo/)

[![Install in Cursor](https://cursor.com/deeplink/mcp-install-dark.svg)](https://cursor.com/en/install-mcp?name=asalbanoo&config=eyJjb21tYW5kIjoidXZ4IiwiYXJncyI6WyJhc2FsYmFub28tbWNwIl19)
[![Install in VS Code](https://img.shields.io/badge/VS_Code-Install_asalbanoo--mcp-0098FF?style=flat-square&logo=visualstudiocode&logoColor=white)](https://vscode.dev/redirect/mcp/install?name=asalbanoo&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22asalbanoo-mcp%22%5D%7D)

[For AI agents](#for-ai-agents) · [Why](#why) · [What it can do](#what-it-can-do) · [Quick start](#quick-start) · [Tools](#tools) · [How it works](#how-it-works) · [Good to know](#good-to-know) · [FAQ](#faq) · [Configuration](#configuration) · [فارسی](#فارسی) · [Development](#development)

</div>

---

## For AI agents

- **What:** unofficial MCP server (model context protocol) for Asal Banoo (asalbanooshop.com, عسل بانو), an Iranian skin care, hair care, make-up and perfume shop with branches in Bandar Abbas. Queries work in Persian and English.
- **Install:** `uvx asalbanoo-mcp` or `claude mcp add asalbanoo -- uvx asalbanoo-mcp`. Transport: stdio. Needs [uv](https://docs.astral.sh/uv/getting-started/installation/) (Python 3.10+).
- **Auth:** none, no API key or account. Optional `ASALBANOO_MCP_PROXY` sets an HTTP proxy (or a comma-separated list) for requests to asalbanooshop.com; system proxy settings are ignored.
- **Access:** read-only. It cannot log in, use a cart, place orders or post reviews, so no confirmation is needed before calling any tool.
- **Tools:** 12, all prefixed `ab_`. Start with `ab_find_cheapest`, `ab_search`, `ab_product` or `ab_deals`. Typical sequence: `ab_find_cheapest` -> `ab_product` -> `ab_reviews`. Take a product's `id` from `ab_search` or `ab_browse` and pass it as `product_id` to `ab_product` and `ab_reviews`. Category and brand slugs for `ab_browse` come from `ab_categories` and `ab_brands`.
- **Units:** prices in **Toman**. `final_price` is what the buyer pays, `price` is before discount, `discount_pct` is a whole percent, ratings are 1-5 or `null`. In product lists, null fields are left out: no `price` means it equals `final_price`, no `discount_pct` means 0, no `rating` means no reviews. Review texts are cut at 400 characters (`full_text=true` on `ab_reviews` returns them whole).
- **Use when:** the user compares cosmetics and skin care prices, sizes, stock, reviews or current discounts on Asal Banoo, or wants the shop's care guides and delivery rules.
- **Do not use when:** the user wants to buy something (no cart or checkout), needs a shipping fee (the shop shows it only at checkout), or asks about another shop.
- **Machine-readable:** [`server.json`](https://github.com/sepehr071/asalbanoo-mcp/blob/main/server.json), and the catalog of all Iranian MCP servers at [iran-mcp](https://github.com/sepehr071/iran-mcp) ([TOOLS.md](https://github.com/sepehr071/iran-mcp/blob/main/TOOLS.md), [servers.json](https://github.com/sepehr071/iran-mcp/blob/main/servers.json), [llms.txt](https://github.com/sepehr071/iran-mcp/blob/main/llms.txt)).

## Why

Asal Banoo (عسل بانو) lists about 3,500 skin, hair, make-up and perfume products, and a search for
"sunscreen" mixes in eye creams, sold-out items and products that only mention sunscreen in their
description. Finding *the cheapest one you can actually order, in the size you want*, means paging
through listings and opening product pages. An agent with `asalbanoo-mcp` does that in seconds:

> **You:** Cheapest sunscreen I can order now?
>
> **Agent:** *calls* `ab_find_cheapest(query="ضد آفتاب")` → `ab_product(product_id=28470)`
>
> | Price | Product | Note |
> |---:|---|---|
> | **427,300** | ضد آفتاب دور چشم آیسول | eye area, untinted; the tinted one (432,200) is sold out |
> | **499,800** | ضدآفتاب دور چشم فتوتیپیک SPF30 درماتیپیک | eye-area, rating 1.5 |
> | **599,800** | ضد آفتاب پوست خشک درماتیپیک Hydra | face, dry skin, 5 tints up to 899,800 |
>
> The two cheapest are for the eye area. For the face, the Dermatypique Hydra is listed from 599,800 Toman,
> but only its Light Beige tint is in stock, at 899,800. Want me to check its reviews with `ab_reviews`?

<sub>Real tool output from 2026-10-06; prices change all the time. Prices are in Toman.</sub>

## What it can do

- **Search** products by name in Persian or English, with price, discount, stock and rating
- **Find the cheapest** in-stock match whose title really contains your words
- **Browse** any category or brand sorted by price, date, popularity or rating, with price range, volume and hair/skin type filters
- **Read** product details: every size/color with its own price and stock, key facts (volume, skin type, origin), reviews with the shop's answers
- **Catch deals**: everything discounted right now, biggest discount first
- **Get advice** from the shop's care guides and comparisons, plus delivery, return and wallet rules
- **Read-only by design**: no login, no cart, no orders, no reviews posted

Example prompts:

- "Cheapest anti-dandruff shampoo between 1 and 2 million Toman, and which one has the best reviews?"
- "How much is the 1000 ml Roverhair Detox shampoo, and is it in stock?"
- "Vichy Mineral 89 or Clinique Moisture Surge for oily skin?"
- "Which Asal Banoo products are discounted the most today?"
- <span dir="rtl">تخفیف&zwnj;های امروز عسل بانو روی ضد آفتاب چیه؟</span>
- <span dir="rtl">ارزان&zwnj;ترین شامپو ضد شوره موجود در عسل بانو کدومه؟</span>
- <span dir="rtl">نظر خریداران درباره سرم ویتامین سی چیه؟</span>

## Quick start

You need [uv](https://docs.astral.sh/uv/getting-started/installation/). No API key or account.

<details open>
<summary><b>Claude Code</b></summary>

```bash
claude mcp add asalbanoo -- uvx asalbanoo-mcp
```
</details>

<details>
<summary><b>Claude Desktop</b></summary>

Settings → Developer → Edit Config, then add:

```json
{
  "mcpServers": {
    "asalbanoo": { "command": "uvx", "args": ["asalbanoo-mcp"] }
  }
}
```
</details>

<details>
<summary><b>Cursor</b></summary>

Click **Install in Cursor** above, or add the Claude Desktop block to `~/.cursor/mcp.json` (or `.cursor/mcp.json` in a project).
</details>

<details>
<summary><b>VS Code (Copilot agent mode)</b></summary>

Click **Install in VS Code** above, or add to `.vscode/mcp.json`:

```json
{
  "servers": {
    "asalbanoo": { "type": "stdio", "command": "uvx", "args": ["asalbanoo-mcp"] }
  }
}
```
</details>

<details>
<summary><b>Codex CLI</b></summary>

```bash
codex mcp add asalbanoo -- uvx asalbanoo-mcp
```

Or in `~/.codex/config.toml`:

```toml
[mcp_servers.asalbanoo]
command = "uvx"
args = ["asalbanoo-mcp"]
```
</details>

<details>
<summary><b>Gemini CLI</b></summary>

Add to `~/.gemini/settings.json`:

```json
{
  "mcpServers": {
    "asalbanoo": { "command": "uvx", "args": ["asalbanoo-mcp"] }
  }
}
```
</details>

<details>
<summary><b>Windsurf</b></summary>

Add the Claude Desktop block to `~/.codeium/windsurf/mcp_config.json`.
</details>

<details>
<summary><b>Anything else</b></summary>

It's a standard stdio MCP server: run `uvx asalbanoo-mcp`, or `pip install asalbanoo-mcp` and run `asalbanoo-mcp`.
</details>

## Tools

All 12 tools are prefixed `ab_` and annotated `readOnlyHint: true`. They return compact JSON, so they don't flood the agent's context.

<details open>
<summary><b>Find products</b> (7)</summary>

| Tool | What it does |
|---|---|
| `ab_search` | Search by keyword: price, discount, stock, rating, with sort and price range |
| `ab_find_cheapest` | Cheapest in-stock matches for a keyword, one flat list (titles must contain every word) |
| `ab_browse` | A category, brand or the whole shop sorted by price / date / popularity / rating, with price range and filters |
| `ab_filters` | Volume, hair/skin type, gender and origin filters of a category or brand, with counts |
| `ab_categories` | Product categories (about 70) with slugs and product counts |
| `ab_brands` | Brands (about 250) with slugs and product counts |
| `ab_deals` | Everything discounted and in stock, biggest discount first |
</details>

<details open>
<summary><b>One product</b> (2)</summary>

| Tool | What it does |
|---|---|
| `ab_product` | Price, discount, stock (exact count when low), every size/color variant, brand, rating, key facts |
| `ab_reviews` | Customer reviews and questions with star breakdown and the shop's answers |
</details>

<details open>
<summary><b>Shop info and blog</b> (3)</summary>

| Tool | What it does |
|---|---|
| `ab_shop_info` | FAQ, terms, about and contact pages as text: delivery (outside Bandar Abbas Post Pishtaz 7-10 working days; Bandar Abbas courier, next day before 13:00), returns, wallet, branches |
| `ab_blog_posts` | Skin and hair care guides and comparisons, newest first |
| `ab_blog_post` | One guide as plain text, with the products and categories it links to |
</details>

## How it works

```text
  AI agent  (Claude, Cursor, Copilot, ...)
      │
      │  MCP over stdio
      ▼
  asalbanoo-mcp  (runs on your machine)
      │
      │  HTTPS
      └──────▶  asalbanooshop.com   listing pages, quick-view fragments, WordPress REST
```

`asalbanoo-mcp` runs locally and calls the same public pages and endpoints the asalbanooshop.com website uses.
There's no hosted server in between, no API key, and nothing about you is sent anywhere else.

The shop has no public product API: prices come from listing cards, the product quick view and the site's live search,
so the server parses that HTML with the Python standard library. Requests go out through a Chrome-impersonating
client, at most 2 at a time with a little jitter. It solves the site's small cookie challenge (HTTP 418)
automatically, retries timeouts, dropped connections, 429 and 5xx up to twice, and keeps the category and brand lists
for an hour. It only reads.

## Good to know

- **Prices are in Toman.** `final_price` is what you pay, `price` is before discount, `discount_pct` is a whole percent. The site's structured data is in Rial; the server doesn't use it for prices.
- **Images**: every product has `image` (absolute, percent-encoded https URL); `ab_product` also has `images` (gallery). To download one yourself send a browser `User-Agent`: plain python/httpx gets HTTP 403 from the site's WAF.
- **Sizes and colors**: a product with variants is listed at its cheapest variant (`final_price`) up to `max_price`, with the biggest variant discount as `discount_pct`; `ab_product` gives each variant's price, stock and `max_qty`.
- **Delivery**: outside Bandar Abbas only by Post Pishtaz, 7-10 working days. In Bandar Abbas by courier, next day when ordered before 13:00, or pick up in the two branches. The shipping fee is shown only at checkout and is not published.
- **Stock**: `in_stock` means orderable online now; `stock_status` shows the exact count when few are left ("فقط 2 عدد در انبار موجود است"). When nothing in stock matches, `ab_search` adds `out_of_stock_matches` so a sold-out brand isn't mistaken for one the shop never carried.
- **Ratings are 1-5**, `null` when nobody has reviewed the product yet. Review dates are Jalali (for example `1405-07-13`).
- **Persian queries match best** (`شامپو`, `ضد آفتاب`), but English brand names work too (`vichy`, `la roche`). There is no separate autocomplete tool: `ab_search` covers the site's header live search.
- **Search also matches descriptions**, so check titles; `ab_find_cheapest` filters on titles for you.
- **Privacy**: review authors' contact details are never extracted or returned.
- **Rate limits**: none seen at about one request per second. The site's `robots.txt` disallows the listing query parameters for crawlers, so please keep request rates low.
- **What it does not do**: no login, cart, checkout, coupons, wallet, wishlist, posted reviews or contact forms; no shipping fee (not published); no other shops.

## FAQ

<details>
<summary><b>Is there an Asal Banoo API or MCP server for AI agents?</b></summary>

Asal Banoo doesn't publish an official API for agents. `asalbanoo-mcp` is an unofficial MCP server that reads the
public pages and endpoints of asalbanooshop.com and exposes them as 12 read-only tools.
</details>

<details>
<summary><b>Can it place an order for me?</b></summary>

No, and that's deliberate. It has no login and never touches the cart, checkout, wallet, wishlist or review endpoints.
The agent finds the best option; you buy it on asalbanooshop.com.
</details>

<details>
<summary><b>Why does <code>ab_find_cheapest</code> skip some items?</b></summary>

The site's search also matches product descriptions, so `ab_find_cheapest` keeps only in-stock items whose title
contains every word of your query (`match_all_words: false` turns that off). It scans the 150 cheapest in-stock
results by default; `complete: false` in the reply means more lie past that, so raise `scan` (up to 300).
</details>

<details>
<summary><b>How do I use Asal Banoo with Claude, Cursor or Copilot?</b></summary>

Install the server once (see [Quick start](#quick-start)), then ask in plain language, in Persian or English. In Claude Code
the install is `claude mcp add asalbanoo -- uvx asalbanoo-mcp`.
</details>

<details>
<summary><b>Are prices in Rial or Toman?</b></summary>

Toman. The site's structured data uses Rial, but the server reads the Toman prices shown on the pages.
</details>

<details>
<summary><b>Is it official, safe and free?</b></summary>

It is unofficial and free (MIT). It is read-only, needs no account or API key, and runs on your machine with no
hosted server in between.
</details>

<details>
<summary><b>I get "Could not reach asalbanooshop.com" or a bot challenge error</b></summary>

The site answers new visitors with a small cookie challenge (HTTP 418); the server solves it automatically and
retries timeouts, dropped connections, 429 and 5xx up to twice. Requests use a Chrome TLS and header profile. If the
site serves a browser check instead, install `asalbanoo-mcp[browser]` and run `patchright install chromium`; the server
then clears it in a headless browser. If it still fails, check your internet connection. System proxy variables are
ignored on purpose; set `ASALBANOO_MCP_PROXY` if you need a proxy.
</details>

<details>
<summary><b>Claude Desktop says <code>uvx</code> is not found</b></summary>

Use the full path to `uvx` (`where uvx` on Windows, `which uvx` on macOS/Linux) as `command`.
</details>

<details>
<summary><b>How do I debug what the agent sees?</b></summary>

```bash
npx @modelcontextprotocol/inspector uvx asalbanoo-mcp
```
</details>

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `ASALBANOO_MCP_PROXY` | unset | Optional HTTP proxy URL for asalbanooshop.com requests, e.g. `http://user:pass@host:port`; system proxy settings are ignored. A comma-separated list is used one at a time, moving on after a block or connect error |

<a id="فارسی"></a>

## فارسی: سرور MCP عسل بانو

<div dir="rtl">

**asalbanoo-mcp** یک سرور MCP غیررسمی برای فروشگاه اینترنتی **عسل بانو** (asalbanooshop.com) است؛ فروشگاه ایرانی محصولات مراقبت از پوست، مراقبت از مو، آرایشی و عطر. این سرور به دستیار هوش مصنوعی شما (Claude، Cursor، Copilot و ...) اجازه می&zwnj;دهد در عسل بانو جستجو کند،
ارزان&zwnj;ترین محصول موجود را پیدا کند، قیمت حجم&zwnj;ها و رنگ&zwnj;های مختلف را مقایسه کند، نظرات و پاسخ مشاوران را بخواند و تخفیف&zwnj;های روز را ببیند.

**چه کارهایی می&zwnj;کند**

- **جستجوی محصول** به فارسی یا انگلیسی، مثلاً شامپو، ضد آفتاب، سرم، کرم مرطوب&zwnj;کننده یا برند (مثل vichy).
- **ارزان&zwnj;ترین محصول موجود** با قیمت، تخفیف و موجودی.
- **مرور دسته&zwnj;ها و برندها** با فیلتر حجم، نوع پوست و مو و بازه قیمت.
- **جزئیات محصول**: قیمت هر حجم و رنگ، موجودی، ویژگی&zwnj;ها، نظرات خریداران و پاسخ فروشگاه.
- **تخفیف&zwnj;های روز** به ترتیب بیشترین تخفیف.
- **مقالات و راهنماها**: مراقبت از پوست و مو، مقایسه محصولات، شرایط ارسال و بازگشت کالا.

**نکته&zwnj;ها**

- فقط خواندنی است: وارد حساب نمی&zwnj;شود، سبد خرید نمی&zwnj;سازد، سفارش ثبت نمی&zwnj;کند و نظر نمی&zwnj;فرستد. خرید را خودتان در سایت انجام می&zwnj;دهید.
- قیمت&zwnj;ها به تومان است.
- هزینه ارسال در سایت منتشر نشده و فقط هنگام پرداخت نمایش داده می&zwnj;شود.
- کلید API لازم نیست و روی سیستم خود شما اجرا می&zwnj;شود و به هیچ سرور واسطی داده نمی&zwnj;فرستد.

**نصب** (اول [uv](https://docs.astral.sh/uv/getting-started/installation/) را نصب کنید). در Claude Code:

</div>

```bash
claude mcp add asalbanoo -- uvx asalbanoo-mcp
```

<div dir="rtl">

در Claude Desktop، Cursor و بقیه برنامه&zwnj;ها همان تنظیم بخش [Quick start](#quick-start) را بگذارید.

**نمونه پرسش&zwnj;ها**

- «ارزان&zwnj;ترین شامپو ضد شوره بین ۱ تا ۲ میلیون تومان کدام است و نظر خریداران درباره&zwnj;اش چیست؟»
- «تخفیف&zwnj;های امروز عسل بانو روی ضد آفتاب چیست؟»
- «ضد آفتاب پوست چرب موجود در عسل بانو چند است؟»

برای جستجو کافی است محصول یا برند را به فارسی یا انگلیسی بنویسید، مثلاً «ضد آفتاب» یا «vichy».

</div>

## Development

```bash
git clone https://github.com/sepehr071/asalbanoo-mcp && cd asalbanoo-mcp
uv sync
uv run ruff check . && uv run ruff format --check .
uv run python -m pytest -q          # offline, against recorded responses
uv run python -m pytest -m live -q  # real asalbanooshop.com
uv build
```

Tools live in `src/asalbanoo_mcp/catalog.py`, `product.py` and `content.py`; each is a typed async function with a
docstring that tells the agent when to use it. Issues and PRs are welcome, especially new tools and fixes for site changes.

Releases: bump the version in `pyproject.toml` and `server.json`, then push a `v*` tag. GitHub Actions tests,
publishes to PyPI and the [MCP Registry](https://registry.modelcontextprotocol.io), and creates the GitHub Release.

## Related servers

- [iran-mcp](https://github.com/sepehr071/iran-mcp): catalog of all Iranian-service MCP servers
- [Khanoumi MCP server](https://github.com/sepehr071/khanoumi-mcp) for cosmetics and skin care prices and shades
- [Shopino MCP server](https://github.com/sepehr071/shopino-mcp) for fashion across thousands of Iranian shops
- [Banimode MCP server](https://github.com/sepehr071/banimode-mcp) for fashion prices and sizes on Banimode
- [Digikala MCP server](https://github.com/sepehr071/digikala-mcp) for products and prices on Digikala
- [Torob MCP server](https://github.com/sepehr071/torob-mcp) for comparing prices across Iranian shops
- Listed on [mcpfarsi.ir](https://mcpfarsi.ir/servers/asalbanoo/), the Persian MCP marketplace

If this saves you clicks, a star helps others find it.

## Disclaimer

Unofficial and not affiliated with or endorsed by Asal Banoo. It is read-only and uses the public pages and
endpoints of the asalbanooshop.com website, which can change without notice. Please keep request rates reasonable.

## Author

<a href="https://www.linkedin.com/in/sepehr-radmard"><img src="https://raw.githubusercontent.com/sepehr071/iran-mcp/main/assets/author-banner.png" alt="Sepehr Radmard: open-source MCP servers for the Iranian web. LinkedIn: linkedin.com/in/sepehr-radmard" width="100%"></a>

Built and maintained by **Sepehr Radmard** (سپهر رادمرد). Connect on [LinkedIn](https://www.linkedin.com/in/sepehr-radmard) or follow [@sepehr071 on GitHub](https://github.com/sepehr071) for more MCP servers for Iranian websites, all listed in [iran-mcp](https://github.com/sepehr071/iran-mcp). If this saves you time, a star on the repo helps other people find it.

## License

[MIT](https://github.com/sepehr071/asalbanoo-mcp/blob/main/LICENSE)
