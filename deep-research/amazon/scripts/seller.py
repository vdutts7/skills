"""seller.py - Amazon seller storefront scraping"""

import json
import os
import re
import sys

from amazon import fetch, log, _strip, _REGISTRY_DIR


def _load_selectors():
    try:
        with open(os.path.join(_REGISTRY_DIR, "selectors", "seller.json")) as f:
            return json.load(f)
    except Exception:
        return {}


def _load_urls():
    try:
        with open(os.path.join(_REGISTRY_DIR, "urls.json")) as f:
            return json.load(f)
    except Exception:
        return {}


def blast_seller(seller_id, n=20):
    sel = _load_selectors()
    urls = _load_urls()

    profile_url = urls.get("seller_profile", "https://www.amazon.com/sp?seller={seller_id}").replace("{seller_id}", seller_id)
    products_url = urls.get("seller_products", "https://www.amazon.com/s?me={seller_id}").replace("{seller_id}", seller_id)

    log("~", f"fetching seller profile: {profile_url}")
    profile_html = fetch(profile_url)

    info = {"seller_id": seller_id}

    if profile_html:
        name_p = sel.get("seller_name", {}).get("pattern", r'id="seller-name"[^>]*>([^<]+)')
        m = re.search(name_p, profile_html)
        if not m:
            alt_p = sel.get("seller_name", {}).get("alt_pattern", r'id="sellerName"[^>]*>([^<]+)')
            m = re.search(alt_p, profile_html)
        info["name"] = _strip(m.group(1)) if m else None

        rating_p = sel.get("seller_rating", {}).get("pattern", r'(\d+)%\s+positive')
        m = re.search(rating_p, profile_html)
        info["positive_rating"] = f"{m.group(1)}%" if m else None

        feedback_p = sel.get("feedback_count", {}).get("pattern", r'([\d,]+)\s+(?:total )?ratings')
        m = re.search(feedback_p, profile_html)
        info["feedback_count"] = m.group(1).replace(",", "") if m else None

        biz_p = sel.get("business_name", {}).get("pattern", r'Business Name.*?<span[^>]*>(.*?)</span>')
        m = re.search(biz_p, profile_html, re.DOTALL)
        info["business_name"] = _strip(m.group(1)) if m else None

        addr_p = sel.get("business_address", {}).get("pattern", r'Business Address.*?<span[^>]*>(.*?)</span>')
        m = re.search(addr_p, profile_html, re.DOTALL)
        info["business_address"] = _strip(m.group(1)) if m else None

    log("~", f"fetching seller products: {products_url}")
    products_html = fetch(products_url)

    products = []
    if products_html:
        count_p = sel.get("product_count", {}).get("pattern", r'([\d,]+)\s+results')
        m = re.search(count_p, products_html)
        info["total_products"] = m.group(1).replace(",", "") if m else None

        blocks = list(re.finditer(
            r'<div[^>]*data-asin="([A-Z0-9]{10})"[^>]*data-component-type="s-search-result"', products_html))

        seen = set()
        for i, block in enumerate(blocks):
            asin = block.group(1)
            if asin in seen:
                continue
            seen.add(asin)

            start = block.start()
            end = blocks[i + 1].start() if i + 1 < len(blocks) else start + 10000
            chunk = products_html[start:end]

            product = {"asin": asin, "url": f"https://www.amazon.com/dp/{asin}"}

            m = re.search(r'<h2[^>]*>(.*?)</h2>', chunk[:8000], re.DOTALL)
            if m:
                raw = re.sub(r'<[^>]{0,500}>', ' ', m.group(1))
                product["title"] = re.sub(r'\s+', ' ', raw).strip()[:200]
            else:
                product["title"] = None

            offscreens = re.findall(r'class="a-offscreen"[^>]*>([^<]+)', chunk[:8000])
            product["price"] = None
            for os_val in offscreens:
                os_val = os_val.strip()
                if os_val.startswith('$') and not os_val.startswith('$0'):
                    product["price"] = os_val
                    break

            m = re.search(r'class="a-icon-alt"[^>]*>(\d+\.?\d*)\s+out of\s+5', chunk[:8000])
            product["rating"] = float(m.group(1)) if m else None

            if product.get("title"):
                products.append(product)
                if len(products) >= n:
                    break

    return {"info": info, "products": products}


def fmt_seller_table(data):
    info = data["info"]
    lines = ["  SELLER PROFILE", "  " + "=" * 60, ""]
    for label, key in [
        ("Seller ID", "seller_id"), ("Name", "name"),
        ("Rating", "positive_rating"), ("Feedback", "feedback_count"),
        ("Business", "business_name"), ("Address", "business_address"),
        ("Products", "total_products"),
    ]:
        val = info.get(key)
        if val:
            lines.append(f"  {label:<16} {val}")

    products = data["products"]
    if products:
        lines.extend(["", f"  PRODUCTS ({len(products)})", "  " + "-" * 40, ""])
        for i, p in enumerate(products, 1):
            rating = f" {p['rating']}/5" if p.get("rating") else ""
            lines.append(f"  [{i}] {(p.get('title') or '?')[:65]}")
            lines.append(f"       {p.get('price', '?')}{rating}")
            lines.append(f"       {p['url']}")
            lines.append("")

    return "\n".join(lines)


def cmd_seller(args):
    data = blast_seller(args.seller_id, n=args.n)
    log("+", f"seller: {data['info'].get('name', '?')} - {len(data['products'])} products")

    if args.format == "json":
        out = json.dumps(data, indent=2, ensure_ascii=False)
    else:
        out = fmt_seller_table(data)

    if args.output:
        with open(args.output, "w") as f: f.write(out)
        log("+", f"written to {args.output}")
    else:
        print(out)
