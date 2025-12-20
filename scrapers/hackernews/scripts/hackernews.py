#!/usr/bin/env python3
"""
hackernews - Hacker News Firebase API CLI
Parallel fetch, state persistence, atomic writes, circuit breaker.
Stdlib only. No deps.

Usage:
  hackernews top [--all] [--json] [--out FILE]
  hackernews new [--all] [--json] [--out FILE]
  hackernews best [--all] [--json] [--out FILE]
  hackernews ask [--all] [--json] [--out FILE]
  hackernews show [--all] [--json] [--out FILE]
  hackernews jobs [--all] [--json] [--out FILE]
  hackernews exhaust [--workers N] [--resume]
  hackernews user <username> [--json]
  hackernews item <id> [--json]
"""

import argparse
import hashlib
import json
import os
import signal
import sys
import tempfile
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from urllib.parse import urlparse

# === CONFIG ===
BASE = "https://hacker-news.firebaseio.com/v0"
EXHAUST_DIR = os.path.expandvars("$HOME/.cursor/data/hn")
QUICK_LIMIT = 30
MAX_WORKERS_DEFAULT = 8
RATE_LIMIT_S = 0.05
MAX_RETRIES = 8
INITIAL_DELAY_MS = 500
MAX_DELAY_MS = 30000
CIRCUIT_BREAKER = 20
CHECKPOINT_INTERVAL = 25

ENDPOINTS = {
    "top":  "/topstories.json",
    "new":  "/newstories.json",
    "best": "/beststories.json",
    "ask":  "/askstories.json",
    "show": "/showstories.json",
    "jobs": "/jobstories.json",
}

# === GLOBALS ===
_shutdown = False
_consecutive_errors = 0
_fetch_count = 0

# === LOGMOJI ===
def ok(msg):   print(f"🟢 {msg}", file=sys.stderr, flush=True)
def fail(msg): print(f"🔴 {msg}", file=sys.stderr, flush=True)
def spin(msg): print(f"🌕 {msg}", file=sys.stderr, flush=True)

# === fetch primitives ===
def atomic_write(path, data):
    """tmp+rename atomic write with  verify"""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path) or ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        with open(tmp, "r") as f:
            json.loads(f.read())  # verify
        os.replace(tmp, path)
    except Exception as e:
        try: os.unlink(tmp)
        except OSError: pass
        raise e

def load_state(path):
    """,060,061"""
    default = {"completed": [], "failed": [], "in_progress": None, "last_run": None, "consecutive_errors": 0}
    try:
        with open(path, "r") as f:
            return json.loads(f.read())
    except (FileNotFoundError, json.JSONDecodeError):
        return default

def save_state(state, path):
    s = {k: v for k, v in state.items() if not k.startswith("_")}
    s["last_run"] = datetime.now(timezone.utc).isoformat()
    atomic_write(path, s)

def signal_handler(sig, frame):
    global _shutdown
    _shutdown = True
    spin(f"signal {sig} - graceful shutdown")

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def fetch_json(url, retries=MAX_RETRIES):
    """,081,125: exponential backoff + jitter"""
    global _consecutive_errors, _fetch_count
    delay_ms = INITIAL_DELAY_MS
    for attempt in range(1, retries + 1):
        if _shutdown:
            return None
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "hackernews/1.0",
                "Accept": "application/json",
            })
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                _consecutive_errors = 0
                _fetch_count += 1
                return data
        except Exception as e:
            _consecutive_errors += 1
            if _consecutive_errors >= CIRCUIT_BREAKER:
                fail(f"circuit breaker tripped ({_consecutive_errors} consecutive)")
                return None
            if attempt < retries:
                jitter = (hash(url + str(attempt)) % 300)
                sleep_s = min(delay_ms + jitter, MAX_DELAY_MS) / 1000
                time.sleep(sleep_s)
                delay_ms *= 2
            else:
                return None

def fetch_item(item_id, completed_set):
    if str(item_id) in completed_set:
        return None
    time.sleep(RATE_LIMIT_S)
    data = fetch_json(f"{BASE}/item/{item_id}.json")
    if data is None:
        return {"_id": item_id, "_error": True}
    return data

