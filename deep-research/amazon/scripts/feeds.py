"""feeds.py - bestsellers, new releases, movers, deals feeds"""

import json
import os
import re
import sys

from amazon import fetch, log, _strip, _REGISTRY_DIR


def _load_selectors(name):
    try:
        with open(os.path.join(_REGISTRY_DIR, "selectors", f"{name}.json")) as f:
            return json.load(f)
    except Exception:
        return {}


def _load_urls():
    try:
        with open(os.path.join(_REGISTRY_DIR, "urls.json")) as f:
            return json.load(f)
    except Exception:
        return {}


# ===== BESTSELLERS =====

def blast_bestsellers(dept="", feed="best", n=20):
    urls = _load_urls()
    sel = _load_selectors("bestsellers")
    feed_paths = sel.get("feed_paths", {})
    feed_slug = feed_paths.get(feed, "bestsellers")

    url_tpl = urls.get({
        "best": "bestsellers",
        "new": "new_releases",
        "movers": "movers",
        "wished": "most_wished",
        "gifted": "most_gifted",
    }.get(feed, "bestsellers"), f"https://www.amazon.com/gp/{feed_slug}/{{dept}}/")
    url = url_tpl.replace("{dept}", dept)

    log("~", f"fetching {feed} feed: {url}")
    html = fetch(url)
    if not html:
        return []

    items = []
    blocks = list(re.finditer(
        sel.get("item_block", {}).get("alt2_pattern", r'data-asin="([A-Z0-9]{10})"'), html))

    if not blocks:
        blocks = list(re.finditer(
            sel.get("item_block", {}).get("pattern", r'id="gridItemRoot"[^>]*>'), html))

    grid_chunks = []
    for i, block in enumerate(blocks):
        start = block.start()
        end = blocks[i + 1].start() if i + 1 < len(blocks) else start + 5000
        grid_chunks.append((block, html[start:end]))

    seen = set()
    for block, chunk in grid_chunks:
        item = {}

        asin_m = re.search(r'data-asin="([A-Z0-9]{10})"', chunk)
        if not asin_m:
            asin_m = re.search(r'/dp/([A-Z0-9]{10})', chunk)
        if not asin_m or asin_m.group(1) in seen:
            continue
        item["asin"] = asin_m.group(1)
        seen.add(item["asin"])

        rank_p = sel.get("rank", {}).get("pattern", r'class="zg-bdg-text"[^>]*>#?(\d+)')
        m = re.search(rank_p, chunk)
        if not m:
            alt_p = sel.get("rank", {}).get("alt_pattern", r'class="a-badge-text"[^>]*>#?(\d+)')
            m = re.search(alt_p, chunk)
        item["rank"] = int(m.group(1)) if m else None

        title_p = sel.get("title", {}).get("pattern", r'class="_cDEzb_p13n-sc-css-line-clamp-[^"]*"[^>]*>(.*?)</')
        m = re.search(title_p, chunk, re.DOTALL)
        if not m:
            alt_p = sel.get("title", {}).get("alt_pattern", r'class="p13n-sc-truncate[^"]*"[^>]*>(.*?)</')
            m = re.search(alt_p, chunk, re.DOTALL)
        item["title"] = _strip(m.group(1)) if m else None

        price_p = sel.get("price", {}).get("pattern", r'class="_cDEzb_p13n-sc-price[^"]*"[^>]*>([^<]+)')
        m = re.search(price_p, chunk)
        if not m:
            alt_p = sel.get("price", {}).get("alt_pattern", r'class="a-color-price"[^>]*>\s*<span[^>]*>([^<]+)')
            m = re.search(alt_p, chunk)
        item["price"] = _strip(m.group(1)) if m else None

        rating_p = sel.get("rating", {}).get("pattern", r'class="a-icon-alt"[^>]*>(\d+\.?\d*)\s+out of')
        m = re.search(rating_p, chunk)
        item["rating"] = float(m.group(1)) if m else None

        review_p = sel.get("review_count", {}).get("pattern", r'class="a-size-small"[^>]*>([\d,]+)')
        m = re.search(review_p, chunk)
        item["reviews"] = m.group(1).replace(",", "") if m else None

        img_p = sel.get("image", {}).get("pattern", r'src="(https://[^"]*images-amazon[^"]+)"')
        m = re.search(img_p, chunk)
        item["image"] = m.group(1) if m else None

        item["url"] = f"https://www.amazon.com/dp/{item['asin']}"

        if item.get("title"):
            items.append(item)
            if len(items) >= n:
                break

    return items


