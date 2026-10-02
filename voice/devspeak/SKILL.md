---
name: devspeak
description: "Developer voice compression -- terse bullets, no qualifiers, 90% adjective cut. Trigger: /devspeak, compress this, write for engineers."
---

# /devspeak

Any written surface. Route only; data in `registry/`; gate in `scripts/`.

## Planes

```yaml
control: SKILL.md
data:
  manifest:    registry/manifest.json        # routes map; read first
  preferences: registry/user-preferences.yaml
  banned:      registry/banned-phrases.json
  operator:    registry/operator-preferences.json
  core:        registry/core.yaml
  logic_flow:  registry/logic-flow.yaml
  antipatterns: registry/antipatterns.json
execution:
  gate:        scripts/devspeak-gate.sh      # mandatory on rewrite/audit; exit 0 before delivery
  engine:      scripts/gate.py
verify: tests/smoke.sh
```

## Execution

```yaml
on_invoke:
  1_read: "registry/manifest.json"
  2_read: "registry/user-preferences.yaml -> registry/banned-phrases.json + registry/operator-preferences.json"
  3_read: "registry/core.yaml"
  4_resolve: "target from selection, draft, open file, or @-mention"
  5_mode:
    rewrite: "pipeline phases 1-7 then MANDATORY scripts/devspeak-gate.sh on output"
    draft:   "phases 1-2 only; no gate"
    audit:   "scripts/devspeak-gate.sh only"
  6_post_gate:
    mandatory: true
    when: [rewrite, audit]
    on_fail: "fix and re-run until exit 0"
    hits: [BP-*, DS-*]
```

## Pipeline

```yaml
1_dump:        "passive first ideas- fragments ok"
2_cluster:     "semantically similar bullets together"
3_consolidate: "dedupe; merge without losing meaning"
4_nest:        "parent=cluster; child=specifics when line would wall"
5_delimit:     "allowed delimiters only; backtick code/paths/commands"
6_logic_flow:  "reshape to if/then decision tree- reads like code logic not essay"
7_preferences: "apply registry/user-preferences.yaml term map + bullet cap rule + forbidden patterns"
```

## Decision tree

```yaml
user_invokes_devspeak:
  target_clear:
    rewrite: "pipeline 1-7 -> mandatory gate -> exit 0 before delivery"
    draft:   "pipeline 1-2 only; skip gate"
    audit:   "gate only; report BP-* + DS-*"
  target_ambiguous: "ask once: rewrite, draft, or audit?"

bullet_capitalization: "lowercase first word after - unless proper noun or acronym"
logic_flow_shape:
  sequential: "use -> chain or nested bullets"
  conditional: "if X -> Y or if_yes/if_no nest"
  essay_tone: "strip transitions; restructure to decision tree"
```

## Cross refs

```yaml
read_first: registry/manifest.json
then:
  - registry/user-preferences.yaml
  - registry/banned-phrases.json
  - registry/operator-preferences.json
  - registry/core.yaml
  - registry/logic-flow.yaml
  - registry/antipatterns.json
  - scripts/devspeak-gate.sh
  - scripts/gate.py
```
