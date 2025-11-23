#!/usr/bin/env python3
"""sanitize.py - apply humanize hard invariants per registry/laws.json.
R-000 (em-dash/en-dash -> hyphen) is the load-bearing check.
"""
import sys
import pathlib
import json

ROOT = pathlib.Path(__file__).resolve().parent.parent
LAWS = ROOT / "registry" / "laws.json"

# Load law definitions (currently apply only the hard invariants R-000)
with open(LAWS) as f:
    laws = json.load(f)

# R-000: em-dash and en-dash forbidden
DASHES = ("\u2013", "\u2014")  # en-dash, em-dash

def sanitize(text: str) -> str:
    for ch in DASHES:
        text = text.replace(ch, "-")
    return text

if __name__ == "__main__":
    if len(sys.argv) > 1:
        text = open(sys.argv[1]).read()
    else:
        text = sys.stdin.read()
    sys.stdout.write(sanitize(text))
