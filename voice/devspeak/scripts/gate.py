#!/usr/bin/env python3
"""devspeak gate - reads manifest routes; no policy inline."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_yaml(path: Path) -> dict:
    if not path.is_file() or yaml is None:
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def resolve_routes(manifest_path: Path) -> dict[str, Path]:
    root = manifest_path.parent
    manifest = load_json(manifest_path)
    routes = manifest.get("routes") or {}
    return {k: root / v for k, v in routes.items() if isinstance(v, str)}


def strip_protected(text: str) -> str:
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`[^`]+`", "CODE", text)
    return text


def count_emojis(text: str, exclude: list[str] | None = None) -> int:
    exclude = exclude or []
    found = re.findall(r"[\U0001F300-\U0001FAFF\u2600-\u27BF❌✅🟢🔴🟡]", text)
    if exclude:
        found = [e for e in found if e not in exclude]
    return len(found)


def check_banned_phrases(clean: str, ledger: dict, strict: bool, emit) -> None:
    for item in ledger.get("phrases") or []:
        pat = item.get("regex") or item.get("match")
        if not pat:
            continue
        flags = re.IGNORECASE if item.get("regex") else 0
        if re.compile(pat, flags).search(clean):
            bid = item.get("id", "BP")
            action = item.get("action", "fix")
            emit("fail", f"{bid}: banned phrase ({action})")


def check_file(
    path: Path,
    ap: dict,
    banned: dict,
    logic: dict,
    strict: bool,
) -> tuple[int, int, int]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    clean = strip_protected(raw)
    lines = max(1, clean.count("\n") + (1 if clean else 0))
    ok = fail = warn = 0

    def emit(level: str, msg: str) -> None:
        nonlocal ok, fail, warn
        if level == "ok":
            ok += 1
            print(f"🟢 - {msg}", file=sys.stderr)
        elif level == "fail":
            fail += 1
            print(f"🔴 - {msg}", file=sys.stderr)
        else:
            warn += 1
            print(f"🟡 - {msg}", file=sys.stderr)

    max_e = 8
    exclude_markers: list[str] = []
    for w in ap.get("warn", []):
        if w.get("name") == "emoji_flood":
            max_e = int(w.get("max_emojis_per_100_lines", 8))
            exclude_markers = list(w.get("exclude_markers") or [])
            break

    emojis = count_emojis(clean, exclude_markers)
    if emojis * 100 // lines > max_e:
        emit("fail" if strict else "warn", f"DS-010 emoji_flood: too many emojis ({emojis} in {lines} lines)")
    else:
        emit("ok", f"{path}: emoji density ok")

    for item in ap.get("forbidden", []):
        if re.compile(item["regex"], re.MULTILINE).search(clean):
            emit("fail", f"{item['id']} {item['name']}: {item['message']}")

    for item in ap.get("warn", []):
        if item.get("name") == "emoji_flood" or not item.get("regex"):
            continue
        flags = re.MULTILINE | (re.IGNORECASE if "i" in item.get("flags", "") else 0)
        if re.compile(item["regex"], flags).search(clean):
            emit("fail" if strict else "warn", f"{item['id']} {item['name']}: {item['message']}")

    check_banned_phrases(clean, banned, strict, emit)

    for phrase in logic.get("antipatterns") or []:
        if phrase.lower() in clean.lower():
            emit("warn", f"logic-flow: essay antipattern `{phrase}`")

    emit("ok", f"{path}: scanned")
    return ok, fail, warn


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", required=True)
    p.add_argument("--strict", action="store_true")
    p.add_argument("files", nargs="+")
    args = p.parse_args()

    manifest_path = Path(args.manifest)
    if not manifest_path.is_file():
        print(f"🔴 - missing manifest: {manifest_path}", file=sys.stderr)
        return 1

    routes = resolve_routes(manifest_path)
    missing = [k for k, v in routes.items() if not v.is_file()]
    if missing:
        for k in missing:
            print(f"🔴 - manifest route missing: {k} -> {routes[k]}", file=sys.stderr)
        return 1

    ap = load_json(routes["antipatterns"])
    banned = load_json(routes["banned_phrases"])
    logic = load_yaml(routes["logic_flow"])

    total_ok = total_fail = total_warn = 0
    for f in args.files:
        path = Path(f)
        if not path.is_file():
            print(f"🔴 - missing file: {path}", file=sys.stderr)
            total_fail += 1
            continue
        ok, fail, warn = check_file(path, ap, banned, logic, args.strict)
        total_ok += ok
        total_fail += fail
        total_warn += warn

    print(
        f"- pass={total_ok} fail={total_fail} warn={total_warn} strict={int(args.strict)}",
        file=sys.stderr,
    )
    return 1 if total_fail else 0


if __name__ == "__main__":
    sys.exit(main())
