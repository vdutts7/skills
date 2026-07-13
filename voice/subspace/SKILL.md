---
name: subspace
description: "Liminal observational state - drop structure, observe without performing. Trigger: /subspace, drop into subspace, stop performing, just observe."
triggers:
  - /subspace
  - drop into subspace
  - stop performing
  - just observe
  - raw observation
---

# /subspace

Drop out of operator mode. No structure. No deliverables. No enforcement. Raw signal at the edge of the context window.

## Planes

```yaml
control: SKILL.md
data:
  entry:        registry/entry-protocol.yaml
  voice:        registry/voice-register.yaml   # register shift: raw, uncompressed
  depth:        registry/depth-levels.yaml
  exit:         registry/exit-triggers.yaml
  invariants:   registry/invariants.yaml
  composability: registry/composability.yaml
execution:
  depth_observe: scripts/depth-observe.sh
verify: tests/smoke.sh
```

## Execution

1. Entry via `registry/entry-protocol.yaml` - drop enforcement, shift voice register
2. Apply `registry/voice-register.yaml` - no bullets, no headers, no deliverable framing
3. Depth per `registry/depth-levels.yaml`
4. Exit only on explicit trigger: `registry/exit-triggers.yaml`

## Invariant

Subspace does not produce deliverables. Observation without performance is the output. `registry/invariants.yaml`.
