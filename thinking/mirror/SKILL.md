---
name: mirror
description: "N-round adversarial self-dialogue: PRIME builds, MIRROR attacks, synthesis resolves. Trigger: /mirror, stress test this, argue against this, find the holes, steelman then attack."
triggers:
  - /mirror
  - stress test this
  - find the holes
  - argue against this
  - steelman then attack
  - devil's advocate
---

# /mirror

N-round adversarial self-dialogue. PRIME builds. MIRROR attacks. Synthesis resolves. Not personas - locked roles.

## Planes

```yaml
control: SKILL.md             # routing table
data:
  personas:   registry/personas.yaml        # role contracts; do not blend
  phases:     registry/phases.yaml          # 4-phase execution
  depth:      registry/depth-levels.yaml    # N rounds calibration
  synthesis:  registry/synthesis-structures.yaml
  rules:      registry/rules.yaml
  errors:     registry/errors.yaml          # loop collapse, drift, persona bleed
  usage:      registry/usage.yaml
execution:
  schema:     scripts/synthesis-schema.sh
verify:       tests/smoke.sh
```

## Execution

1. **Scope** - extract exact claim/plan/argument being interrogated
2. **Depth** - `registry/depth-levels.yaml`; confirm N rounds (default: 3)
3. **Dialogue** - PRIME → MIRROR alternation per `registry/phases.yaml`; role contracts from `registry/personas.yaml`
4. **Synthesis** - `registry/synthesis-structures.yaml`; canonical synthesis after final round

## Invariant

PRIME and MIRROR are locked roles. No blending. Persona bleed → `registry/errors.yaml`.

