"""product.py - Amazon product rip + variation enumeration"""

import csv
import io
import json
import os
import random
import re
import sys
import time

from amazon import fetch, log, _strip, _section, asin_from_input, _REGISTRY_DIR


def rip_product(html, url):
    """extract all product data from HTML. single-pass, sectioned for speed."""
    d = {"url": url}

    m = re.search(r"/dp/([A-Z0-9]{10})", url) or re.search(r"/gp/product/([A-Z0-9]{10})", url)
    d["asin"] = m.group(1) if m else None
    if not d["asin"]:
        m = re.search(r'"ASIN"\s*:\s*"([A-Z0-9]{10})"', html[:50000])
        d["asin"] = m.group(1) if m else None

    m = re.search(r'"parentAsin"\s*:\s*"([A-Z0-9]{10})"', html)
    d["parent_asin"] = m.group(1) if m else None

    sec = _section(html, r'id="productTitle"', max_len=2000)
    m = re.search(r'id="productTitle"[^>]*>(.*?)</span>', sec, re.DOTALL)
    if not m:
        m = re.search(r"<title>(.*?)</title>", html[:10000], re.DOTALL)
        if m:
            d["title"] = re.sub(r"\s*:?\s*Amazon\.com.*$", "", _strip(m.group(1)))
        else:
            d["title"] = None
    else:
        d["title"] = _strip(m.group(1))

    sec = _section(html, r'id="bylineInfo"', max_len=2000)
    m = re.search(r'id="bylineInfo"[^>]*>(.*?)</a>', sec, re.DOTALL)
    if m:
        t = _strip(m.group(1))
        d["brand"] = re.sub(r"\s*Store$", "", re.sub(r"^(Visit the |Brand:\s*)", "", t))
    else:
        d["brand"] = None

    m = re.search(r'href="(/stores/[^"]+)"', sec)
    d["brand_store_url"] = f"https://www.amazon.com{m.group(1).split('&')[0]}" if m else None

    price_sec = _section(html, r'id="corePrice|id="corePriceDisplay|id="apex_desktop|class="a-price"', max_len=10000)
    if not price_sec:
        price_sec = html
    m = re.search(r'class="a-price-whole"[^>]*>(\d+)<.*?class="a-price-fraction"[^>]*>(\d+)<', price_sec, re.DOTALL)
    if m:
        d["price"] = f"${m.group(1)}.{m.group(2)}"
    else:
        m = re.search(r'"priceAmount":\s*([\d.]+)', price_sec)
        d["price"] = f"${m.group(1)}" if m else None

    m = re.search(r'class="a-text-price"[^>]*>.*?class="a-offscreen"[^>]*>\s*\$?([\d,]+\.?\d*)', price_sec, re.DOTALL)
    d["list_price"] = f"${m.group(1)}" if m else None

    savings = {}
    m = re.search(r"savingsPercentage.*?(\d+)%", price_sec)
    if m: savings["percent"] = f"{m.group(1)}%"
    m = re.search(r"savingsAmount.*?\$?([\d,.]+)", price_sec)
    if m: savings["amount"] = f"${m.group(1)}"
    d["savings"] = savings or None

    sec = _section(html, r"Save.*?with\s+coupon", max_len=1000)
    m = re.search(r"Save.*?(\d+%?)\s+with\s+coupon", sec, re.I)
    d["coupon"] = m.group(1) if m else None

    sec = _section(html, r"out of\s+5\s+stars", max_len=1000)
    m = re.search(r"(\d+\.?\d*)\s+out of\s+5\s+stars", sec)
    d["rating"] = m.group(1) if m else None

    sec = _section(html, r'id="acrCustomerReviewText"', max_len=1000)
    m = re.search(r'id="acrCustomerReviewText"[^>]*>\s*\(?([\d,]+)\)?\s*(?:ratings|reviews)?', sec)
    d["review_count"] = m.group(1).replace(",", "") if m else None

    m = re.search(r"([\d,]+)\s+answered\s+question", html)
    d["answered_questions"] = m.group(1).replace(",", "") if m else None

    sec = _section(html, r'id="availability"', max_len=2000)
    m = re.search(r'id="availability"[^>]*>(.*?)</div>', sec, re.DOTALL)
    d["availability"] = _strip(m.group(1)) if m else None

    delivery = {}
    sec = _section(html, r"delivery", max_len=5000)
    m = re.search(r"Prime.*?delivery.*?(\w+day,\s+\w+\s+\d+)", sec, re.DOTALL)
    if m: delivery["prime"] = m.group(1)
    m = re.search(r"FREE delivery\s+(\w+day,\s+\w+\s+\d+)", sec)
    if m: delivery["free"] = m.group(1)
    d["delivery"] = delivery or None

    merchant = {}
    sec = _section(html, r"tabular-buybox|Ships from|Sold by", max_len=5000)
    spans = re.findall(r'tabular-buybox-text[^>]*>\s*(?:<[^>]*>\s*)*(.*?)\s*</(?:span|a)', sec, re.DOTALL)
    clean = [_strip(s) for s in spans if _strip(s)]
    if len(clean) >= 4:
        merchant["ships_from"] = clean[1]
        merchant["sold_by"] = clean[3]
    d["merchant"] = merchant or None

    sec = _section(html, r'id="feature-bullets"', max_len=20000)
    items = re.findall(r'<span class="a-list-item"[^>]*>(.*?)</span>', sec, re.DOTALL)
    d["features"] = [_strip(i) for i in items if _strip(i) and len(_strip(i)) > 3 and "see more" not in _strip(i).lower()]

    sec = _section(html, r'id="wayfinding-breadcrumbs', max_len=5000)
    links = re.findall(r"<a[^>]*>(.*?)</a>", sec, re.DOTALL)
    d["categories"] = [_strip(l) for l in links if _strip(l)]

    imgs = re.findall(r'"hiRes"\s*:\s*"(https://[^"]+)"', html)
    if not imgs:
        imgs = re.findall(r'"large"\s*:\s*"(https://[^"]+)"', html)
    d["images"] = list(dict.fromkeys(imgs))

    details = {}
    sec = _section(html, r'id="productDetails|id="detailBullets|class="a-keyvalue"', max_len=30000)
    rows = re.findall(r'<th[^>]*class="a-color-secondary[^"]*"[^>]*>(.*?)</th>\s*<td[^>]*>(.*?)</td>', sec, re.DOTALL)
    for k, v in rows:
        key, val = _strip(k), _strip(v)
        if key and val and len(key) < 80:
            val = re.sub(r"\s*(var |P\.when|function).*", "", val, flags=re.DOTALL).strip()
            if val and len(val) < 500:
                details[key] = val
    d["tech_details"] = details

    bsr = []
    sec = _section(html, r"Best\s*Sellers?\s*Rank", max_len=5000)
    m = re.search(r'Best\s*Sellers?\s*Rank.*?#([\d,]+)\s+in\s+([^<\(]{3,60})', sec, re.DOTALL)
    if m:
        bsr.append({"rank": m.group(1).replace(",", ""), "category": m.group(2).strip()})
    subs = re.findall(r'#([\d,]+)\s+in\s+<a[^>]*>([^<]+)</a>', sec)
    for rank, cat in subs:
        bsr.append({"rank": rank.replace(",", ""), "category": cat.strip()})
    d["bestseller_rank"] = bsr or None

    variations = {}
    var_sec = _section(html, r'"variationDisplayLabels"|"variationValues"', max_len=20000)
    blocks = re.findall(r'"variationDisplayLabels"\s*:\s*\{([^}]+)\}', var_sec)
    if blocks:
        for k, v in re.findall(r'"(\w+)"\s*:\s*"([^"]+)"', blocks[0]):
            variations[k] = v
    dims = re.findall(r'"variationValues"\s*:\s*\{([^}]+)\}', var_sec)
    if dims:
        for k, v in re.findall(r'"(\w+)"\s*:\s*\[([^\]]+)\]', dims[0]):
            options = re.findall(r'"([^"]+)"', v)
            label = variations.get(k, k)
            variations[label] = options
    d["variations"] = variations or None

    return d


