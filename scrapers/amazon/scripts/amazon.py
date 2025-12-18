#!/usr/bin/env python3
"""amazon - unified Amazon product intelligence CLI
TLS-impersonated. no auth. no browser.

usage:
    amazon rip <ASIN|URL> [--format json|csv|table]
    amazon search <query> [--n 10] [--min-rating 4.0]
    amazon reviews <ASIN|URL> [--format json|table]
    amazon review-deep <ASIN|URL> [--pages 5] [--star five_star] [--sort recent]
    amazon category <node_id|URL> [--n 20] [--sort price-asc]
    amazon bestsellers [dept] [--feed best|new|movers|wished|gifted]
    amazon deals [--n 20]
    amazon seller <seller_id> [--n 20]
    amazon variations <ASIN|URL>
    amazon harvest <URL> [--pages N]
    amazon batch <file> [--format json|csv|table] [--delay 1.5]
    amazon endpoints refresh [--root DIR]
    amazon endpoints list [--pattern STR] [--all-hosts]
    amazon twister <ASIN|URL> [--format raw|json]
    amazon track add <ASIN> [--label name]
    amazon track check [--asin ASIN]
    amazon track history <ASIN>
"""

import argparse
import csv
import io
import json
import os
import random
import re
import sys
import time

try:
    from curl_cffi import requests as cffi_req
    HAS_CFFI = True
except ImportError:
    HAS_CFFI = False
    from urllib.request import urlopen, Request

from urllib.parse import urlparse

# --- frozen profile: extracted from a real browser HAR ---
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_REGISTRY_DIR = os.path.join(_SCRIPT_DIR, "..", "registry")
_FROZEN_PATH = os.path.join(_REGISTRY_DIR, "frozen-profile.json")
_FROZEN = None


def _load_frozen():
    global _FROZEN
    if _FROZEN is not None:
        return _FROZEN
    try:
        with open(_FROZEN_PATH) as f:
            _FROZEN = json.load(f)
    except Exception:
        _FROZEN = {}
    return _FROZEN


_IMPERSONATE = "chrome131"

_HEADERS = {
    "Upgrade-Insecure-Requests": "1",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Cache-Control": "max-age=0",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "sec-ch-ua": '"Chromium";v="131", "Not_A Brand";v="24", "Google Chrome";v="131"',
    "sec-ch-ua-full-version-list": '"Chromium";v="131.0.6778.204", "Not_A Brand";v="24.0.0.0", "Google Chrome";v="131.0.6778.204"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-ch-viewport-height": "900",
    "sec-ch-viewport-width": "1440",
    "sec-ch-device-memory": "8",
    "sec-ch-dpr": "2",
    "device-memory": "8",
    "downlink": "10",
    "dpr": "2",
    "ect": "4g",
    "rtt": "50",
    "viewport-width": "1440",
}

CAPTCHA_MARKERS = [
    "api-services-support@amazon.com",
    "Sorry, we just need to make sure",
    "Enter the characters you see below",
    "To discuss automated access to Amazon data",
    "Type the characters you see in this image",
]

_session = None


def _get_session():
    """single persistent session - consistent TLS fingerprint + cookie jar"""
    global _session
    if _session is None:
        frozen = _load_frozen()
        imp = frozen.get("impersonate", _IMPERSONATE)
        _session = cffi_req.Session(impersonate=imp)
    return _session


def _reset_session():
    global _session
    _session = None


def _get_headers():
    """load headers from frozen profile, fall back to hardcoded"""
    frozen = _load_frozen()
    if frozen and "headers" in frozen:
        return dict(frozen["headers"])
    return dict(_HEADERS)


def log(emoji, msg):
    print(f"{emoji} {msg}", file=sys.stderr)


def _is_captcha(html):
    if len(html) > 50000:
        return False
    for marker in CAPTCHA_MARKERS:
        if marker in html:
            return True
    return False


