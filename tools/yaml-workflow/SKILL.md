---
name: yaml-workflow
description: "Prose plan to terse YAML workflow with required fields and phases. Trigger: /yaml-workflow, make a workflow, plan as YAML, structure this plan."
triggers:
  - /yaml-workflow
  - make a workflow
  - plan as YAML
  - structure this plan
  - turn this into a workflow
---

# /yaml-workflow

Prose plan → terse YAML workflow. Required fields enforced. No novel schema invention.

## Planes

```yaml
control: SKILL.md
data:
  required_structure:  registry/required-structure.yaml   # mandatory fields
  skeleton:            registry/skeleton-selection.yaml   # which skeleton to use
  step_schema:         registry/step-schema.yaml
  style_rules:         registry/style-rules.yaml
  config_isolation:    registry/config-isolation.yaml
  meta_patterns:       registry/meta-patterns.yaml
  execution_checklist: registry/execution-checklist.yaml
  handoff:             registry/handoff-execution.yaml
  plans_of_plans:      registry/plans-of-plans.yaml
  output:              registry/output-and-plans-copy.yaml
  gotchas:             registry/gotchas-risks.yaml
execution:
  validate:            scripts/validate-workflow.py
verify: tests/smoke.sh
```

## Execution

1. Select skeleton: `registry/skeleton-selection.yaml`
2. Map prose → YAML per `registry/step-schema.yaml` + `registry/required-structure.yaml`
3. Apply `registry/style-rules.yaml` (terse; no prose inside yaml values)
4. Validate: `scripts/validate-workflow.py`
5. Apply meta-patterns: `registry/meta-patterns.yaml` (parallel steps, conditional branches)

## Invariant

`registry/required-structure.yaml`: missing required fields = invalid. Do not ship.