def fmt_table(data):
    lines = ["=" * 72]
    lines.append(f"  {data.get('title', 'N/A')}")
    lines.append("=" * 72 + "\n")

    for label, key in [
        ("ASIN", "asin"), ("Parent ASIN", "parent_asin"), ("Brand", "brand"),
        ("Price", "price"), ("List Price", "list_price"), ("Coupon", "coupon"),
        ("Rating", "rating"), ("Reviews", "review_count"),
        ("Q&A", "answered_questions"), ("Availability", "availability"),
    ]:
        val = data.get(key)
        if val:
            lines.append(f"  {label:<16} {val}")

    savings = data.get("savings")
    if savings:
        parts = [savings.get("amount", ""), f"({savings['percent']})" if "percent" in savings else ""]
        lines.append(f"  {'Savings':<16} {' '.join(p for p in parts if p)}")

    delivery = data.get("delivery")
    if delivery:
        for k, v in delivery.items():
            lines.append(f"  {k.title():<16} {v}")

    merchant = data.get("merchant")
    if merchant:
        for k, v in merchant.items():
            lines.append(f"  {k.replace('_',' ').title():<16} {v}")

    bsr = data.get("bestseller_rank")
    if bsr:
        for i, b in enumerate(bsr):
            label = "BSR" if i == 0 else ""
            lines.append(f"  {label:<16} #{b['rank']} in {b['category']}")

    cats = data.get("categories")
    if cats:
        lines.append(f"  {'Categories':<16} {' > '.join(cats)}")

    lines.append("")
    features = data.get("features")
    if features:
        lines.append("  FEATURES")
        lines.append("  " + "-" * 40)
        for f in features:
            lines.append(f"    * {f}")
        lines.append("")

    tech = data.get("tech_details")
    if tech:
        lines.append("  TECH DETAILS")
        lines.append("  " + "-" * 40)
        mk = max(len(k) for k in tech) if tech else 20
        for k, v in tech.items():
            lines.append(f"    {k:<{mk+2}} {v}")
        lines.append("")

    variations = data.get("variations")
    if variations:
        lines.append("  VARIATIONS")
        lines.append("  " + "-" * 40)
        for k, v in variations.items():
            if k.startswith("_"): continue
            if isinstance(v, list):
                lines.append(f"    {k}: {', '.join(v)}")
            else:
                lines.append(f"    {k}: {v}")
        lines.append("")

    imgs = data.get("images")
    if imgs:
        lines.append(f"  IMAGES ({len(imgs)})")
        lines.append("  " + "-" * 40)
        for i, img in enumerate(imgs, 1):
            lines.append(f"    [{i}] {img}")
        lines.append("")

    return "\n".join(lines)


