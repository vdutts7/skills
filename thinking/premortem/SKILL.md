---
name: premortem
description: "Prospective hindsight - assumes failure and works backward to find every reason why. Trigger: /premortem, premortem this, what could kill this, stress test this plan, find the blind spots, what am I missing."
triggers:
  - /premortem
  - premortem this
  - premortem my
  - what could kill this
  - future-proof this
  - stress test this plan
  - what am i missing here
  - find the blind spots
  - what could go wrong
  - poke holes in this
  - where will this break
  - devil's advocate this
skip:
  - simple feedback requests
  - factual questions
---

# /premortem

Frame: **this already failed 6 months from now. Why?**

The frame shift is the whole mechanism - "what could go wrong?" produces hedged answers; "this is dead, explain how it died" produces specific, honest ones.

## Planes

```yaml
control: SKILL.md             # you are here - routing table
data:
  when_to_run:    registry/when-to-run.yaml
  context:        registry/context-gathering.yaml
  session_flow:   registry/session-flow.yaml
  output_format:  registry/output-format.yaml
  temporal_triad: registry/temporal-triad.yaml
  notes:          registry/important-notes.yaml
  example:        registry/example.yaml
execution:
  scaffold:       scripts/scaffold-report.sh
verify:           tests/smoke.sh
```

## Execution

1. Load context from `registry/context-gathering.yaml` - check what exists before asking
2. Run session via `registry/session-flow.yaml` (6 steps: frame → raw-dump → deep-dive agents → synthesis → report → save)
3. Emit report per `registry/output-format.yaml`
4. After synthesis: if they want an execution order, sequence it as a separate pass (`registry/temporal-triad.yaml`)

## Invariant

Do not blend premortem (future failure frame) with execution sequencing or retrospective. Different temporal frames, different outputs. `registry/temporal-triad.yaml`.

