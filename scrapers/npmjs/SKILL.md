---
name: npmjs
description: "npm package lookup, download stats, dependents. Trigger: /npmjs, npm package info, dep review, supply chain audit."
---

# /npmjs

## Planes

```yaml
control: SKILL.md
data:
  endpoints: registry/endpoints.json
  schemas:   registry/schemas.json
  cli:       registry/cli.json
execution:
  entry:     scripts/npmcli.py     # avoids clashing with Node npm on PATH
verify: tests/smoke.sh
```

## Subcommands

```yaml
search:    "search packages by query (/-/v1/search)"
info:      "package metadata (abbreviated by default, --full for complete)"
versions:  "list all versions with timestamps"
downloads: "download stats (last-day, last-week, last-month, or date range)"
deps:      "dependency tree for latest or specific version"
exhaust:   "full metadata dump plus all versions plus download history"
```

## Flags

```yaml
--json: "raw JSON output"
--full: "full metadata instead of abbreviated (info subcommand)"
--out:  "write to file"
--top:  "limit results (search default 20, versions default 10)"
```

## Decision tree

```yaml
user_wants_npm_data:
  search:       "scripts/npmcli.py search <query> [--top N]"
  package_info: "scripts/npmcli.py info <package> [--full]"
  versions:     "scripts/npmcli.py versions <package> [--top N]"
  downloads:    "scripts/npmcli.py downloads <package> [--period last-week]"
  deps:         "scripts/npmcli.py deps <package> [--version x.y.z]"
  exhaust:      "scripts/npmcli.py exhaust <package> [--out FILE]"
not_npm: "route elsewhere"
```

