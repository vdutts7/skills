---
name: machreadify
description: "Prose to structured JSON or YAML. Trigger: /machreadify, structure this, make this machine-readable, convert to JSON."
triggers:
  - /machreadify
  - structure this
  - make this machine-readable
  - convert to JSON
  - convert to YAML
---

# /machreadify

Prose → machine-readable structured output. Format and scope selected from registry; no novel schema invention.

## Planes

```yaml
control: SKILL.md
data:
  format_selection:  registry/format-selection.yaml
  scope_selection:   registry/scope-selection.yaml
  targets:           registry/conversion-targets.yaml
  principles:        registry/principles.yaml
  execution:         registry/execution.yaml
  output_format:     registry/output-format.yaml
execution:
  detect:            scripts/detect-format.py
verify: tests/smoke.sh
```

## Execution

1. Detect format: `scripts/detect-format.py` or `registry/format-selection.yaml`
2. Select scope: `registry/scope-selection.yaml`
3. Convert per `registry/conversion-targets.yaml`
4. Validate output per `registry/output-format.yaml`

## Invariant

`registry/principles.yaml`: preserve all information; no lossy summarization during conversion.
