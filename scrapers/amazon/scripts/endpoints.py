"""endpoints.py - harvest www.amazon.com XHR/Fetch URLs from a local HAR folder (report.json + raw.har)."""

import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from urllib.parse import urlparse

from amazon import log, _REGISTRY_DIR

DEFAULT_HAR_ROOT = "./captures"

SKIP_HOST_SUBSTR = (
    "chrome-extension://",
    "moz-extension://",
    "localhost",
    "127.0.0.1",
)
SKIP_NETLOC_SUBSTR = (
    "googleapis.com",
    "googlesyndication.com",
    "gstatic.com",
    "doubleclick.net",
    "facebook.com",
    "firebase",
)


def _endpoint_id(method, path):
    raw = f"{method.lower()}_{(path or '/').strip('/')}".replace("/", "_")
    raw = re.sub(r"[^a-zA-Z0-9_]+", "_", raw).strip("_").lower()
    return raw[:96] or "endpoint"


def _categorize(path):
    p = path or ""
    if "twister" in p.lower():
        return "twister"
    if "add-to-cart" in p:
        return "cart"
    if "glow" in p:
        return "localization"
    if "dram/" in p:
        return "lazy_fragment"
    if "/acp/" in p:
        return "experiments"
    if "/cart/" in p:
        return "cart"
    if "/cross_border" in p:
        return "interstitial"
    return "xhr"


def _skip_url(url):
    if not url or not url.startswith(("http://", "https://")):
        return True
    for s in SKIP_HOST_SUBSTR:
        if s in url:
            return True
    try:
        u = urlparse(url)
        host = (u.hostname or "").lower()
        if not host:
            return True
        for s in SKIP_NETLOC_SUBSTR:
            if s in host:
                return True
    except Exception:
        return True
    return False


def _harvest_report(report_path, capture_id, bucket):
    try:
        with open(report_path, encoding="utf-8", errors="replace") as f:
            data = json.load(f)
    except Exception as e:
        log("~", f"skip report {report_path}: {e}")
        return
    apis = (data.get("network") or {}).get("apis") or []
    for row in apis:
        method = (row.get("method") or "GET").upper()
        url = row.get("url") or ""
        if method not in ("GET", "POST", "PUT"):
            continue
        if _skip_url(url):
            continue
        u = urlparse(url)
        host = u.hostname or ""
        if not host.endswith("amazon.com"):
            continue
        key = (method, host.lower(), u.path or "/")
        entry = bucket.setdefault(key, {"method": method, "host": host, "path": u.path or "/", "samples": set(), "sources": set(), "category": _categorize(u.path)})
        entry["samples"].add(url)
        entry["sources"].add(f"report:{capture_id}")


def _har_interesting(method, url, rtype):
    """Keep HAR rows that look like APIs (skip static assets / bare PDP HTML)."""
    if _skip_url(url):
        return False
    if method not in ("GET", "POST"):
        return False
    u = urlparse(url)
    host = u.hostname or ""
    if not host.endswith("amazon.com"):
        return False
    path = u.path or ""
    pl = path.lower()
    if pl.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp", ".ico", ".woff", ".woff2")):
        return False

    if method == "POST":
        return True
    if rtype in ("xhr", "fetch"):
        return True

    if "/gp/product/ajax/" in path or "/cart/" in path or "/portal-migration/" in path:
        return True
    if path.startswith("/hz/") or path.startswith("/acp/") or "/dram/" in path:
        return True
    if path.startswith("/cross_border"):
        return True
    if path.startswith("/s") and "k=" in url:
        return True
    return False


def _harvest_har(har_path, capture_id, bucket):
    try:
        with open(har_path, encoding="utf-8", errors="replace") as f:
            har = json.load(f)
    except Exception as e:
        log("~", f"skip har {har_path}: {e}")
        return
    entries = (har.get("log") or {}).get("entries") or []
    for item in entries:
        req = item.get("request") or {}
        method = (req.get("method") or "GET").upper()
        url = req.get("url") or ""
        rtype = item.get("_resourceType") or ""
        if not _har_interesting(method, url, rtype):
            continue
        u = urlparse(url)
        host = u.hostname or ""
        key = (method, host.lower(), u.path or "/")
        entry = bucket.setdefault(key, {"method": method, "host": host, "path": u.path or "/", "samples": set(), "sources": set(), "category": _categorize(u.path)})
        entry["samples"].add(url)
        entry["sources"].add(f"har:{capture_id}")


