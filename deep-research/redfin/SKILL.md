---
name: redfin
description: "Real estate listings by market via Stingray API. Trigger: /redfin, real estate search, listings, market comps."
---

# /redfin

## Planes

```yaml
control: SKILL.md
data:
  stingray: registry/stingray.json   # endpoints, params, markets, fields, anti-scrape
execution:
  entry:    scripts/redfin-stingray.py
verify: tests/smoke.sh
```

## Execution

```yaml
flow:
  1_read:   "registry/stingray.json -> endpoints, markets, params"
  2_infer:  "city name -> registry/stingray.json#markets code"
  3_run:    "python3 scripts/redfin-stingray.py --market {code} --output ./redfin-data"
  variants:
    all:  "--all-markets"
    csv:  "--format csv"
    sold: "--status 9"
```

## Invariants

```yaml
- never_ask: [which market, which format, permission]
- infer_market: "city name -> registry/stingray.json#markets code"
- run_always: "never describe what it would do"
```
