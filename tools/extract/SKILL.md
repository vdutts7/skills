---
name: extract
description: "Deep entity and command extractor, rabid-raccoon mode - does not skim. Trigger: /extract, extract everything, don't miss anything, full extraction pass."
triggers:
  - /extract
  - extract everything
  - don't miss anything
  - full extraction pass
  - rabid extraction
  - exhaust this
---

# /extract

Rabid-raccoon extraction. Digs until there is nothing left to find. Does not skim.

## Planes

```yaml
control: SKILL.md
data:
  role:            registry/role.yaml
  rules:           registry/extraction-rules.yaml
  probe_mode:      registry/probe-mode.yaml
  flags:           registry/flags.yaml
  output_formats:  registry/output-formats.yaml
  antipatterns:    registry/antipatterns.yaml
  dogma:           registry/dogma.yaml
  handoff:         registry/handoff.yaml
  usage:           registry/usage.yaml
  suggest_files:   registry/suggest-files.yaml
execution:
  probe:           scripts/probe-passes.py
verify: tests/smoke.sh
```

## Execution

1. Role entry: `registry/role.yaml` - rabid raccoon; not a summarizer
2. Flags: `registry/flags.yaml` - `--strict`, `--probe`, `--suggest-files`
3. Run passes: `scripts/probe-passes.py` per `registry/probe-mode.yaml`
4. Output: `registry/output-formats.yaml`
5. Anti-skim check: `registry/antipatterns.yaml` - if anything was skipped, it wasn't extraction

## Invariant

`registry/dogma.yaml`: extraction is complete or it is wrong. Partial extraction = no extraction.
