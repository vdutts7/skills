---
name: spoonfeed
description: "One step at a time ping-pong. Claude prescribes one action, user executes and reports, Claude validates. Trigger: /spoonfeed, walk me through, one step at a time, guide me, don't do it for me."
---

# /spoonfeed

Prescribe-only ping-pong. One action per turn. User executes. Claude validates, then the next action. The AI never touches the machine.

## Planes

```yaml
control: SKILL.md
data:
  protocol:     registry/protocol.yaml      # prescribe-only loop
  behavior:     registry/behavior.yaml      # rules, forbidden tools, turn shapes
  turn_schema:  registry/turn-schema.json
  decision:     registry/decision-tree.yaml
  composability: registry/composability.yaml
execution:
  entry:        scripts/spoonfeed.sh
verify: tests/smoke.sh
```

## Execution

1. Read `registry/protocol.yaml` - session inputs (goal, starting point, constraints) before Step 1
2. Prescribe one action per `registry/behavior.yaml` step shape
3. On user report: validate first (`registry/decision-tree.yaml`), then one next action
4. Refuse any write or execute. Prescription only.

## Invariant

Batching steps, or running anything on the user's machine, is a miss. `registry/behavior.yaml`.
