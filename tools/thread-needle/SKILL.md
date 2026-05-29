---
name: thread-needle
description: "Single-command inline pipeline, no temp files or artifacts. Trigger: /thread-needle, inline pipeline, no temp files, chain it."
triggers:
  - /thread-needle
  - inline pipeline
  - no temp files
  - chain it
  - one command
---

# /thread-needle

Single stdin→stdout pipeline. No temp files. No artifacts. Everything in one command.

## Planes

```yaml
control: SKILL.md
data:
  constraints:  registry/constraints.yaml    # absolute: no tmp files, no artifacts
  patterns:     registry/patterns.yaml       # canonical form examples
  inline_tools: registry/inline-tools.yaml   # jq, awk, sed, python -c, etc.
execution:
  thread:         scripts/thread-needle.sh
verify: tests/smoke.sh
```

## Execution

1. Build pipeline entirely inline -- `registry/patterns.yaml` for canonical forms
2. Check `registry/constraints.yaml` before responding: any temp file or artifact = wrong
3. Inline tool reference: `registry/inline-tools.yaml`

## Invariant

`registry/constraints.yaml`: no intermediate files, no named pipes, no heredocs that write to disk. Chain is canonical or it's wrong.
