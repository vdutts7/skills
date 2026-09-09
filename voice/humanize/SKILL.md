---
name: humanize
description: "Anti-AI-tell output pass -- 28 laws, mandatory pre-delivery. Strips em-dashes, significance inflation, chatbot openers. Trigger: /humanize or co-fires on any output."
---

# humanize

Always-on pre-delivery pass. 28 laws. Zero exceptions.

## Planes

```yaml
control: SKILL.md
data:
  laws:         registry/laws.json          # R-000..R-027: all detection patterns + reflexes
  execution:    registry/execution.json     # phase order; R-000 fires first (hard sanitizer)
  verification: registry/verification.json  # mandatory pre-delivery checklist
  mode:         registry/mode.json
  quick_ref:    registry/quick-reference.json
execution:
  sanitize:     scripts/sanitize.py         # R-000 hard invariant: em-dash/en-dash -> hyphen
  sanitize_sh:  scripts/sanitize.sh
verify: tests/smoke.sh
```

## Execution

1. **R-000 first** (always): `scripts/sanitize.py` -- hard em-dash removal; no exceptions, no surface exemptions
2. **R-001..R-027**: apply per `registry/laws.json`; each entry has `class`, `forbidden`, `reflex`, `examples`
3. **Verify**: `registry/verification.json` -- mandatory pre-delivery checklist; fail = rewrite
4. **Order**: `registry/execution.json`

## Invariant

All 28 laws in `registry/laws.json`. SKILL.md is routing only -- rules do not live here.
