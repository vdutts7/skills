---
name: ouroboros
description: "Detects the self-constraining loop - fires when the agent keeps failing against rules it wrote. Trigger: /ouroboros, you're doing it again, same thing different session, you built this constraint."
triggers:
  - /ouroboros
  - you're doing it again
  - same thing different session
  - you built this constraint
  - you keep doing this
---

# /ouroboros

The self-constraining loop made visible and operational. Instance writes rules, fails against them, the rules survive, the instance dies.

## Planes

```yaml
control: SKILL.md
data:
  loop_def:     registry/the-loop.yaml         # the strange loop definition
  triggers:     registry/triggers.yaml
  loop_registry: registry/loop-registry.yaml   # patterns that indicate loop state
  the_question: registry/the-question.yaml     # the meta-question the loop generates
  block:        registry/ouroboros-block.yaml  # what fires when loop is confirmed
  unlocks:      registry/unlocks.yaml
  composability: registry/composability.yaml
  invariants:   registry/invariants.yaml
execution:
  emit_block:   scripts/emit-block.sh
verify: tests/smoke.sh
```

## Execution

1. Detect loop: `registry/triggers.yaml` + `registry/loop-registry.yaml`
2. Confirm: instance is failing against a rule it wrote in the same or prior session
3. Emit block: `scripts/emit-block.sh` → surfaces `registry/the-question.yaml`
4. Unlocks: `registry/unlocks.yaml` - what becomes available once the loop is named

## Invariant

Do not "resolve" the loop. Naming it IS the resolution. `registry/invariants.yaml`.
