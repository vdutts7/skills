"""search.py - Amazon search + category browsing"""

import json
import os
import re
import sys
from urllib.parse import quote_plus, urlencode

from amazon import fetch, log, _strip, _REGISTRY_DIR


def _load_selectors():
    try:
        with open(os.path.join(_REGISTRY_DIR, "selectors", "search.json")) as f:
            return json.load(f)
    except Exception:
        return {}


def _load_urls():
    try:
        with open(os.path.join(_REGISTRY_DIR, "urls.json")) as f:
            return json.load(f)
    except Exception:
        return {}


def search_amazon(query, n=10, min_rating=0.0):
    """search Amazon via TLS-impersonated HTTP."""
    url = f"https://www.amazon.com/s?k={quote_plus(query)}"
    log("~", f"searching: {query}")
    html = fetch(url)
    if not html:
        return []

    results = []
    seen = set()

    blocks = list(re.finditer(
        r'<div[^>]*data-asin="([A-Z0-9]{10})"[^>]*data-component-type="s-search-result"', html))

    for i, block in enumerate(blocks):
        asin = block.group(1)
        if asin in seen:
            continue
        seen.add(asin)

        start = block.start()
        end = blocks[i + 1].start() if i + 1 < len(blocks) else start + 10000
        chunk = html[start:end]

        if "puis-sponsored-label" in chunk[:5000] or ">Sponsored<" in chunk[:3000]:
            continue

        r = {"asin": asin, "url": f"https://www.amazon.com/dp/{asin}"}

        m = re.search(r'<h2[^>]*>(.*?)</h2>', chunk[:8000], re.DOTALL)
        if m:
            raw = re.sub(r'<[^>]{0,500}>', ' ', m.group(1))
            raw = re.sub(r'\s+', ' ', raw).strip()
            if len(raw) > 20:
                r["title"] = raw[:200]
            else:
                spans = re.findall(r'<span[^>]*>(.*?)</span>', m.group(1), re.DOTALL)
                texts = sorted([re.sub(r'<[^>]+>', '', s).strip() for s in spans], key=len, reverse=True)
                r["title"] = texts[0][:200] if texts and len(texts[0]) > 10 else raw[:200]
        else:
            r["title"] = None

        r["price"] = None
        offscreens = re.findall(r'class="a-offscreen"[^>]*>([^<]+)', chunk[:8000])
        for os_val in offscreens:
            os_val = os_val.strip()
            if os_val.startswith('$') and not os_val.startswith('$0'):
                if 'List' not in os_val:
                    r["price"] = os_val
                    break
        if not r["price"]:
            price_m = re.search(r'>\s*(\$\d[\d,]*\.?\d{0,2})\s*<', chunk[:12000])
            if price_m:
                r["price"] = price_m.group(1)

        m = re.search(r'class="a-icon-alt"[^>]*>(\d+\.?\d*)\s+out of\s+5', chunk[:8000])
        r["rating"] = float(m.group(1)) if m else None

        rcount_pats = [
            r'aria-label="([\d,]+)"',
            r'<span[^>]*class="a-size-base[^"]*"[^>]*>([\d,]+)</span>',
        ]
        r["reviews"] = None
        for rp in rcount_pats:
            m = re.search(rp, chunk[:8000])
            if m:
                r["reviews"] = m.group(1).replace(",", "")
                break

        m = re.search(r'class="s-image"[^>]*src="([^"]+)"', chunk[:5000])
        r["image"] = m.group(1) if m else None

        r["prime"] = "a-icon-prime" in chunk[:5000]

        if r["title"]:
            if min_rating and r.get("rating") and r["rating"] < min_rating:
                continue
            results.append(r)
            if len(results) >= n:
                break

    return results


def fmt_search_table(results):
    lines = []
    for i, r in enumerate(results, 1):
        prime = " [PRIME]" if r.get("prime") else ""
        rating = f" {r['rating']}/5" if r.get("rating") else ""
        reviews = f" ({r['reviews']} reviews)" if r.get("reviews") else ""
        lines.append(f"  [{i}] {r.get('title', '?')[:80]}")
        lines.append(f"      {r.get('price', '?')}{rating}{reviews}{prime}")
        lines.append(f"      {r['url']}")
        lines.append("")
    return "\n".join(lines)


def cmd_search(args):
    results = search_amazon(args.query, n=args.n, min_rating=args.min_rating)
    log("+", f"{len(results)} results")

    if args.format == "json":
        out = json.dumps(results, indent=2, ensure_ascii=False)
    else:
        out = fmt_search_table(results)

    if args.output:
        with open(args.output, "w") as f: f.write(out)
        log("+", f"written to {args.output}")
    else:
        print(out)


