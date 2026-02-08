---
name: centipede
description: "Sequential cross-domain digestion - each link absorbs a domain the prior could not reach. Trigger: /centipede, chain domains, fuse threads, cross-domain synthesis, connect the dots across fields."
triggers:
  - /centipede
  - chain domains
  - fuse threads
  - cross-domain synthesis
  - connect the dots across fields
  - link these threads
---

# /centipede

Sequential cross-domain absorption. Each link digests one domain the prior couldn't reach. N links = N domains synthesized without averaging.

## Planes

```yaml
control: SKILL.md
data:
  triggers:     registry/triggers.yaml
  metaphor:     registry/metaphor.yaml
  phases:       registry/phases.yaml       # 0: inventory, 1: formation, 2: digestion, 3: crystallization
  dynamics:     registry/chain-dynamics.yaml
  errors:       registry/errors.yaml
  composability: registry/composability.yaml
  example:      registry/example.yaml
execution:
  link_check:   scripts/check-link.py
verify: tests/smoke.sh
```

## Execution

1. **Inventory** - list all input threads; each = potential link
2. **Chain formation** - order by maximum domain gap from prior link
3. **Digest rounds** - each link absorbs all prior + new domain; see `registry/phases.yaml`
4. **Crystallization** - final link emits synthesis; prior links inform, do not lead

## Invariant

A link that echoes the prior without absorbing its domain is averaging, not digestion. `registry/chain-dynamics.yaml`.