def _is_captcha_ajax(html):
    """Small AJAX/HTML fragments must not trip on generic PDP strings (false positives)."""
    if not html:
        return True
    if len(html) > 250000:
        return False
    needles = (
        "validateCaptcha",
        "[redacted]-captcha-verify",
        "captchacharacters",
        "api-services-support@amazon.com",
        "Enter the characters you see below",
        "Type the characters you see in this image",
        "Sorry, we just need to make sure",
    )
    return any(n in html for n in needles)


def fetch(url, retries=5, *, referer=None, xhr=False, lax_captcha=False):
    """Fetch URL. xhr=True: same-origin AJAX headers. lax_captcha: use AJAX captcha heuristics (small fragments)."""
    for attempt in range(retries):
        try:
            headers = dict(_get_headers())
            if xhr:
                headers["Accept"] = "*/*"
                headers["Sec-Fetch-Dest"] = "empty"
                headers["Sec-Fetch-Mode"] = "cors"
                headers["Sec-Fetch-Site"] = "same-origin"
                headers.pop("Upgrade-Insecure-Requests", None)
                if referer:
                    headers["Referer"] = referer
                    try:
                        pr = urlparse(referer)
                        if pr.scheme and pr.netloc:
                            headers["Origin"] = f"{pr.scheme}://{pr.netloc}"
                    except Exception:
                        pass
            elif referer:
                headers["Referer"] = referer

            if HAS_CFFI:
                sess = _get_session()
                resp = sess.get(url, headers=headers, timeout=15, allow_redirects=True)
                html = resp.text
            else:
                from urllib.request import urlopen, Request
                req = Request(url, headers=headers)
                with urlopen(req, timeout=15) as resp:
                    html = resp.read().decode("utf-8", errors="replace")

            use_ajax_check = xhr or lax_captcha
            blocked = _is_captcha_ajax(html) if use_ajax_check else _is_captcha(html)
            if blocked:
                backoff = random.uniform(2, 5) * (2 ** attempt)
                log("~", f"captcha, backoff {backoff:.1f}s ({attempt+1}/{retries})")
                _reset_session()
                time.sleep(backoff)
                continue
            return html
        except Exception as e:
            if attempt < retries - 1:
                _reset_session()
                time.sleep(random.uniform(1, 3) * (attempt + 1))
            else:
                log("x", f"fetch failed: {url} - {e}")
                return None
    log("x", f"captcha blocked after {retries} attempts")
    return None


def fetch_ajax(url, referer=None, retries=5):
    """Same-origin XHR-style GET (twister, cart fragments, etc.)."""
    return fetch(url, retries=retries, referer=referer, xhr=True)


