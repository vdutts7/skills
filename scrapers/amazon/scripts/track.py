"""track.py - price tracking with watchlist, history, and change detection"""

import json
import os
import re
import sys
import time

from amazon import fetch, log, _strip, _section, asin_from_input

_TRACK_DIR = os.path.expanduser("~/.amazon")
_WATCHLIST = os.path.join(_TRACK_DIR, "watchlist.jsonl")
_HISTORY = os.path.join(_TRACK_DIR, "history.jsonl")


def _ensure_dir():
    os.makedirs(_TRACK_DIR, exist_ok=True)


def _load_watchlist():
    _ensure_dir()
    items = {}
    if os.path.exists(_WATCHLIST):
        with open(_WATCHLIST) as f:
            for line in f:
                line = line.strip()
                if line:
                    entry = json.loads(line)
                    items[entry["asin"]] = entry
    return items


def _save_watchlist(items):
    _ensure_dir()
    with open(_WATCHLIST, "w") as f:
        for entry in items.values():
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _append_history(record):
    _ensure_dir()
    with open(_HISTORY, "a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _load_history(asin=None):
    records = []
    if os.path.exists(_HISTORY):
        with open(_HISTORY) as f:
            for line in f:
                line = line.strip()
                if line:
                    rec = json.loads(line)
                    if asin is None or rec.get("asin") == asin:
                        records.append(rec)
    return records


def _extract_price(html):
    """quick price extraction without full product rip"""
    sec = _section(html, r'id="corePrice|id="corePriceDisplay|id="apex_desktop|class="a-price"', max_len=10000)
    if not sec:
        sec = html[:50000]
    m = re.search(r'class="a-price-whole"[^>]*>(\d+)<.*?class="a-price-fraction"[^>]*>(\d+)<', sec, re.DOTALL)
    if m:
        return float(f"{m.group(1)}.{m.group(2)}")
    m = re.search(r'"priceAmount":\s*([\d.]+)', sec)
    if m:
        return float(m.group(1))
    return None


def _extract_title(html):
    sec = _section(html, r'id="productTitle"', max_len=2000)
    m = re.search(r'id="productTitle"[^>]*>(.*?)</span>', sec, re.DOTALL)
    if m:
        return _strip(m.group(1))
    m = re.search(r"<title>(.*?)</title>", html[:10000], re.DOTALL)
    if m:
        return re.sub(r"\s*:?\s*Amazon\.com.*$", "", _strip(m.group(1)))
    return None


def cmd_track_add(args):
    asin, url = asin_from_input(args.target)
    if not asin:
        log("x", f"can't parse ASIN from: {args.target}")
        sys.exit(1)

    watchlist = _load_watchlist()
    if asin in watchlist:
        log("~", f"{asin} already on watchlist")
        return

    log("~", f"fetching current price for {asin}")
    html = fetch(url)
    price = _extract_price(html) if html else None
    title = _extract_title(html) if html else None

    entry = {
        "asin": asin,
        "label": args.label or title or asin,
        "added": int(time.time()),
        "last_price": price,
        "last_check": int(time.time()),
    }
    watchlist[asin] = entry
    _save_watchlist(watchlist)

    if price:
        _append_history({"asin": asin, "price": price, "ts": int(time.time())})

    log("+", f"added {asin} to watchlist: {entry['label']} @ ${price}" if price else f"added {asin} (price unknown)")


def cmd_track_check(args):
    watchlist = _load_watchlist()
    if not watchlist:
        log("x", "watchlist is empty - use 'track add' first")
        return

    targets = watchlist
    if hasattr(args, "asin") and args.asin:
        if args.asin in watchlist:
            targets = {args.asin: watchlist[args.asin]}
        else:
            log("x", f"{args.asin} not on watchlist")
            return

    results = []
    for asin, entry in targets.items():
        url = f"https://www.amazon.com/dp/{asin}"
        log("~", f"checking {asin}: {entry.get('label', '?')}")
        html = fetch(url)
        new_price = _extract_price(html) if html else None

        old_price = entry.get("last_price")
        change = None
        if new_price is not None and old_price is not None:
            diff = new_price - old_price
            if abs(diff) > 0.01:
                pct = (diff / old_price) * 100
                change = {"diff": round(diff, 2), "pct": round(pct, 1)}

        record = {
            "asin": asin,
            "label": entry.get("label", asin),
            "old_price": old_price,
            "new_price": new_price,
            "change": change,
            "ts": int(time.time()),
        }
        results.append(record)

        if new_price is not None:
            _append_history({"asin": asin, "price": new_price, "ts": int(time.time())})
            entry["last_price"] = new_price
            entry["last_check"] = int(time.time())

        time.sleep(1.5)

    _save_watchlist(watchlist)

    fmt = getattr(args, "format", "table")
    if fmt == "json":
        out = json.dumps(results, indent=2, ensure_ascii=False)
    else:
        out = _fmt_check_table(results)

    print(out)


def _fmt_check_table(results):
    lines = ["  PRICE CHECK", "  " + "=" * 60, ""]
    for r in results:
        change_str = ""
        if r.get("change"):
            c = r["change"]
            arrow = "v" if c["diff"] < 0 else "^"
            change_str = f" {arrow} ${abs(c['diff']):.2f} ({c['pct']:+.1f}%)"
        old = f"${r['old_price']:.2f}" if r.get("old_price") is not None else "?"
        new = f"${r['new_price']:.2f}" if r.get("new_price") is not None else "?"
        lines.append(f"  {r['asin']} {r.get('label', '?')[:40]}")
        lines.append(f"           {old} -> {new}{change_str}")
        lines.append("")
    return "\n".join(lines)


def cmd_track_history(args):
    asin, _ = asin_from_input(args.target)
    if not asin:
        log("x", f"can't parse ASIN from: {args.target}")
        sys.exit(1)

    records = _load_history(asin)
    if not records:
        log("x", f"no history for {asin}")
        return

    fmt = getattr(args, "format", "table")
    if fmt == "json":
        out = json.dumps(records, indent=2, ensure_ascii=False)
    else:
        lines = [f"  PRICE HISTORY: {asin}", "  " + "=" * 40, ""]
        prev = None
        for r in records:
            ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(r["ts"]))
            price = r.get("price")
            change = ""
            if prev is not None and price is not None:
                diff = price - prev
                if abs(diff) > 0.01:
                    change = f"  ({'+' if diff > 0 else ''}{diff:.2f})"
            lines.append(f"  {ts}  ${price:.2f}{change}" if price else f"  {ts}  ?")
            if price is not None:
                prev = price
        out = "\n".join(lines)

    print(out)


def cmd_track(args):
    {
        "add": cmd_track_add,
        "check": cmd_track_check,
        "history": cmd_track_history,
    }[args.track_cmd](args)
