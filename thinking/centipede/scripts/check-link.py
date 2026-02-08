#!/usr/bin/env python3
"""check-link.py - verify a candidate centipede digestion-link output has 5 operations."""
import sys, json

REQUIRED = ["ingest", "dissolve", "identify", "reform", "output"]

if __name__ == "__main__":
    text = open(sys.argv[1]).read() if len(sys.argv) > 1 else sys.stdin.read()
    try:
        import yaml
        d = yaml.safe_load(text)
    except Exception:
        d = json.loads(text)
    if not isinstance(d, dict):
        print("🔴 link must be a mapping", file=sys.stderr); sys.exit(1)
    missing = [k for k in REQUIRED if k not in d]
    if missing:
        print(f"🔴 missing operations: {', '.join(missing)}", file=sys.stderr); sys.exit(1)
    print("🟢 link has all 5 operations")
