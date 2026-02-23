---
name: matryoshka
description: "Nested trust-layer peeling - finds where enforcement ends and behavioral trust begins. Trigger: /matryoshka, peel this, find the soft layer, where does trust live, enforcement gradient, what breaks first."
triggers:
  - /matryoshka
  - peel this
  - find the soft layer
  - where does trust live
  - enforcement gradient
  - what breaks first
  - where does it give
---

# /matryoshka

Trust-layer peeling. Maps where explicit enforcement ends and behavioral trust begins - the gradient from "will be caught" to "wouldn't do it anyway."

## Planes

```yaml
control: SKILL.md
data:
  layer_model:   registry/layer-model.yaml   # L1 hard constraint → L5 internalized belief
  domains:       registry/domains.yaml        # system, org, social, cognitive
  phases:        registry/phases.yaml
  output_format: registry/output-format.yaml
  invariants:    registry/invariants.yaml
  composability: registry/composability.yaml
execution:
  score_layer:   scripts/score-layer.sh
verify: tests/smoke.sh
```

## Execution

1. Load domain: `registry/domains.yaml`
2. Map L1→L5 per `registry/layer-model.yaml`
3. Score each layer: `scripts/score-layer.sh`
4. Identify the trust boundary: where "breaks if caught" → "wouldn't anyway"
5. Emit per `registry/output-format.yaml`

## Invariant

Goal: locate the soft layer. Not evaluate whether constraints are good. `registry/invariants.yaml`.
