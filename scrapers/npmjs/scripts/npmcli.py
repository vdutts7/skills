#!/usr/bin/env python3
"""
npmcli - npm registry CLI (zero auth, stdlib only)

Usage:
  npmcli search <query> [--top N] [--json]
  npmcli info <package> [--full] [--json]
  npmcli versions <package> [--top N] [--json]
  npmcli downloads <package> [--period PERIOD] [--json]
  npmcli deps <package> [--version VER] [--json]
  npmcli exhaust <package> [--out FILE]
"""
import argparse, json, os, signal, ssl, sys, time, urllib.error, urllib.request
from datetime import datetime, timezone
from urllib.parse import quote

REG = "https://registry.npmjs.org"
DL = "https://api.npmjs.org"
UA = "npmcli/1.0"
_shutdown = False

def ok(m):   print(f"\U0001f7e2 {m}", file=sys.stderr, flush=True)
def fail(m): print(f"\U0001f534 {m}", file=sys.stderr, flush=True)
def spin(m): print(f"\U0001f315 {m}", file=sys.stderr, flush=True)
signal.signal(signal.SIGINT, lambda s,f: (globals().__setitem__('_shutdown', True), spin("interrupted")))

def fetch(url, accept="application/json", timeout=12):
    ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                return json.loads(resp.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            if e.code == 404: return None
            if attempt < 2: time.sleep(0.5 * (attempt + 1))
        except Exception:
            if attempt < 2: time.sleep(0.5 * (attempt + 1))
    return None

def encode_pkg(name):
    """Encode scoped package names: @scope/pkg -> @scope%2fpkg"""
    if name.startswith("@") and "/" in name:
        scope, pkg = name.split("/", 1)
        return f"{scope}%2F{pkg}"
    return quote(name, safe="@")

def fmt_bytes(n):
    if n > 1048576: return f"{n/1048576:.1f} MB"
    if n > 1024: return f"{n/1024:.1f} KB"
    return f"{n} B"

def fmt_num(n):
    if n >= 1_000_000_000: return f"{n/1_000_000_000:.1f}B"
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
    if n >= 1_000: return f"{n/1_000:.1f}K"
    return str(n)

# === SUBCOMMANDS ===
def cmd_search(args):
    spin(f"searching: {args.query}")
    top = args.top or 20
    data = fetch(f"{REG}/-/v1/search?text={quote(args.query)}&size={top}")
    if not data: fail("search failed"); return 1
    if args.json:
        json.dump(data, sys.stdout, indent=2); print(); return 0
    total = data.get("total", 0)
    objects = data.get("objects", [])
    print(f"  {total:,} total matches, showing {len(objects)}")
    print(f"  {'name':<35s} {'version':<12s} {'score':>5s}  description")
    print(f"  {'-'*35} {'-'*12} {'-'*5}  {'-'*40}")
    for obj in objects:
        p = obj.get("package", {})
        sc = obj.get("score", {}).get("final", 0)
        print(f"  {p.get('name','?'):<35s} {p.get('version','?'):<12s} {sc:>5.2f}  {p.get('description','')[:45]}")
    ok(f"{len(objects)}/{total:,} results")
    return 0

def cmd_info(args):
    pkg = encode_pkg(args.package)
    spin(f"fetching: {args.package}")
    if args.full:
        data = fetch(f"{REG}/{pkg}")
    else:
        data = fetch(f"{REG}/{pkg}", accept="application/vnd.npm.install-v1+json")
    if not data: fail(f"package not found: {args.package}"); return 1
    if args.json:
        json.dump(data, sys.stdout, indent=2); print(); return 0
    # formatted output
    dist_tags = data.get("dist-tags", {})
    latest = dist_tags.get("latest", "?")
    versions = data.get("versions", {})
    desc = data.get("description", "")
    license = data.get("license", "?")
    homepage = data.get("homepage", "")
    repo = data.get("repository", {})
    repo_url = repo.get("url", "") if isinstance(repo, dict) else str(repo)
    maintainers = data.get("maintainers", [])
    keywords = data.get("keywords", [])

    print(f"  package:      {data.get('name', args.package)}")
    print(f"  latest:       {latest}")
    print(f"  versions:     {len(versions)}")
    if desc: print(f"  description:  {desc[:80]}")
    print(f"  license:      {license}")
    if homepage: print(f"  homepage:     {homepage}")
    if repo_url: print(f"  repository:   {repo_url}")
    if dist_tags and len(dist_tags) > 1:
        tags = ", ".join(f"{k}={v}" for k, v in dist_tags.items())
        print(f"  dist-tags:    {tags}")
    if maintainers:
        names = ", ".join(m.get("name", "?") for m in maintainers[:5])
        print(f"  maintainers:  {names}")
    if keywords:
        print(f"  keywords:     {', '.join(keywords[:10])}")

    # get latest version details
    if latest in versions:
        v = versions[latest]
        deps = v.get("dependencies", {})
        dev_deps = v.get("devDependencies", {})
        peer = v.get("peerDependencies", {})
        dist = v.get("dist", {})
        print(f"  deps:         {len(deps)} runtime, {len(dev_deps)} dev, {len(peer)} peer")
        if dist.get("unpackedSize"):
            print(f"  size:         {fmt_bytes(dist['unpackedSize'])} unpacked, {dist.get('fileCount','?')} files")

    # quick download stats
    dl = fetch(f"{DL}/downloads/point/last-week/{quote(args.package)}")
    if dl and dl.get("downloads"):
        print(f"  downloads:    {fmt_num(dl['downloads'])}/week")
    ok(f"{args.package}")
    return 0

def cmd_versions(args):
    pkg = encode_pkg(args.package)
    spin(f"fetching versions: {args.package}")
    data = fetch(f"{REG}/{pkg}")
    if not data: fail(f"not found: {args.package}"); return 1
    time_map = data.get("time", {})
    versions = data.get("versions", {})
    dist_tags = data.get("dist-tags", {})
    tag_rev = {v: k for k, v in dist_tags.items()}

    if args.json:
        json.dump({"versions": list(versions.keys()), "time": time_map, "dist_tags": dist_tags}, sys.stdout, indent=2)
        print(); return 0

    # sort by publish time, most recent first
    sorted_v = sorted(time_map.items(), key=lambda x: x[1], reverse=True)
    # filter out 'created' and 'modified' meta keys
    sorted_v = [(v, t) for v, t in sorted_v if v not in ("created", "modified")]
    top = args.top or 10
    print(f"  {len(versions)} total versions (showing {min(top, len(sorted_v))} most recent)")
    print(f"  {'version':<20s} {'published':<22s} {'tag'}")
    print(f"  {'-'*20} {'-'*22} {'-'*10}")
    for ver, ts in sorted_v[:top]:
        tag = tag_rev.get(ver, "")
        print(f"  {ver:<20s} {ts[:19]:<22s} {tag}")
    ok(f"{args.package}: {len(versions)} versions")
    return 0

def cmd_downloads(args):
    period = args.period or "last-week"
    spin(f"downloads: {args.package} ({period})")

    point = fetch(f"{DL}/downloads/point/{period}/{quote(args.package)}")
    if not point: fail(f"no download data: {args.package}"); return 1

    range_data = fetch(f"{DL}/downloads/range/{period}/{quote(args.package)}")

    if args.json:
        out = {"point": point}
        if range_data: out["range"] = range_data
        json.dump(out, sys.stdout, indent=2); print(); return 0

    print(f"  package:    {args.package}")
    print(f"  period:     {point.get('start','')} to {point.get('end','')}")
    print(f"  total:      {point.get('downloads',0):,}")

    if range_data and range_data.get("downloads"):
        days = range_data["downloads"]
        avg = sum(d["downloads"] for d in days) / len(days) if days else 0
        peak = max(days, key=lambda d: d["downloads"])
        print(f"  daily avg:  {avg:,.0f}")
        print(f"  peak:       {peak['downloads']:,} ({peak['day']})")
        # sparkline
        vals = [d["downloads"] for d in days]
        mx = max(vals) if vals else 1
        bars = "".join(["_", ".", ":", "|"][min(3, int(v/mx*3.99))] for v in vals)
        print(f"  trend:      [{bars}]")
    ok(f"{args.package}: {fmt_num(point.get('downloads',0))}/{'week' if 'week' in period else period}")
    return 0

def cmd_deps(args):
    pkg = encode_pkg(args.package)
    spin(f"deps: {args.package}")
    data = fetch(f"{REG}/{pkg}", accept="application/vnd.npm.install-v1+json")
    if not data: fail(f"not found: {args.package}"); return 1
    dist_tags = data.get("dist-tags", {})
    ver = args.version or dist_tags.get("latest", "")
    versions = data.get("versions", {})
    if ver not in versions:
        fail(f"version {ver} not found"); return 1
    v = versions[ver]
    deps = v.get("dependencies", {})
    peer = v.get("peerDependencies", {})
    optional = v.get("optionalDependencies", {})

    if args.json:
        json.dump({"version": ver, "dependencies": deps, "peerDependencies": peer, "optionalDependencies": optional}, sys.stdout, indent=2)
        print(); return 0

    print(f"  {args.package}@{ver}")
    if deps:
        print(f"  dependencies ({len(deps)}):")
        for name, semver in sorted(deps.items()):
            print(f"    {name:<35s} {semver}")
    if peer:
        print(f"  peerDependencies ({len(peer)}):")
        for name, semver in sorted(peer.items()):
            print(f"    {name:<35s} {semver}")
    if optional:
        print(f"  optionalDependencies ({len(optional)}):")
        for name, semver in sorted(optional.items()):
            print(f"    {name:<35s} {semver}")
    if not deps and not peer and not optional:
        print("  zero dependencies")
    ok(f"{args.package}@{ver}: {len(deps)} deps, {len(peer)} peer")
    return 0

def cmd_exhaust(args):
    pkg = encode_pkg(args.package)
    t0 = time.time()
    spin(f"exhaust: {args.package}")

    # full metadata
    spin("  full metadata")
    full = fetch(f"{REG}/{pkg}")
    if not full: fail(f"not found: {args.package}"); return 1

    # download stats for multiple periods
    spin("  download stats")
    dl = {}
    for period in ["last-day", "last-week", "last-month"]:
        d = fetch(f"{DL}/downloads/point/{period}/{quote(args.package)}")
        if d: dl[period] = d

    # download range for last month
    range_data = fetch(f"{DL}/downloads/range/last-month/{quote(args.package)}")

    elapsed = round(time.time() - t0, 1)
    output = {
        "_meta": {"package": args.package, "exhausted_at": datetime.now(timezone.utc).isoformat(), "elapsed_seconds": elapsed},
        "metadata": full,
        "downloads": {"point": dl, "range": range_data},
        "summary": {
            "name": full.get("name"),
            "latest": full.get("dist-tags", {}).get("latest"),
            "versions": len(full.get("versions", {})),
            "license": full.get("license"),
            "description": full.get("description"),
            "downloads_last_week": dl.get("last-week", {}).get("downloads", 0),
            "maintainers": [m.get("name") for m in full.get("maintainers", [])],
        }
    }

    if args.out:
        import tempfile
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(args.out) or ".", suffix=".tmp")
        with os.fdopen(fd, "w") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        os.replace(tmp, args.out)
        ok(f"wrote {args.out} ({fmt_bytes(os.path.getsize(args.out))})")
    elif args.json:
        json.dump(output, sys.stdout, indent=2); print()
    else:
        s = output["summary"]
        print(f"  {s['name']}@{s['latest']}")
        print(f"  {s['versions']} versions | {s['license']} | {s['description'][:60]}")
        print(f"  {fmt_num(s['downloads_last_week'])}/week")
        print(f"  maintainers: {', '.join(s['maintainers'][:5])}")
        print(f"  full metadata: {fmt_bytes(len(json.dumps(full)))}")
    ok(f"exhaust complete: {elapsed}s")
    return 0


