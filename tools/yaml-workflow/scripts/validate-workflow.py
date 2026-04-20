#!/usr/bin/env python3
"""validate-workflow.py - confirm a yaml-workflow file matches the required structure.
Checks: id/version/shape/goal present; steps|phases|pipeline present; every step has id+cmd|action."""
import yaml, sys

REQUIRED_TOP = ["id", "version", "shape", "goal"]
SHAPE_BODIES = {
    "skeleton_flow": "steps",
    "skeleton_phases": "phases",
    "skeleton_pipeline": "pipeline",
    "skeleton_meta_phases": "phases",
    "skeleton_leaf_phase": "steps",
}

def errors(doc):
    errs = []
    for k in REQUIRED_TOP:
        if k not in doc: errs.append(f"missing top-level: {k}")
    shape = doc.get("shape")
    if shape and shape not in SHAPE_BODIES:
        errs.append(f"unknown shape: {shape}")
    body_key = SHAPE_BODIES.get(shape, "steps")
    items = doc.get(body_key) or []
    if not items:
        errs.append(f"empty body: {body_key}")
    for i, item in enumerate(items):
        if not isinstance(item, dict): continue
        if "id" not in item:
            errs.append(f"{body_key}[{i}] missing id")
        # For step-like nodes (no nested workflow), require cmd OR action
        if body_key in ("steps", "pipeline") and "nested_workflow_ref" not in item:
            if not (item.get("cmd") or item.get("action")):
                errs.append(f"{body_key}[{i}] missing cmd|action")
    return errs

if __name__ == "__main__":
    text = open(sys.argv[1]).read() if len(sys.argv) > 1 else sys.stdin.read()
    doc = yaml.safe_load(text)
    if not isinstance(doc, dict):
        print("🔴 not a mapping", file=sys.stderr); sys.exit(1)
    errs = errors(doc)
    if errs:
        for e in errs: print(f"🔴 {e}", file=sys.stderr)
        sys.exit(1)
    print("🟢 workflow valid")