def _strip(html_frag):
    """fast tag stripper - avoids catastrophic backtracking"""
    if not html_frag:
        return ""
    t = re.sub(r"<(?:script|style)[^>]*>.*?</(?:script|style)>", " ", html_frag, flags=re.DOTALL | re.I)
    t = re.sub(r"<[^>]{0,500}>", " ", t)
    for old, new in [("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'), ("&lrm;", ""), ("&rlm;", ""), ("&#39;", "'")]:
        t = t.replace(old, new)
    t = re.sub(r"&#\d+;", "", t)
    t = re.sub(r"&\w+;", "", t)
    return re.sub(r"\s+", " ", t).strip()


def _section(html, start_pat, end_pat=None, max_len=50000):
    """extract a section of HTML to avoid running regex on full 1.4MB page"""
    m = re.search(start_pat, html)
    if not m:
        return ""
    s = m.start()
    if end_pat:
        m2 = re.search(end_pat, html[s + 100:])
        e = s + 100 + m2.start() if m2 else s + max_len
    else:
        e = s + max_len
    return html[s:min(e, len(html))]


def asin_from_input(target):
    """resolve ASIN or URL to (asin, url)"""
    target = target.strip()
    if re.match(r"^[A-Z0-9]{10}$", target):
        return target, f"https://www.amazon.com/dp/{target}"
    m = re.search(r"/dp/([A-Z0-9]{10})", target) or re.search(r"/gp/product/([A-Z0-9]{10})", target)
    if m:
        return m.group(1), target
    return None, target


def load_urls():
    """load URL patterns from registry"""
    try:
        with open(os.path.join(_REGISTRY_DIR, "urls.json")) as f:
            return json.load(f)
    except Exception:
        return {}


def harvest_asins(html):
    """extract all ASINs from any Amazon page"""
    asins = []
    seen = set()
    for pat in [r'data-asin="([A-Z0-9]{10})"', r'/dp/([A-Z0-9]{10})', r'/gp/product/([A-Z0-9]{10})']:
        for m in re.finditer(pat, html):
            a = m.group(1)
            if a not in seen:
                seen.add(a)
                asins.append(a)
    return asins


def find_next_page(html):
    m = re.search(r'class="s-pagination-next"[^>]*href="([^"]+)"', html)
    if not m:
        m = re.search(r'<li class="a-last">\s*<a[^>]*href="([^"]+)"', html)
    if m:
        href = m.group(1).replace("&amp;", "&")
        return f"https://www.amazon.com{href}" if href.startswith("/") else href
    return None


def cmd_harvest(args):
    url = args.target.strip()
    all_asins = []
    seen = set()
    for page in range(1, args.pages + 1):
        log("~", f"harvest page {page}/{args.pages}")
        html = fetch(url)
        if not html:
            break
        for a in harvest_asins(html):
            if a not in seen:
                seen.add(a)
                all_asins.append(a)
        log("+", f"page {page}: {len(seen)} ASINs total")
        if page < args.pages:
            nxt = find_next_page(html)
            if not nxt:
                log("+", f"no more pages after {page}")
                break
            url = nxt
            time.sleep(random.uniform(0.8, 2.0))

    out = "\n".join(all_asins) + "\n"
    if args.output:
        with open(args.output, "w") as f: f.write(out)
        log("+", f"{len(all_asins)} ASINs -> {args.output}")
    else:
        sys.stdout.write(out)


def cmd_batch(args):
    from product import rip_product, fmt_table, fmt_csv_flat

    with open(args.file, "r") as f:
        targets = [l.strip() for l in f if l.strip() and not l.startswith("#")]
    log("~", f"batch: {len(targets)} targets, {args.delay}s delay")

    all_data = []
    for i, target in enumerate(targets, 1):
        asin, url = asin_from_input(target)
        if not asin:
            log("x", f"[{i}/{len(targets)}] invalid: {target}")
            continue
        html = fetch(url)
        if not html:
            log("x", f"[{i}/{len(targets)}] fetch failed: {asin}")
            continue
        data = rip_product(html, url)
        filled = sum(1 for v in data.values() if v and v != [] and v != {})
        title = (data.get("title") or "?")[:50]
        log("+", f"[{i}/{len(targets)}] {asin} {filled}/22 {title}")
        all_data.append(data)
        if i < len(targets):
            time.sleep(random.uniform(args.delay * 0.5, args.delay * 1.5))

    if args.format == "json":
        out = json.dumps(all_data, indent=2, ensure_ascii=False)
    elif args.format == "jsonl":
        out = "\n".join(json.dumps(d, ensure_ascii=False) for d in all_data)
    elif args.format == "csv":
        if all_data:
            rows = []
            all_keys = set()
            for d in all_data:
                flat = {}
                for k, v in d.items():
                    if isinstance(v, list):
                        flat[k] = " | ".join(str(x) for x in v) if v and not isinstance(v[0], dict) else json.dumps(v, ensure_ascii=False)
                    elif isinstance(v, dict):
                        for sk, sv in v.items():
                            flat[f"{k}_{sk}"] = json.dumps(sv, ensure_ascii=False) if isinstance(sv, (list, dict)) else sv
                    else:
                        flat[k] = v
                rows.append(flat)
                all_keys.update(flat.keys())
            buf = io.StringIO()
            w = csv.DictWriter(buf, fieldnames=sorted(all_keys), extrasaction="ignore")
            w.writeheader()
            for r in rows: w.writerow(r)
            out = buf.getvalue()
        else:
            out = ""
    else:
        out = "\n\n".join(fmt_table(d) for d in all_data)

    if args.output:
        with open(args.output, "w") as f: f.write(out)
        log("+", f"written to {args.output}")
    else:
        print(out)

    log("+" if len(all_data) == len(targets) else "~", f"batch: {len(all_data)}/{len(targets)} succeeded")


def main():
    p = argparse.ArgumentParser(description="amazon - Amazon product intelligence CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    rp = sub.add_parser("rip", help="extract product data")
    rp.add_argument("target", help="ASIN or Amazon URL")
    rp.add_argument("-f", "--format", choices=["json", "csv", "table"], default="table")
    rp.add_argument("-o", "--output", help="output file")

    sp = sub.add_parser("search", help="search products")
    sp.add_argument("query", help="search terms")
    sp.add_argument("-n", type=int, default=10, help="max results")
    sp.add_argument("--min-rating", type=float, default=0.0, help="minimum rating filter")
    sp.add_argument("-f", "--format", choices=["json", "table"], default="table")
    sp.add_argument("-o", "--output", help="output file")

    rv = sub.add_parser("reviews", help="extract reviews from product page")
    rv.add_argument("target", help="ASIN or Amazon URL")
    rv.add_argument("-f", "--format", choices=["json", "table"], default="table")
    rv.add_argument("-o", "--output", help="output file")

    rd = sub.add_parser("review-deep", help="paginated review extraction with filters")
    rd.add_argument("target", help="ASIN or Amazon URL")
    rd.add_argument("--pages", type=int, default=5, help="max pages to fetch")
    rd.add_argument("--star", choices=["five_star", "four_star", "three_star", "two_star", "one_star", "positive", "critical"], help="star filter")
    rd.add_argument("--verified", action="store_true", help="verified purchases only")
    rd.add_argument("--sort", choices=["recent", "helpful"], default="helpful", help="sort order")
    rd.add_argument("-f", "--format", choices=["json", "table"], default="table")
    rd.add_argument("-o", "--output", help="output file")

    cp = sub.add_parser("category", help="browse category by node ID")
    cp.add_argument("target", help="category node ID or Amazon category URL")
    cp.add_argument("-n", type=int, default=20, help="max results")
    cp.add_argument("--sort", choices=["price-asc", "price-desc", "rating", "newest", "bestselling"], help="sort order")
    cp.add_argument("--min-price", type=float, help="minimum price")
    cp.add_argument("--max-price", type=float, help="maximum price")
    cp.add_argument("--prime", action="store_true", help="Prime eligible only")
    cp.add_argument("--min-rating", type=int, choices=[1, 2, 3, 4], help="minimum star rating")
    cp.add_argument("-f", "--format", choices=["json", "table"], default="table")
    cp.add_argument("-o", "--output", help="output file")

    bs = sub.add_parser("bestsellers", help="browse bestseller/new-release/movers feeds")
    bs.add_argument("dept", nargs="?", default="", help="department slug (e.g. electronics)")
    bs.add_argument("--feed", choices=["best", "new", "movers", "wished", "gifted"], default="best", help="feed type")
    bs.add_argument("-n", type=int, default=20, help="max items")
    bs.add_argument("-f", "--format", choices=["json", "table"], default="table")
    bs.add_argument("-o", "--output", help="output file")

    dp = sub.add_parser("deals", help="discover active deals")
    dp.add_argument("-n", type=int, default=20, help="max deals")
    dp.add_argument("-f", "--format", choices=["json", "table"], default="table")
    dp.add_argument("-o", "--output", help="output file")

    sl = sub.add_parser("seller", help="scrape seller storefront")
    sl.add_argument("seller_id", help="Amazon seller ID")
    sl.add_argument("-n", type=int, default=20, help="max products")
    sl.add_argument("-f", "--format", choices=["json", "table"], default="table")
    sl.add_argument("-o", "--output", help="output file")

    vr = sub.add_parser("variations", help="enumerate product variations")
    vr.add_argument("target", help="ASIN or Amazon URL")
    vr.add_argument("-f", "--format", choices=["json", "table"], default="table")
    vr.add_argument("-o", "--output", help="output file")

    hp = sub.add_parser("harvest", help="harvest ASINs from any page")
    hp.add_argument("target", help="Amazon URL")
    hp.add_argument("--pages", type=int, default=1, help="pages to crawl")
    hp.add_argument("-o", "--output", help="output file")

    bp = sub.add_parser("batch", help="batch rip from ASIN/URL list file")
    bp.add_argument("file", help="file with one ASIN/URL per line")
    bp.add_argument("-f", "--format", choices=["json", "jsonl", "csv", "table"], default="table")
    bp.add_argument("-o", "--output", help="output file")
    bp.add_argument("-d", "--delay", type=float, default=1.5, help="delay between requests")

    tp = sub.add_parser("track", help="price tracking")
    track_sub = tp.add_subparsers(dest="track_cmd", required=True)
    ta = track_sub.add_parser("add", help="add ASIN to watchlist")
    ta.add_argument("target", help="ASIN or URL")
    ta.add_argument("--label", help="friendly label")
    tc = track_sub.add_parser("check", help="check prices on watchlist")
    tc.add_argument("--asin", help="check specific ASIN only")
    tc.add_argument("-f", "--format", choices=["json", "table"], default="table")
    th = track_sub.add_parser("history", help="show price history")
    th.add_argument("target", help="ASIN or URL")
    th.add_argument("-f", "--format", choices=["json", "table"], default="table")

    ep = sub.add_parser("endpoints", help="mine XHR URLs from a local HAR folder → registry/endpoints.json")
    eps = ep.add_subparsers(dest="endpoints_cmd", required=True)
    er = eps.add_parser("refresh", help="merge report.json + raw.har from --root into registry/endpoints.json")
    er.add_argument("--root", default="./captures", help="folder of HAR capture directories")
    el = eps.add_parser("list", help="show harvested endpoints")
    el.add_argument("--pattern", default="", help="filter path/id substring")
    el.add_argument("--all-hosts", action="store_true", help="include non-www *.amazon.com hosts")
    el.add_argument("-f", "--format", choices=["text", "json"], default="text")

    tw = sub.add_parser("twister", help="fetch twister dimension-slot AJAX (variation fragment)")
    tw.add_argument("target", help="ASIN or PDP URL")
    tw.add_argument("-f", "--format", choices=["raw", "json"], default="raw")
    tw.add_argument("-o", "--output", help="output file")

    args = p.parse_args()

    cmd_map = {
        "rip": lambda: __import__("product").cmd_rip(args),
        "search": lambda: __import__("search").cmd_search(args),
        "reviews": lambda: __import__("reviews").cmd_reviews(args),
        "review-deep": lambda: __import__("reviews").cmd_review_deep(args),
        "category": lambda: __import__("search").cmd_category(args),
        "bestsellers": lambda: __import__("feeds").cmd_bestsellers(args),
        "deals": lambda: __import__("feeds").cmd_deals(args),
        "seller": lambda: __import__("seller").cmd_seller(args),
        "variations": lambda: __import__("product").cmd_variations(args),
        "harvest": lambda: cmd_harvest(args),
        "batch": lambda: cmd_batch(args),
        "track": lambda: __import__("track").cmd_track(args),
        "endpoints": lambda: __import__("endpoints").cmd_endpoints(args),
        "twister": lambda: __import__("twister_api").cmd_twister(args),
    }

    handler = cmd_map.get(args.cmd)
    if handler:
        handler()
    else:
        p.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