def fetch_user(username, completed_set):
    if username in completed_set:
        return None
    time.sleep(RATE_LIMIT_S)
    data = fetch_json(f"{BASE}/user/{username}.json")
    if data is None:
        return {"_id": username, "_error": True}
    return data

def parallel_fetch(ids, fn, completed_set, label, workers):
    results = {}
    pending = [x for x in ids if str(x) not in completed_set]
    spin(f"{label}: {len(ids)} total, {len(ids)-len(pending)} cached, {len(pending)} pending")
    if not pending:
        return results
    done = 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fn, x, completed_set): x for x in pending}
        for future in as_completed(futures):
            if _shutdown:
                break
            xid = futures[future]
            try:
                item = future.result()
                if item is None:
                    continue
                if not item.get("_error"):
                    results[str(xid)] = item
                    done += 1
                    if done % 100 == 0:
                        elapsed = time.time() - t0
                        spin(f"{label}: {done}/{len(pending)} ({_fetch_count/(elapsed or 1):.0f} req/s)")
            except Exception:
                pass
    ok(f"{label}: {done} fetched")
    return results


# === TABLE FORMATTING ===
def format_stories(items, ids):
    """Pretty-print story list as aligned table"""
    rows = []
    for rank, sid in enumerate(ids, 1):
        item = items.get(str(sid))
        if not item:
            continue
        title = item.get("title", "?")[:65]
        score = item.get("score", 0)
        by = item.get("by", "?")
        comments = item.get("descendants", 0) or 0
        url = item.get("url", "")
        domain = ""
        if url:
            try: domain = urlparse(url).netloc.replace("www.", "")[:25]
            except Exception: pass
        rows.append((rank, score, comments, by[:14], domain, title))
    
    if not rows:
        print("  (no stories)")
        return

    print(f"  {'#':>3}  {'pts':>5}  {'cmt':>4}  {'by':<14}  {'domain':<25}  title")
    print(f"  {'---':>3}  {'-----':>5}  {'----':>4}  {'-'*14}  {'-'*25}  {'-'*40}")
    for rank, score, comments, by, domain, title in rows:
        print(f"  {rank:>3}  {score:>5}  {comments:>4}  {by:<14}  {domain:<25}  {title}")

def format_user(user):
    """Pretty-print user profile"""
    if not user:
        fail("user not found")
        return
    created = datetime.fromtimestamp(user.get("created", 0), tz=timezone.utc).strftime("%Y-%m-%d")
    submitted = user.get("submitted", [])
    print(f"  user:      {user.get('id', '?')}")
    print(f"  karma:     {user.get('karma', 0):,}")
    print(f"  created:   {created}")
    print(f"  submitted: {len(submitted):,} items")
    about = user.get("about", "")
    if about:
        # strip HTML tags for display
        import re
        about = re.sub(r'<[^>]+>', '', about)[:200]
        print(f"  about:     {about}")

def format_item(item):
    """Pretty-print single item"""
    if not item:
        fail("item not found")
        return
    print(f"  id:       {item.get('id', '?')}")
    print(f"  type:     {item.get('type', '?')}")
    print(f"  by:       {item.get('by', '?')}")
    print(f"  score:    {item.get('score', 0)}")
    print(f"  title:    {item.get('title', '')}")
    print(f"  url:      {item.get('url', '')}")
    ts = item.get("time", 0)
    if ts:
        print(f"  time:     {datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()}")
    print(f"  comments: {item.get('descendants', 0)}")
    kids = item.get("kids", [])
    if kids:
        print(f"  replies:  {len(kids)} direct")