def fmt_bestsellers_table(items, feed="best"):
    feed_names = {"best": "BESTSELLERS", "new": "NEW RELEASES", "movers": "MOVERS & SHAKERS",
                  "wished": "MOST WISHED FOR", "gifted": "MOST GIFTED"}
    lines = [f"  {feed_names.get(feed, feed.upper())}", "  " + "=" * 60, ""]
    for item in items:
        rank = f"#{item['rank']}" if item.get("rank") else "?"
        rating = f" {item['rating']}/5" if item.get("rating") else ""
        reviews = f" ({item['reviews']} reviews)" if item.get("reviews") else ""
        price = item.get("price", "?")
        lines.append(f"  {rank:>4} {(item.get('title') or '?')[:65]}")
        lines.append(f"       {price}{rating}{reviews}")
        lines.append(f"       {item['url']}")
        lines.append("")
    return "\n".join(lines)


def cmd_bestsellers(args):
    items = blast_bestsellers(dept=args.dept, feed=args.feed, n=args.n)
    log("+", f"{len(items)} items from {args.feed} feed")

    if args.format == "json":
        out = json.dumps(items, indent=2, ensure_ascii=False)
    else:
        out = fmt_bestsellers_table(items, feed=args.feed)

    if args.output:
        with open(args.output, "w") as f: f.write(out)
        log("+", f"written to {args.output}")
    else:
        print(out)


# ===== DEALS =====

def blast_deals(n=20):
    sel = _load_selectors("deals")
    url = "https://www.amazon.com/gp/goldbox"

    log("~", f"fetching deals: {url}")
    html = fetch(url)
    if not html:
        return []

    deals = []

    card_pat = sel.get("deal_card", {}).get("pattern", r'class="a-cardui dcl-product"')
    cards = list(re.finditer(card_pat, html))

    if not cards:
        log("~", "no deal cards found on goldbox page")
        return []

    seen = set()
    for i, card in enumerate(cards):
        start = card.start()
        end = cards[i + 1].start() if i + 1 < len(cards) else start + 5000
        chunk = html[start:end]

        deal = {}

        asin_p = sel.get("asin_from_link", {}).get("pattern", r'/dp/([A-Z0-9]{10})')
        m = re.search(asin_p, chunk)
        if not m or m.group(1) in seen:
            continue
        deal["asin"] = m.group(1)
        seen.add(deal["asin"])

        title_p = sel.get("title", {}).get("pattern", r'class="dcl-truncate dcl-product-label"[^>]*>\s*<span>([^<]+)</span>')
        m = re.search(title_p, chunk, re.DOTALL)
        if not m:
            alt_p = sel.get("title", {}).get("alt_pattern", r'alt="([^"]{10,})"')
            m = re.search(alt_p, chunk)
        raw_title = m.group(1) if m else None
        if raw_title:
            import html as html_mod
            deal["title"] = html_mod.unescape(_strip(raw_title))
        else:
            deal["title"] = None

        price_p = sel.get("price_current", {}).get("pattern", r'class="a-offscreen">([^<]+)</span>')
        m = re.search(price_p, chunk)
        deal["price"] = m.group(1).strip() if m else None

        orig_p = sel.get("price_original", {}).get("pattern", r'dcl-product-price-old[^>]*>.*?class="a-offscreen">([^<]+)')
        m = re.search(orig_p, chunk, re.DOTALL)
        deal["original_price"] = m.group(1).strip() if m else None

        disc_p = sel.get("discount", {}).get("pattern", r'(\d+)%\s*off')
        m = re.search(disc_p, chunk)
        deal["discount"] = f"{m.group(1)}%" if m else None

        badge_p = sel.get("deal_badge", {}).get("pattern", r'_badgeMessage[^>]*>.*?<span[^>]*>([^<]+)</span>')
        m = re.search(badge_p, chunk, re.DOTALL)
        deal["badge"] = _strip(m.group(1)) if m else None

        img_p = sel.get("image", {}).get("pattern", r'class="[^"]*dcl-dynamic-image"[^>]*src="([^"]+)"')
        m = re.search(img_p, chunk)
        deal["image"] = m.group(1) if m else None

        deal["url"] = f"https://www.amazon.com/dp/{deal['asin']}"
        deals.append(deal)
        if len(deals) >= n:
            break

    return deals


def fmt_deals_table(deals):
    lines = ["  DEALS", "  " + "=" * 60, ""]
    for i, d in enumerate(deals, 1):
        badge = f" [{d['badge']}]" if d.get("badge") else ""
        discount = f" {d['discount']} off" if d.get("discount") else ""
        lines.append(f"  [{i}]{badge} {(d.get('title') or '?')[:65]}")
        price_line = d.get("price", "?")
        if d.get("original_price"):
            price_line += f" (was {d['original_price']})"
        lines.append(f"       {price_line}{discount}")
        if d.get("url"):
            lines.append(f"       {d['url']}")
        lines.append("")
    return "\n".join(lines)


def cmd_deals(args):
    deals = blast_deals(n=args.n)
    log("+", f"{len(deals)} deals found")

    if args.format == "json":
        out = json.dumps(deals, indent=2, ensure_ascii=False)
    else:
        out = fmt_deals_table(deals)

    if args.output:
        with open(args.output, "w") as f: f.write(out)
        log("+", f"written to {args.output}")
    else:
        print(out)
