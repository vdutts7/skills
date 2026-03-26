---
name: potemkin
description: "Constraint extraction and reparameterization - names the actual blocking constraint, tests if it's hard or soft. Trigger: /potemkin, stuck on the same wall, what is actually stopping this, constraint audit."
triggers:
  - /potemkin
  - stuck on the same wall
  - what is actually stopping this
  - constraint audit
  - name the real constraint
  - is this actually a hard constraint
---

# /potemkin

Constraint extraction. Names the constraint, classifies it (hard/soft/false), reparameterizes to find the actual solution space.

## Planes

```yaml
control: SKILL.md
data:
  phases:       registry/phases.yaml        # core loop + constraint classification
  decision:     registry/decision-tree.yaml # terminal state routing
  anti_laziness: registry/anti-laziness.yaml
  usage:        registry/usage.yaml         # when to use / when NOT to use
  potemkin_db:  registry/potemkin.json      # constraint instance database
execution:
  classify:     scripts/classify-constraint.py
verify: tests/smoke.sh
```

## Execution

1. Extract stated constraint verbatim
2. Classify via `registry/phases.yaml`: hard (physical/legal), soft (organizational), false (assumed)
3. `scripts/classify-constraint.py` - apply decision tree
4. Reparameterize: what does the solution space look like if this constraint is soft or false?
5. Check `registry/anti-laziness.yaml` - first classification is not always right

## Invariant

Do not accept "we can't do that" as a terminal state without classification. `registry/decision-tree.yaml`.