# === SUBCOMMANDS ===
def cmd_list(args):
    """Fetch a story list endpoint"""
    endpoint = ENDPOINTS[args.command]
    spin(f"fetching {args.command} stories")
    ids = fetch_json(f"{BASE}{endpoint}")
    if ids is None:
        fail("failed to fetch story list")
        return 1

    limit = len(ids) if args.all else min(QUICK_LIMIT, len(ids))
    ids = ids[:limit]

    spin(f"fetching {len(ids)} items")
    items = parallel_fetch(ids, fetch_item, set(), "items", args.workers)

    if args.out:
        output = [items.get(str(sid)) for sid in ids if str(sid) in items]
        atomic_write(args.out, output)
        ok(f"wrote {len(output)} stories to {args.out}")
    elif args.json:
        output = [items.get(str(sid)) for sid in ids if str(sid) in items]
        json.dump(output, sys.stdout, indent=2, ensure_ascii=False)
        print()
    else:
        format_stories(items, ids)
        ok(f"{len(items)} stories")
    return 0

def cmd_exhaust(args):
    """Full surface exhaust - all endpoints, all items, all users"""
    t0 = time.time()
    os.makedirs(EXHAUST_DIR, exist_ok=True)
    state_path = os.path.join(EXHAUST_DIR, ".state.json")
    
    if args.resume:
        state = load_state(state_path)
        spin("resuming from checkpoint")
    else:
        state = load_state("/dev/null")  # fresh

    # phase 1: all list endpoints
    spin("phase 1: enumerating all story lists + metadata")
    lists = {}
    meta = {}
    with ThreadPoolExecutor(max_workers=len(ENDPOINTS) + 2) as pool:
        futs = {pool.submit(fetch_json, f"{BASE}{path}"): name for name, path in ENDPOINTS.items()}
        futs[pool.submit(fetch_json, f"{BASE}/maxitem.json")] = "_maxitem"
        futs[pool.submit(fetch_json, f"{BASE}/updates.json")] = "_updates"
        for future in as_completed(futs):
            name = futs[future]
            try:
                data = future.result()
                if name == "_maxitem":
                    meta["max_item_id"] = data
                elif name == "_updates":
                    meta["updates"] = data
                else:
                    lists[name] = data or []
                spin(f"  {name}: {len(data) if isinstance(data, list) else 1}")
            except Exception:
                fail(f"  {name}: FAILED")

    # deduplicate
    all_item_ids = set()
    for ids in lists.values():
        all_item_ids.update(ids)
    if meta.get("updates"):
        all_item_ids.update(meta["updates"].get("items", []))

    ok(f"phase 1: {len(all_item_ids)} unique items across {len(lists)} lists")

    # phase 2: fetch items
    spin(f"phase 2: fetching {len(all_item_ids)} items")
    completed_items = set(str(x) for x in state.get("completed", []))
    items = parallel_fetch(list(all_item_ids), fetch_item, completed_items, "items", args.workers)
    state["completed"] = list(completed_items | set(items.keys()))
    save_state(state, state_path)

    # phase 3: fetch users
    all_users = set()
    for item in items.values():
        by = item.get("by")
        if by:
            all_users.add(by)
    if meta.get("updates"):
        all_users.update(meta["updates"].get("profiles", []))

    spin(f"phase 3: fetching {len(all_users)} user profiles")
    completed_users = set(state.get("completed_users", []))
    users = parallel_fetch(list(all_users), fetch_user, completed_users, "users", args.workers)

    # phase 4: analysis + write
    spin("phase 4: assembly")
    from collections import Counter
    
    domains = Counter()
    for item in items.values():
        url = item.get("url", "")
        if url:
            try:
                dom = urlparse(url).netloc.replace("www.", "")
                if dom: domains[dom] += 1
            except Exception: pass

    scores = [item.get("score", 0) for item in items.values() if item.get("type") == "story"]
    karmas = [u.get("karma", 0) for u in users.values() if isinstance(u, dict)]
    
    elapsed = time.time() - t0

    # content hash for determinism 
    content_hash = hashlib.sha256(
        json.dumps(list(items.values()), sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()[:16]

    output = {
        "_meta": {
            "source": "hacker-news-firebase-api",
            "mode": "full_surface_exhaust",
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": round(elapsed, 1),
            "total_http_requests": _fetch_count,
            "rps": round(_fetch_count / elapsed, 1) if elapsed > 0 else 0,
            "content_hash": content_hash,
        },
        "lists": {name: {"count": len(ids), "ids": ids} for name, ids in lists.items()},
        "items": {"total": len(items), "data": list(items.values())},
        "users": {"total": len(users), "data": list(users.values())},
        "domains": {"unique": len(domains), "top_50": domains.most_common(50)},
        "updates": meta.get("updates"),
    }

    atomic_write(os.path.join(EXHAUST_DIR, "hn_exhaust.json"), output)
    atomic_write(os.path.join(EXHAUST_DIR, "analysis.json"), {
        "list_sizes": {n: len(ids) for n, ids in lists.items()},
        "unique_items": len(items),
        "unique_users": len(users),
        "unique_domains": len(domains),
        "avg_score": round(sum(scores)/len(scores)) if scores else 0,
        "max_score": max(scores) if scores else 0,
        "avg_karma": round(sum(karmas)/len(karmas)) if karmas else 0,
        "top_domains": domains.most_common(20),
        "elapsed": round(elapsed, 1),
        "requests": _fetch_count,
        "content_hash": content_hash,
    })

    ok(f"exhaust complete: {len(items)} items, {len(users)} users, {len(domains)} domains")
    ok(f"{_fetch_count} requests in {elapsed:.1f}s ({_fetch_count/elapsed:.0f} req/s)")
    ok(f"output: {EXHAUST_DIR}/")
    return 0

def cmd_user(args):
    """Fetch single user profile"""
    spin(f"fetching user: {args.username}")
    data = fetch_json(f"{BASE}/user/{args.username}.json")
    if data is None:
        fail(f"user not found: {args.username}")
        return 1
    if args.json:
        json.dump(data, sys.stdout, indent=2, ensure_ascii=False)
        print()
    else:
        format_user(data)
    ok(f"user: {args.username}")
    return 0

def cmd_item(args):
    """Fetch single item"""
    spin(f"fetching item: {args.item_id}")
    data = fetch_json(f"{BASE}/item/{args.item_id}.json")
    if data is None:
        fail(f"item not found: {args.item_id}")
        return 1
    if args.json:
        json.dump(data, sys.stdout, indent=2, ensure_ascii=False)
        print()
    else:
        format_item(data)
    ok(f"item: {args.item_id}")
    return 0


# === MAIN ===
def main():
    p = argparse.ArgumentParser(prog="hackernews", description="Hacker News Firebase API CLI")
    sub = p.add_subparsers(dest="command", required=True)

    # list subcommands (top, new, best, ask, show, jobs)
    for name in ENDPOINTS:
        sp = sub.add_parser(name, help=f"Fetch /{name}stories")
        sp.add_argument("--all", action="store_true", help="Fetch all (no limit)")
        sp.add_argument("--json", action="store_true", help="Raw JSON output")
        sp.add_argument("--out", type=str, help="Write to file")
        sp.add_argument("--workers", type=int, default=MAX_WORKERS_DEFAULT, help="Parallel workers")

    # exhaust
    sp = sub.add_parser("exhaust", help="Full surface exhaust (all endpoints)")
    sp.add_argument("--workers", type=int, default=MAX_WORKERS_DEFAULT, help="Parallel workers")
    sp.add_argument("--resume", action="store_true", help="Resume from checkpoint")

    # user
    sp = sub.add_parser("user", help="Fetch user profile")
    sp.add_argument("username", help="HN username")
    sp.add_argument("--json", action="store_true", help="Raw JSON output")

    # item
    sp = sub.add_parser("item", help="Fetch single item")
    sp.add_argument("item_id", help="Item ID")
    sp.add_argument("--json", action="store_true", help="Raw JSON output")

    args = p.parse_args()

    if args.command in ENDPOINTS:
        return cmd_list(args)
    elif args.command == "exhaust":
        return cmd_exhaust(args)
    elif args.command == "user":
        return cmd_user(args)
    elif args.command == "item":
        return cmd_item(args)
    else:
        p.print_help()
        return 1

if __name__ == "__main__":
    sys.exit(main() or 0)
