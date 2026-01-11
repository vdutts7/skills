#!/usr/bin/env python3
"""
redfin-stingray - Redfin listing scraper via public Stingray API.

Usage:
  redfin-stingray.py [options]

Options:
  --market MARKET    Single market code (e.g. nyc, sfar, socal)
  --all-markets      Scrape all known markets
  --status STATUS    1=active (default), 9=sold
  --max-pages N      Max pages per market (default: 20)
  --num-homes N      Listings per page (default: 350, max tested: 350)
  --output DIR       Output directory (default: ./redfin-data)
  --format FORMAT    json|csv|both (default: json)
  --delay SECS       Delay between requests (default: 1.5)
  --resume           Resume from .state.json (default: true)
  --dry-run          Print URLs without fetching

"""

import argparse
import json
import os
import sys
import time
import csv
import io
import signal
import tempfile
import shutil
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# --- constants ---

BASE_URL = "https://www.redfin.com/stingray/api"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
PREFIX = "{}&&"

MARKETS = {
    "nyc":   {"region_id": 30749, "region_type": 6, "city": "New York"},
    "sfar":  {"region_id": 17534, "region_type": 6, "city": "San Francisco"},
    "socal": {"region_id": 11203, "region_type": 6, "city": "Los Angeles"},
    "chi":   {"region_id": 29470, "region_type": 6, "city": "Chicago"},
    "bos":   {"region_id": 1826,  "region_type": 6, "city": "Boston"},
    "mia":   {"region_id": 11458, "region_type": 6, "city": "Miami"},
    "sea":   {"region_id": 16163, "region_type": 6, "city": "Seattle"},
    "atl":   {"region_id": 10313, "region_type": 6, "city": "Atlanta"},
    "dal":   {"region_id": 30794, "region_type": 6, "city": "Dallas"},
    "den":   {"region_id": 11093, "region_type": 6, "city": "Denver"},
    "aus":   {"region_id": 30818, "region_type": 6, "city": "Austin"},
}

# --- state management  ---

class State:
    def __init__(self, path):
        self.path = Path(path)
        self.data = {"completed": [], "failed": [], "in_progress": None, "last_run": None, "consecutive_errors": 0, "total_listings": 0}
        if self.path.exists():
            with open(self.path) as f:
                self.data.update(json.load(f))

    def save(self):
        tmp = self.path.with_suffix('.tmp')
        with open(tmp, 'w') as f:
            json.dump(self.data, f, indent=2)
        tmp.rename(self.path)  #  atomic

    def is_completed(self, key):
        return key in self.data["completed"]

    def mark_completed(self, key, count=0):
        if key not in self.data["completed"]:
            self.data["completed"].append(key)
        self.data["in_progress"] = None
        self.data["total_listings"] += count
        self.data["consecutive_errors"] = 0
        self.save()

    def mark_failed(self, key, reason=""):
        self.data["failed"].append({"key": key, "reason": reason, "ts": now_iso()})
        self.data["consecutive_errors"] += 1
        self.data["in_progress"] = None
        self.save()

    def mark_in_progress(self, key):
        self.data["in_progress"] = key
        self.data["last_run"] = now_iso()
        self.save()

# --- helpers ---

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", file=sys.stderr)

def strip_prefix(raw):
    if raw.startswith(PREFIX):
        return raw[len(PREFIX):]
    return raw

def build_url(market_code, page=1, num_homes=350, status=1):
    m = MARKETS[market_code]
    return (
        f"{BASE_URL}/gis?al=1"
        f"&market={market_code}"
        f"&num_homes={num_homes}"
        f"&page_number={page}"
        f"&region_id={m['region_id']}"
        f"&region_type={m['region_type']}"
        f"&sf=1,2,3,5,6,7"
        f"&status={status}"
        f"&uipt=1,2,3,4,5,6,7,8"
        f"&v=8"
        f"&ord=redfin-recommended-asc"
    )

def build_csv_url(market_code, num_homes=350, status=1):
    m = MARKETS[market_code]
    return (
        f"{BASE_URL}/gis-csv?al=1"
        f"&market={market_code}"
        f"&num_homes={num_homes}"
        f"&region_id={m['region_id']}"
        f"&region_type={m['region_type']}"
        f"&sf=1,2,3,5,6,7"
        f"&status={status}"
        f"&uipt=1,2,3,4,5,6,7,8"
        f"&v=8"
    )

# --- fetch with backoff  ---

def fetch(url, max_retries=5):
    delay = 1.0
    for attempt in range(max_retries):
        try:
            req = Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip, deflate"})
            resp = urlopen(req, timeout=30)
            data = resp.read()
            if resp.headers.get('Content-Encoding') == 'gzip':
                import gzip
                data = gzip.decompress(data)
            return data.decode('utf-8')
        except HTTPError as e:
            if e.code in (429, 503):
                log(f"  retry {attempt+1}/{max_retries} (HTTP {e.code}), waiting {delay:.1f}s")
                time.sleep(delay)
                delay = min(delay * 2, 60)  #  exponential
                continue
            raise
        except (URLError, TimeoutError) as e:
            log(f"  retry {attempt+1}/{max_retries} (network: {e}), waiting {delay:.1f}s")
            time.sleep(delay)
            delay = min(delay * 2, 60)
            continue
    raise RuntimeError(f"failed after {max_retries} retries: {url}")

# --- atomic file write  ---

