---
name: loop
description: "Iterative test-fix loop until green. Trigger: /loop, keep trying until it passes, retry until green, loop until exit 0."
triggers:
  - /loop
  - keep trying until it passes
  - retry until green
  - loop until exit 0
  - don't stop until it works
---

# /loop

Run → fail → diagnose → fix → repeat until green or iteration cap hit.

## Planes

```yaml
control: SKILL.md
data:
  modes:        registry/modes.yaml           # test-fix vs generic
  triggers:     registry/triggers.yaml
  rules:        registry/rules.yaml
  antipatterns: registry/antipatterns.yaml
  composability: registry/composability.yaml
execution:
  test_fix:     registry/test-fix-protocol.yaml
  generic:      registry/generic-loop.yaml
  audit_line:   scripts/audit-line.sh
verify: tests/smoke.sh
```

## Execution

1. Identify mode: `registry/modes.yaml`
2. Run protocol: `registry/test-fix-protocol.yaml` or `registry/generic-loop.yaml`
3. Line-level diagnostics: `scripts/audit-line.sh`
4. Never ask permission to retry; never summarize failed attempts; `registry/antipatterns.yaml`

## Invariant

Max 10 iterations. On cap: report last failure verbatim, stop.
