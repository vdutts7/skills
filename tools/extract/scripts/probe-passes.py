#!/usr/bin/env python3
"""probe-passes.py - emit the 7-step probe_sequence checklist with counters.
Used to confirm coverage before handoff. Reads registry/probe-mode.yaml as SSOT."""
import yaml, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
mode = yaml.safe_load(open(ROOT / "registry" / "probe-mode.yaml"))
seq = mode["probe_sequence"]

if __name__ == "__main__":
    print("PROBE PASSES (run all 7 in order; done_only_when zero unopened segments remain)")
    for k, v in seq.items():
        if k == "7_done_only_when":
            print(f"  STOP: {v}")
        else:
            print(f"  [ ] {k}: {v}")
