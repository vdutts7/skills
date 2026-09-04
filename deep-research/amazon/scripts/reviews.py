"""reviews.py - Amazon review extraction + deep pagination"""

import json
import os
import re
import sys
import time
import random

from amazon import fetch, log, _strip, asin_from_input, _REGISTRY_DIR


def _load_selectors():
    try:
        with open(os.path.join(_REGISTRY_DIR, "selectors", "reviews.json")) as f:
            return json.load(f)
    except Exception:
        return {}


def _load_urls():
    try:
        with open(os.path.join(_REGISTRY_DIR, "urls.json")) as f:
            return json.load(f)
    except Exception:
        return {}


def rip_reviews(html, url):
    """extract inline reviews from product page"""
    reviews = []
    blocks = re.split(r'data-hook="review"', html)
    for block in blocks[1:]:
        review = {}
        m = re.search(r'(\d+\.?\d*) out of 5 stars', block[:2000])
        review["stars"] = float(m.group(1)) if m else None
        m = re.search(r'data-hook="review(?:Title|title)"[^>]*>.*?<span[^>]*>(.*?)</span>', block[:3000], re.DOTALL)
        if m:
            review["title"] = _strip(m.group(1))
        m = re.search(r'data-hook="review-date"[^>]*>(.*?)</span>', block[:3000], re.DOTALL)
        if m:
            review["date"] = _strip(m.group(1))
        review["verified"] = "Verified Purchase" in block[:3000]
        m = re.search(r'class="a-profile-name"[^>]*>(.*?)</span>', block[:3000], re.DOTALL)
        review["author"] = _strip(m.group(1)) if m else None
        m = re.search(r'data-hook="reviewText"[^>]*>.*?<span[^>]*>(.*?)</span>', block[:10000], re.DOTALL)
        if not m:
            m = re.search(r'data-hook="review-body"[^>]*>.*?<span[^>]*>(.*?)</span>', block[:10000], re.DOTALL)
        review["body"] = _strip(m.group(1)) if m else None
        m = re.search(r'(\d+)\s+(?:people|person)\s+found\s+this\s+helpful', block[:5000])
        review["helpful"] = int(m.group(1)) if m else 0

        if review.get("title") or review.get("body"):
            reviews.append(review)

    return reviews


def fmt_reviews_table(reviews):
    lines = []
    for i, r in enumerate(reviews, 1):
        stars = "*" * int(r.get("stars", 0)) if r.get("stars") else "?"
        verified = " [VERIFIED]" if r.get("verified") else ""
        helpful = f" ({r['helpful']} helpful)" if r.get("helpful") else ""
        lines.append(f"--- Review {i} ---")
        lines.append(f"  {stars}{verified}{helpful}")
        lines.append(f"  {r.get('author', '?')} - {r.get('date', '?')}")
        if r.get("title"):
            lines.append(f"  {r['title']}")
        if r.get("body"):
            lines.append(f"  {r['body'][:500]}")
        lines.append("")
    return "\n".join(lines)


def cmd_reviews(args):
    asin, url = asin_from_input(args.target)
    if not asin:
        log("x", f"can't parse ASIN from: {args.target}")
        sys.exit(1)
    log("~", f"fetching reviews from product page: {url}")
    html = fetch(url)
    if not html:
        sys.exit(1)
    reviews = rip_reviews(html, url)
    log("+", f"{len(reviews)} reviews extracted")

    if args.format == "json":
        out = json.dumps(reviews, indent=2, ensure_ascii=False)
    else:
        out = fmt_reviews_table(reviews)

    if args.output:
        with open(args.output, "w") as f: f.write(out)
        log("+", f"written to {args.output}")
    else:
        print(out)


# ===== REVIEW DEEP - PAGINATED WITH FILTERS =====

def blast_reviews_deep(asin, pages=5, star=None, verified=False, sort="helpful"):
    """paginated review extraction from dedicated review pages with filters"""
    sel = _load_selectors()
    urls = _load_urls()

    url_tpl = urls.get("reviews_filtered",
        "https://www.amazon.com/product-reviews/{asin}/?pageNumber={page}&filterByStar={star}&reviewerType={reviewer_type}&sortBy={sort}")

    star_filter = sel.get("star_filter_map", {}).get(star, "") if star else ""
    reviewer_type = sel.get("reviewer_type_map", {}).get("verified" if verified else "all", "all_reviews")
    sort_val = sel.get("sort_map", {}).get(sort, sort)

    all_reviews = []

    for page_num in range(1, pages + 1):
        url = (url_tpl
            .replace("{asin}", asin)
            .replace("{page}", str(page_num))
            .replace("{star}", star_filter)
            .replace("{reviewer_type}", reviewer_type)
            .replace("{sort}", sort_val))

        log("~", f"review page {page_num}/{pages}: {asin}")
        html = fetch(url)
        if not html:
            log("x", f"failed to fetch review page {page_num}")
            break

        page_reviews = rip_reviews(html, url)
        if not page_reviews:
            log("+", f"no more reviews after page {page_num - 1}")
            break

        all_reviews.extend(page_reviews)
        log("+", f"page {page_num}: {len(page_reviews)} reviews ({len(all_reviews)} total)")

        if page_num < pages:
            time.sleep(random.uniform(1.0, 2.5))

    return all_reviews


def cmd_review_deep(args):
    asin, _ = asin_from_input(args.target)
    if not asin:
        log("x", f"can't parse ASIN from: {args.target}")
        sys.exit(1)

    reviews = blast_reviews_deep(
        asin, pages=args.pages, star=args.star,
        verified=args.verified, sort=args.sort,
    )
    log("+", f"{len(reviews)} total reviews extracted")

    if args.format == "json":
        out = json.dumps(reviews, indent=2, ensure_ascii=False)
    else:
        out = fmt_reviews_table(reviews)

    if args.output:
        with open(args.output, "w") as f: f.write(out)
        log("+", f"written to {args.output}")
    else:
        print(out)
