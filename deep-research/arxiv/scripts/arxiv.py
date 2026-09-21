#!/usr/bin/env python3
"""
arxiv.py - arXiv public API CLI
Usage:
  arxiv.py search '<query>' [--max N] [--cat <category>] [--full]
  arxiv.py paper <arxiv-id>
  arxiv.py recent <category> [--max N]
"""
import sys
import time
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import argparse
import json

API = "https://export.arxiv.org/api/query"
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}
DELAY = 1.0  # seconds between requests (be civil)


def fetch(params: dict) -> ET.Element:
    url = API + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=15) as r:
        return ET.fromstring(r.read())


def parse_entry(entry: ET.Element, full: bool = False) -> dict:
    def text(tag):
        el = entry.find(tag, NS)
        return el.text.strip() if el is not None and el.text else ""

    arxiv_id = text("atom:id").split("/abs/")[-1].strip()
    abstract = text("atom:summary")
    if not full:
        abstract = abstract[:350] + ("..." if len(abstract) > 350 else "")
    return {
        "id": arxiv_id,
        "title": " ".join(text("atom:title").split()),
        "authors": [
            a.find("atom:name", NS).text.strip()
            for a in entry.findall("atom:author", NS)
            if a.find("atom:name", NS) is not None
        ],
        "published": text("atom:published")[:10],
        "abstract": abstract,
        "categories": [
            c.attrib.get("term", "")
            for c in entry.findall("atom:category", NS)
        ],
        "pdf": f"https://arxiv.org/pdf/{arxiv_id}",
        "abs": f"https://arxiv.org/abs/{arxiv_id}",
    }


def cmd_search(args):
    q = args.query
    if args.cat:
        q = f"cat:{args.cat} AND all:{q}"
    params = {
        "search_query": f"all:{q}",
        "start": 0,
        "max_results": args.max,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }
    root = fetch(params)
    entries = root.findall("atom:entry", NS)
    results = [parse_entry(e, full=args.full) for e in entries]
    print(json.dumps(results, indent=2))


def cmd_paper(args):
    bare = args.id.replace("arxiv:", "").strip()
    root = fetch({"id_list": bare, "max_results": 1})
    entries = root.findall("atom:entry", NS)
    if not entries:
        print(json.dumps({"error": f"not found: {bare}"}))
        sys.exit(1)
    print(json.dumps(parse_entry(entries[0], full=True), indent=2))


def cmd_recent(args):
    params = {
        "search_query": f"cat:{args.category}",
        "start": 0,
        "max_results": args.max,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    root = fetch(params)
    entries = root.findall("atom:entry", NS)
    results = [parse_entry(e) for e in entries]
    print(json.dumps(results, indent=2))


def main():
    p = argparse.ArgumentParser(description="arXiv CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("search", help="search arXiv")
    s.add_argument("query")
    s.add_argument("--max", type=int, default=10)
    s.add_argument("--cat", default="")
    s.add_argument("--full", action="store_true")

    pp = sub.add_parser("paper", help="fetch single paper")
    pp.add_argument("id")

    r = sub.add_parser("recent", help="recent submissions in category")
    r.add_argument("category")
    r.add_argument("--max", type=int, default=20)

    args = p.parse_args()
    time.sleep(0)  # placeholder; enforce DELAY between calls in loops

    dispatch = {"search": cmd_search, "paper": cmd_paper, "recent": cmd_recent}
    dispatch[args.cmd](args)


if __name__ == "__main__":
    main()