def _copy_if_exists(src, dst_dir):
    if not os.path.isfile(src):
        return False
    os.makedirs(dst_dir, exist_ok=True)
    shutil.copy2(src, os.path.join(dst_dir, os.path.basename(src)))
    return True


def _write_har_index(har_path, out_path):
    """Strip cookies/bodies; keep method + URL + resourceType for quick intel."""
    try:
        with open(har_path, encoding="utf-8", errors="replace") as f:
            har = json.load(f)
    except Exception:
        return False
    rows = []
    for item in (har.get("log") or {}).get("entries") or []:
        req = item.get("request") or {}
        url = req.get("url") or ""
        if not url.startswith(("http://", "https://")):
            continue
        rows.append(
            {
                "method": (req.get("method") or "GET").upper(),
                "url": url[:2048],
                "_resourceType": item.get("_resourceType") or "",
            }
        )
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({"entry_count": len(rows), "entries": rows}, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def harvest_har_dir(root=None):
    root = root or DEFAULT_HAR_ROOT
    bucket = {}
    if not os.path.isdir(root):
        log("x", f"HAR root missing: {root}")
        return None

    subs = []
    for name in os.listdir(root):
        p = os.path.join(root, name)
        if os.path.isdir(p):
            subs.append((name, p))
    subs.sort(key=lambda x: x[0], reverse=True)
    latest_capture_id = subs[0][0] if subs else None

    for capture_id, base in subs:
        rp = os.path.join(base, "explore", "report.json")
        if os.path.isfile(rp):
            _harvest_report(rp, capture_id, bucket)
        hp = os.path.join(base, "raw.har")
        if os.path.isfile(hp):
            _harvest_har(hp, capture_id, bucket)

    endpoints = []
    templates = {}
    for key, row in sorted(bucket.items(), key=lambda kv: (kv[1]["host"], kv[1]["path"])):
        method, host, path = key
        samples = sorted(row["samples"], key=len, reverse=True)
        sample_url = samples[0] if samples else ""
        eid = _endpoint_id(method, path)
        if path.endswith("twisterDimensionSlotsDefault") or "twisterDimensionSlotsDefault" in path:
            templates["twister_dimension_slots"] = sample_url
            eid = "twister_dimension_slots"
        ep = {
            "id": eid,
            "category": row["category"],
            "method": method,
            "host": host,
            "path": path,
            "sample_url": sample_url,
            "sample_count": len(samples),
            "sources": sorted(row["sources"]),
        }
        endpoints.append(ep)

    out = {
        "_meta": {
            "endpoint_count": len(endpoints),
            "note": "Regenerate: amazon endpoints refresh --root <har-dir>. Samples are from HAR captures; replay may need fresh PDP query strings.",
            "latest_capture_id": latest_capture_id,
        },
        "templates": templates,
        "endpoints": endpoints,
    }
    return out


def write_registry(doc):
    path = os.path.join(_REGISTRY_DIR, "endpoints.json")
    os.makedirs(_REGISTRY_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
    return path


def load_registry():
    path = os.path.join(_REGISTRY_DIR, "endpoints.json")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"_meta": {}, "templates": {}, "endpoints": []}


def cmd_endpoints_refresh(args):
    doc = harvest_har_dir(args.root)
    if not doc:
        sys.exit(1)

    path = write_registry(doc)
    log("+", f"wrote {doc['_meta']['endpoint_count']} endpoints → {path}")
    if doc.get("templates"):
        log("+", f"templates: {', '.join(doc['templates'].keys())}")


def cmd_endpoints_list(args):
    doc = load_registry()
    eps = doc.get("endpoints") or []
    pat = (args.pattern or "").lower()
    www_only = not getattr(args, "all_hosts", False)
    rows = []
    for ep in eps:
        if www_only and ep.get("host") != "www.amazon.com":
            continue
        if pat and pat not in (ep.get("path") or "").lower() and pat not in (ep.get("id") or "").lower():
            continue
        rows.append(ep)
    if args.format == "json":
        print(json.dumps(rows, indent=2, ensure_ascii=False))
        return
    for ep in rows:
        print(f"{ep.get('method')} {ep.get('host')}{ep.get('path')}  [{ep.get('category')}]")
        if ep.get("sample_url"):
            print(f"    {ep['sample_url'][:140]}{'…' if len(ep['sample_url']) > 140 else ''}")
        print()


def cmd_endpoints(args):
    {"refresh": cmd_endpoints_refresh, "list": cmd_endpoints_list}[args.endpoints_cmd](args)

