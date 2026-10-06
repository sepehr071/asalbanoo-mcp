<!-- mcp-name: io.github.sepehr071/asalbanoo-mcp -->

<div align="center">

<img src="https://raw.githubusercontent.com/sepehr071/asalbanoo-mcp/main/.github/banner.png" alt="asalbanoo-mcp: let your AI agent find the cheapest sunscreen you can actually order on Asal Banoo" width="100%">

# 🧴 asalbanoo-mcp

**Let your AI agent shop for cosmetics and skin care on Asal Banoo.**<br>
Search shampoos, sunscreens, serums and make-up, compare real prices and sizes,<br>
read reviews and the shop's skin advice, check stock and catch today's discounts, all from Claude, Cursor or Copilot.

[![PyPI](https://img.shields.io/pypi/v/asalbanoo-mcp?color=2563eb)](https://pypi.org/project/asalbanoo-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/asalbanoo-mcp)](https://pypi.org/project/asalbanoo-mcp/)
[![CI](https://github.com/sepehr071/asalbanoo-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/sepehr071/asalbanoo-mcp/actions/workflows/ci.yml)
[![MCP Registry](https://img.shields.io/badge/MCP_Registry-io.github.sepehr071%2Fasalbanoo--mcp-7c3aed)](https://registry.modelcontextprotocol.io/?q=asalbanoo-mcp)
[![License: MIT](https://img.shields.io/badge/license-MIT-16a34a)](https://github.com/sepehr071/asalbanoo-mcp/blob/main/LICENSE)

[![Install in Cursor](https://cursor.com/deeplink/mcp-install-dark.svg)](https://cursor.com/en/install-mcp?name=asalbanoo&config=eyJjb21tYW5kIjoidXZ4IiwiYXJncyI6WyJhc2FsYmFub28tbWNwIl19)
[![Install in VS Code](https://img.shields.io/badge/VS_Code-Install_asalbanoo--mcp-0098FF?style=flat-square&logo=visualstudiocode&logoColor=white)](https://vscode.dev/redirect/mcp/install?name=asalbanoo&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22asalbanoo-mcp%22%5D%7D)

[Quick start](#quick-start) · [What it can do](#what-it-can-do) · [Tools](#tools) · [FAQ](#faq) · [فارسی](#فارسی)

</div>

---

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

- 🔎 **Search** products by name in Persian or English, with price, discount, stock and rating
- 💸 **Find the cheapest** in-stock match whose title really contains your words
- 🗂️ **Browse** any category or brand sorted by price, date, popularity or rating, with price range, volume and hair/skin type filters
- 📋 **Read** product details: every size/color with its own price and stock, key facts (volume, skin type, origin), reviews with the shop's answers
- ⚡ **Catch deals**: everything discounted right now, biggest discount first
- 📚 **Get advice** from the shop's care guides and comparisons, plus delivery, return and wallet rules
- 🔒 **Read-only by design**: no login, no cart, no orders, no reviews posted

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

Click **Install in Cursor** above, or add the Claude Desktop block to `~/.cursor/mcp.json`.
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
<summary><b>Anything else</b></summary>

It's a standard stdio MCP server: run `uvx asalbanoo-mcp`, or `pip install asalbanoo-mcp` and run `asalbanoo-mcp`.
</details>

Then just ask:

- "Cheapest anti-dandruff shampoo between 1 and 2 million Toman, and which one has the best reviews?"
- "How much is the 1000 ml Roverhair Detox shampoo, and is it in stock?"
- "Vichy Mineral 89 or Clinique Moisture Surge for oily skin?"
- <span dir="rtl">تخفیف&zwnj;های امروز عسل بانو روی ضد آفتاب چیه؟</span>

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

## Tools

<details open>
<summary><b>🔎 Find products</b> (7)</summary>

| Tool | What it does |
|---|---|
| `ab_search` | Search by keyword: price, discount, stock, rating, with sort and price range |
| `ab_find_cheapest` | Cheapest in-stock matches for a keyword, one flat list (titles must contain every word) |
| `ab_browse` | A category, brand or the whole shop sorted by price / date / popularity / rating, with price range and filters |
| `ab_filters` | Volume, hair/skin type, gender and origin filters of a category or brand, with counts |
| `ab_categories` | Product categories with slugs and product counts |
| `ab_brands` | Brands with slugs and product counts |
| `ab_deals` | Everything discounted and in stock, biggest discount first |
</details>

<details open>
<summary><b>📋 One product</b> (2)</summary>

| Tool | What it does |
|---|---|
| `ab_product` | Price, discount, stock (exact count when low), every size/color variant, brand, rating, key facts |
| `ab_reviews` | Customer reviews and questions with star breakdown and the shop's answers |
</details>

<details open>
<summary><b>📚 Shop info and blog</b> (3)</summary>

| Tool | What it does |
|---|---|
| `ab_shop_info` | FAQ, terms, about and contact pages as text: delivery times, returns, wallet, branches |
| `ab_blog_posts` | Skin and hair care guides and comparisons, newest first |
| `ab_blog_post` | One guide as plain text, with the products and categories it links to |
</details>

All 12 tools are annotated `readOnlyHint: true` and return compact structured JSON, so they don't flood the agent's context.

## Good to know

- **Prices are in Toman.** `final_price` is what you pay, `price` is before discount, `discount_pct` is a whole percent. The site's structured data is in Rial; the server doesn't use it for prices.
- **Sizes and colors**: a product with variants is listed at its cheapest variant (`final_price`) up to `max_price`, with the biggest variant discount as `discount_pct`; `ab_product` gives each variant's price, stock and `max_qty`.
- **Delivery**: outside Bandar Abbas only by Post Pishtaz, 7-10 working days. In Bandar Abbas by courier, next day when ordered before 13:00, or pick up in the two branches. The shipping fee is shown only at checkout and is not published.
- **Stock**: `in_stock` means orderable online now; `stock_status` shows the exact count when few are left ("فقط 2 عدد در انبار موجود است"). When nothing in stock matches, `ab_search` adds `out_of_stock_matches` so a sold-out brand isn't mistaken for one the shop never carried.
- **Ratings are 1–5**, `null` when nobody has reviewed the product yet.
- **Persian queries match best** (`شامپو`, `ضد آفتاب`), but English brand names work too (`vichy`, `la roche`). There is no separate autocomplete tool: `ab_search` covers the site's header live search.

## FAQ

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
<summary><b>I get "Could not reach asalbanooshop.com" or a bot challenge error</b></summary>

The site answers new visitors with a small cookie challenge (HTTP 418); the server solves it automatically and
retries a dropped connection once. If it still fails, check your internet connection. System proxy variables are
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
| `ASALBANOO_MCP_PROXY` | unset | HTTP proxy for every request, e.g. `http://user:pass@host:port` |

## فارسی

<div dir="rtl">

**asalbanoo-mcp** به دستیار هوش مصنوعی شما (Claude، Cursor، Copilot و ...) اجازه می&zwnj;دهد در فروشگاه عسل بانو جستجو کند،
ارزان&zwnj;ترین محصول موجود را پیدا کند، قیمت حجم&zwnj;ها و رنگ&zwnj;های مختلف را مقایسه کند، نظرات و پاسخ مشاوران را بخواند و تخفیف&zwnj;های روز را ببیند.

- فقط خواندنی است: وارد حساب نمی&zwnj;شود، سبد خرید نمی&zwnj;سازد، سفارش ثبت نمی&zwnj;کند و نظر نمی&zwnj;فرستد.
- قیمت&zwnj;ها به تومان است.
- روی سیستم خود شما اجرا می&zwnj;شود و به هیچ سرور واسطی داده نمی&zwnj;فرستد.

**نصب در Claude Code:**

</div>

```bash
claude mcp add asalbanoo -- uvx asalbanoo-mcp
```

<div dir="rtl">

بعد بپرسید: «ارزان&zwnj;ترین شامپو ضد شوره بین ۱ تا ۲ میلیون تومان کدام است و نظر خریداران درباره&zwnj;اش چیست؟»

</div>

## Development

```bash
git clone https://github.com/sepehr071/asalbanoo-mcp && cd asalbanoo-mcp
uv sync
uv run pytest            # offline, against recorded responses
uv run pytest -m live    # real asalbanooshop.com
uv run ruff check .
```

Tools live in `src/asalbanoo_mcp/catalog.py`, `product.py` and `content.py`; each is a typed async function with a
docstring that tells the agent when to use it. Issues and PRs are welcome, especially new tools and fixes for site changes.

Releases: bump the version in `pyproject.toml` and `server.json`, then push a `v*` tag. GitHub Actions tests,
publishes to PyPI and the [MCP Registry](https://registry.modelcontextprotocol.io), and creates the GitHub Release.

## Disclaimer

Unofficial and not affiliated with or endorsed by Asal Banoo. It uses the public pages and endpoints of the
asalbanooshop.com website, which can change without notice. Please keep request rates reasonable.

## License

[MIT](https://github.com/sepehr071/asalbanoo-mcp/blob/main/LICENSE)