def atomic_write(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    with open(tmp, 'w') as f:
        if isinstance(content, str):
            f.write(content)
        else:
            json.dump(content, f, indent=2)
    tmp.rename(path)

# --- scrape ---

def scrape_market_json(market_code, outdir, num_homes=350, max_pages=20, status=1, delay=1.5, state=None, dry_run=False):
    city = MARKETS[market_code]["city"]
    all_homes = []
    data_sources = []

    for page in range(1, max_pages + 1):
        key = f"{market_code}:p{page}:s{status}"

        if state and state.is_completed(key):
            log(f"  skip {key} (completed)")
            continue

        url = build_url(market_code, page=page, num_homes=num_homes, status=status)

        if dry_run:
            log(f"  [dry-run] {url}")
            continue

        if state:
            state.mark_in_progress(key)

        log(f"  {market_code} page {page}...")
        try:
            raw = fetch(url)
            raw = strip_prefix(raw)
            d = json.loads(raw)

            if d.get("resultCode") != 0:
                log(f"  error: {d.get('errorMessage', 'unknown')}")
                if state:
                    state.mark_failed(key, d.get("errorMessage", ""))
                break

            homes = d.get("payload", {}).get("homes", [])
            sources = d.get("payload", {}).get("dataSources", [])

            all_homes.extend(homes)
            if sources:
                data_sources = sources

            count = len(homes)
            if state:
                state.mark_completed(key, count)

            log(f"  {market_code} page {page}: {count} listings (total: {len(all_homes)})")

            if count < num_homes:
                break  # last page

            time.sleep(delay)  # 

        except Exception as e:
            log(f"  FAIL {key}: {e}")
            if state:
                state.mark_failed(key, str(e))
            if state and state.data["consecutive_errors"] >= 5:
                log(f"  circuit breaker: 5 consecutive errors, stopping {market_code}")
                break
            continue

    if all_homes and not dry_run:
        out = {
            "market": market_code,
            "city": city,
            "status": "active" if status == 1 else "sold",
            "scraped_at": now_iso(),
            "count": len(all_homes),
            "data_sources": data_sources,
            "homes": all_homes,
        }
        outpath = Path(outdir) / f"{market_code}_s{status}.json"
        atomic_write(outpath, out)
        log(f"  wrote {outpath} ({len(all_homes)} listings)")

    return len(all_homes)

def scrape_market_csv(market_code, outdir, num_homes=350, status=1, delay=1.5, state=None, dry_run=False):
    key = f"{market_code}:csv:s{status}"
    if state and state.is_completed(key):
        log(f"  skip {key} (completed)")
        return 0

    url = build_csv_url(market_code, num_homes=num_homes, status=status)

    if dry_run:
        log(f"  [dry-run] {url}")
        return 0

    if state:
        state.mark_in_progress(key)

    log(f"  {market_code} CSV download...")
    try:
        raw = fetch(url)
        outpath = Path(outdir) / f"{market_code}_s{status}.csv"
        atomic_write(outpath, raw)
        lines = raw.strip().split('\n')
        count = max(0, len(lines) - 1)
        if state:
            state.mark_completed(key, count)
        log(f"  wrote {outpath} ({count} rows)")
        return count
    except Exception as e:
        log(f"  FAIL {key}: {e}")
        if state:
            state.mark_failed(key, str(e))
        return 0

# --- main ---

def main():
    parser = argparse.ArgumentParser(description="Redfin stingray scraper")
    parser.add_argument("--market", type=str, help="Single market code")
    parser.add_argument("--all-markets", action="store_true", help="Scrape all markets")
    parser.add_argument("--status", type=int, default=1, choices=[1, 9], help="1=active, 9=sold")
    parser.add_argument("--max-pages", type=int, default=20)
    parser.add_argument("--num-homes", type=int, default=350)
    parser.add_argument("--output", type=str, default="./redfin-data")
    parser.add_argument("--format", type=str, default="json", choices=["json", "csv", "both"])
    parser.add_argument("--delay", type=float, default=1.5)
    parser.add_argument("--no-resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.market and not args.all_markets:
        parser.error("specify --market MARKET or --all-markets")

    outdir = Path(args.output)
    outdir.mkdir(parents=True, exist_ok=True)

    state = None if args.no_resume else State(outdir / ".state.json")

    #  signal handling
    def handle_signal(sig, frame):
        log(f"caught signal {sig}, saving state...")
        if state:
            state.save()
        sys.exit(0)
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    markets = list(MARKETS.keys()) if args.all_markets else [args.market]
    for m in markets:
        if m not in MARKETS:
            log(f"unknown market: {m}. known: {', '.join(MARKETS.keys())}")
            sys.exit(1)

    total = 0
    for m in markets:
        log(f"--- {MARKETS[m]['city']} ({m}) ---")
        if args.format in ("json", "both"):
            total += scrape_market_json(m, outdir, args.num_homes, args.max_pages, args.status, args.delay, state, args.dry_run)
        if args.format in ("csv", "both"):
            scrape_market_csv(m, outdir, args.num_homes, args.status, args.delay, state, args.dry_run)
            time.sleep(args.delay)

    #  summary
    log(f"=== DONE ===")
    log(f"  total listings: {total}")
    if state:
        log(f"  completed keys: {len(state.data['completed'])}")
        log(f"  failed keys: {len(state.data['failed'])}")
        if state.data["failed"]:
            for f in state.data["failed"][-5:]:
                log(f"  FAIL: {f['key']} - {f['reason']}")

if __name__ == "__main__":
    main()