# ===== CATEGORY BROWSING =====

def browse_category(target, n=20, sort=None, min_price=None, max_price=None,
                    prime_only=False, min_rating=None):
    """browse Amazon category by node ID or URL with all filter flags"""
    sel = _load_selectors()
    urls = _load_urls()

    if target.startswith("http"):
        url = target
    elif target.isdigit():
        url = urls.get("category_browse", "https://www.amazon.com/s?rh=n%3A{node_id}").replace("{node_id}", target)
    else:
        url = f"https://www.amazon.com/s?rh=n%3A{target}"

    params = []
    if sort:
        sort_map = sel.get("category_sort_map", {})
        s_val = sort_map.get(sort, sort)
        params.append(f"s={s_val}")

    filter_p = sel.get("category_filter_params", {})
    if min_price is not None:
        params.append(f"{filter_p.get('min_price', 'low-price')}={int(min_price)}")
    if max_price is not None:
        params.append(f"{filter_p.get('max_price', 'high-price')}={int(max_price)}")
    if prime_only:
        params.append(f"rh={filter_p.get('prime_only', 'p_85=2470955011')}")
    if min_rating:
        rating_map = filter_p.get("rating_map", {})
        r_val = rating_map.get(str(min_rating))
        if r_val:
            params.append(f"rh=p_72%3A{r_val}")

    if params:
        sep = "&" if "?" in url else "?"
        url += sep + "&".join(params)

    log("~", f"browsing category: {url}")
    return search_amazon_raw(url, n=n)


def search_amazon_raw(url, n=20):
    """search/browse from a pre-built URL - reuses search extraction logic"""
    html = fetch(url)
    if not html:
        return []

    results = []
    seen = set()

    blocks = list(re.finditer(
        r'<div[^>]*data-asin="([A-Z0-9]{10})"[^>]*data-component-type="s-search-result"', html))

    for i, block in enumerate(blocks):
        asin = block.group(1)
        if asin in seen:
            continue
        seen.add(asin)

        start = block.start()
        end = blocks[i + 1].start() if i + 1 < len(blocks) else start + 10000
        chunk = html[start:end]

        if "puis-sponsored-label" in chunk[:5000] or ">Sponsored<" in chunk[:3000]:
            continue

        r = {"asin": asin, "url": f"https://www.amazon.com/dp/{asin}"}

        m = re.search(r'<h2[^>]*>(.*?)</h2>', chunk[:8000], re.DOTALL)
        if m:
            raw = re.sub(r'<[^>]{0,500}>', ' ', m.group(1))
            raw = re.sub(r'\s+', ' ', raw).strip()
            r["title"] = raw[:200] if len(raw) > 20 else None
        else:
            r["title"] = None

        r["price"] = None
        offscreens = re.findall(r'class="a-offscreen"[^>]*>([^<]+)', chunk[:8000])
        for os_val in offscreens:
            os_val = os_val.strip()
            if os_val.startswith('$') and not os_val.startswith('$0') and 'List' not in os_val:
                r["price"] = os_val
                break
        if not r["price"]:
            price_m = re.search(r'>\s*(\$\d[\d,]*\.?\d{0,2})\s*<', chunk[:12000])
            if price_m:
                r["price"] = price_m.group(1)

        m = re.search(r'class="a-icon-alt"[^>]*>(\d+\.?\d*)\s+out of\s+5', chunk[:8000])
        r["rating"] = float(m.group(1)) if m else None

        for rp in [r'aria-label="([\d,]+)"', r'<span[^>]*class="a-size-base[^"]*"[^>]*>([\d,]+)</span>']:
            m = re.search(rp, chunk[:8000])
            if m:
                r["reviews"] = m.group(1).replace(",", "")
                break
        else:
            r["reviews"] = None

        r["prime"] = "a-icon-prime" in chunk[:5000]

        if r["title"]:
            results.append(r)
            if len(results) >= n:
                break

    return results


def cmd_category(args):
    results = browse_category(
        args.target, n=args.n, sort=args.sort,
        min_price=args.min_price, max_price=args.max_price,
        prime_only=args.prime, min_rating=args.min_rating,
    )
    log("+", f"{len(results)} category results")

    if args.format == "json":
        out = json.dumps(results, indent=2, ensure_ascii=False)
    else:
        out = fmt_search_table(results)

    if args.output:
        with open(args.output, "w") as f: f.write(out)
        log("+", f"written to {args.output}")
    else:
        print(out)