def fmt_csv_flat(data):
    flat = {}
    for k, v in data.items():
        if isinstance(v, list):
            flat[k] = " | ".join(str(i) for i in v) if v and not isinstance(v[0], dict) else json.dumps(v, ensure_ascii=False)
        elif isinstance(v, dict):
            for sk, sv in v.items():
                flat[f"{k}_{sk}"] = json.dumps(sv, ensure_ascii=False) if isinstance(sv, (list, dict)) else sv
        else:
            flat[k] = v
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=flat.keys())
    w.writeheader()
    w.writerow(flat)
    return buf.getvalue()


def cmd_rip(args):
    asin, url = asin_from_input(args.target)
    if not asin:
        log("x", f"can't parse ASIN from: {args.target}")
        sys.exit(1)
    log("~", f"ripping {url}")
    html = fetch(url)
    if not html:
        sys.exit(1)
    data = rip_product(html, url)
    filled = sum(1 for v in data.values() if v and v != [] and v != {})
    log("+", f"extracted {filled}/{len(data)} fields")

    if args.format == "json":
        out = json.dumps(data, indent=2, ensure_ascii=False)
    elif args.format == "csv":
        out = fmt_csv_flat(data)
    else:
        out = fmt_table(data)

    if args.output:
        with open(args.output, "w") as f: f.write(out)
        log("+", f"written to {args.output}")
    else:
        print(out)