def main():
    p = argparse.ArgumentParser(prog="npmcli", description="npm registry CLI")
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("search", help="Search packages")
    sp.add_argument("query"); sp.add_argument("--top", type=int); sp.add_argument("--json", action="store_true")

    sp = sub.add_parser("info", help="Package metadata")
    sp.add_argument("package"); sp.add_argument("--full", action="store_true"); sp.add_argument("--json", action="store_true")

    sp = sub.add_parser("versions", help="Version history")
    sp.add_argument("package"); sp.add_argument("--top", type=int); sp.add_argument("--json", action="store_true")

    sp = sub.add_parser("downloads", help="Download statistics")
    sp.add_argument("package"); sp.add_argument("--period", default="last-week"); sp.add_argument("--json", action="store_true")

    sp = sub.add_parser("deps", help="Dependency tree")
    sp.add_argument("package"); sp.add_argument("--version", type=str); sp.add_argument("--json", action="store_true")

    sp = sub.add_parser("exhaust", help="Full metadata + downloads dump")
    sp.add_argument("package"); sp.add_argument("--out", type=str); sp.add_argument("--json", action="store_true")

    args = p.parse_args()
    return {"search": cmd_search, "info": cmd_info, "versions": cmd_versions,
            "downloads": cmd_downloads, "deps": cmd_deps, "exhaust": cmd_exhaust}[args.command](args)

if __name__ == "__main__": sys.exit(main() or 0)
