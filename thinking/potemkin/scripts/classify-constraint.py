#!/usr/bin/env python3
"""classify-constraint.py - classify constraint as hard or soft."""
import sys

HARD_SIGNALS = ["physical", "mathematical", "legal", "regulatory", "immutable"]
SOFT_SIGNALS = ["assume", "prefer", "default", "traditionally", "usually", "typically", "our policy"]

def classify(text):
    t = text.lower()
    if any(s in t for s in HARD_SIGNALS):
        return ("hard", "matches hard constraint signal")
    if any(s in t for s in SOFT_SIGNALS):
        return ("soft", "matches soft constraint signal")
    return ("unknown", "no clear signal found")

if __name__ == "__main__":
    text = open(sys.argv[1]).read() if len(sys.argv) > 1 else sys.stdin.read()
    kind, reason = classify(text)
    print(f"{kind}\t{reason}")