# ===== VARIATION ENUMERATION =====

def enumerate_variations(html, parent_asin):
    """resolve all child ASINs from variation data on product page"""
    variations = []

    asin_map_m = re.search(r'"dimensionValuesDisplayData"\s*:\s*\{(.*?)\}\s*[,}]', html, re.DOTALL)
    child_asins = set()

    if asin_map_m:
        for m in re.finditer(r'"([A-Z0-9]{10})"\s*:\s*\[', asin_map_m.group(1)):
            child_asins.add(m.group(1))

    a2a_m = re.search(r'"asin_to_asin_map"\s*:\s*\{(.*?)\}', html, re.DOTALL)
    if a2a_m:
        for m in re.finditer(r'"([A-Z0-9]{10})"\s*:\s*"([A-Z0-9]{10})"', a2a_m.group(1)):
            child_asins.add(m.group(1))
            child_asins.add(m.group(2))

    dim_labels = {}
    labels_m = re.search(r'"variationDisplayLabels"\s*:\s*\{([^}]+)\}', html)
    if labels_m:
        for k, v in re.findall(r'"(\w+)"\s*:\s*"([^"]+)"', labels_m.group(1)):
            dim_labels[k] = v

    dim_values = {}
    vals_m = re.search(r'"variationValues"\s*:\s*\{([^}]+)\}', html)
    if vals_m:
        for k, v in re.findall(r'"(\w+)"\s*:\s*\[([^\]]+)\]', vals_m.group(1)):
            options = re.findall(r'"([^"]+)"', v)
            label = dim_labels.get(k, k)
            dim_values[label] = options

    display_data = {}
    if asin_map_m:
        for m in re.finditer(r'"([A-Z0-9]{10})"\s*:\s*\[([^\]]*)\]', asin_map_m.group(1)):
            vals = re.findall(r'"([^"]+)"', m.group(2))
            display_data[m.group(1)] = vals

    for asin in sorted(child_asins):
        entry = {"asin": asin, "url": f"https://www.amazon.com/dp/{asin}"}
        if asin in display_data:
            dims = display_data[asin]
            dim_keys = list(dim_values.keys())
            for i, val in enumerate(dims):
                if i < len(dim_keys):
                    entry[dim_keys[i]] = val
        variations.append(entry)

    return {"parent_asin": parent_asin, "dimensions": dim_values, "children": variations}


def fmt_variations_table(data):
    lines = [f"  VARIATIONS for {data['parent_asin']}", "  " + "=" * 60, ""]

    dims = data.get("dimensions", {})
    if dims:
        for k, v in dims.items():
            lines.append(f"  {k}: {', '.join(v)}")
        lines.append("")

    children = data.get("children", [])
    lines.append(f"  {len(children)} child ASINs:")
    lines.append("  " + "-" * 40)
    for c in children:
        attrs = [f"{k}={v}" for k, v in c.items() if k not in ("asin", "url")]
        attr_str = f" ({', '.join(attrs)})" if attrs else ""
        lines.append(f"    {c['asin']}{attr_str}")

    return "\n".join(lines)


def cmd_variations(args):
    asin, url = asin_from_input(args.target)
    if not asin:
        log("x", f"can't parse ASIN from: {args.target}")
        sys.exit(1)
    log("~", f"enumerating variations for {asin}")
    html = fetch(url)
    if not html:
        sys.exit(1)
    data = enumerate_variations(html, asin)
    log("+", f"{len(data['children'])} child ASINs found")

    if args.format == "json":
        out = json.dumps(data, indent=2, ensure_ascii=False)
    else:
        out = fmt_variations_table(data)

    if args.output:
        with open(args.output, "w") as f: f.write(out)
        log("+", f"written to {args.output}")
    else:
        print(out)

