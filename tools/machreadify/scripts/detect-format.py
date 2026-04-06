#!/usr/bin/env python3
"""detect-format.py - classify a prose input into the machreadify target format.
Heuristic dispatcher per registry/format-selection.yaml + conversion-targets.yaml."""
import re, sys

def classify(text):
    t = text.lower()
    # CLI / shell signatures
    if re.search(r"^\s*\$\s|^\s*#!|`[a-z]+\s+[^`]*`", text, re.M):
        return ("bash", "cli/shell signatures detected")
    # Decision logic
    if re.search(r"\bif\b.*\bthen\b|if/then|decision|branch", t):
        return ("yaml_matrix", "decision logic - consider skill_compile if agent-executable")
    # Instruction list (numbered or bulleted with verbs)
    if re.search(r"^\s*\d+\.\s|^\s*-\s+(run|execute|set|fetch|read|emit|verify)", text, re.M):
        return ("yaml_workflow", "instruction list with verbs")
    # Config / metadata signatures
    if re.search(r"^\s*\w+\s*[:=]\s|^\s*\{|\[\s*[\{\"']", text, re.M):
        return ("json|yaml", "config/manifest/state")
    # Table signatures
    if re.search(r"\|.+\|.+\|", text):
        return ("json_array|yaml_list", "table detected")
    return ("yaml", "default for ambiguous structured prose")

if __name__ == "__main__":
    text = open(sys.argv[1]).read() if len(sys.argv) > 1 else sys.stdin.read()
    fmt, why = classify(text)
    print(f"{fmt}\t{why}")
