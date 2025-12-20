---
name: hackernews
description: "HN stories, users, and exhaust via Firebase API. Trigger: /hackernews, HN front page, hacker news data, HN user profile."
---

# /hackernews

## Planes

```yaml
control: SKILL.md
data:
  endpoints: registry/endpoints.json   # Firebase API surface map + config
execution:
  entry:     scripts/hackernews.py
verify: tests/smoke.sh
```

## Subcommands

```yaml
top:     "fetch /topstories + item details (default: 30, --all for 500)"
new:     "fetch /newstories + item details"
best:    "fetch /beststories + item details"
ask:     "fetch /askstories + item details"
show:    "fetch /showstories + item details"
jobs:    "fetch /jobstories + item details"
exhaust: "full surface exhaust - all endpoints, all items, all users"
user:    "fetch /user/{username}.json"
item:    "fetch /item/{id}.json"
```

## Flags

```yaml
--all:     "no limit (default caps at 30)"
--json:    "raw JSON output (default: formatted table)"
--out:     "write to file instead of stdout"
--workers: "parallel worker count (default: 8)"
--resume:  "resume from .state.json checkpoint"
```

## Decision tree

```yaml
user_wants_hn_data:
  subcommand_given: "scripts/hackernews.py <subcommand>"
  default: "scripts/hackernews.py top"
  wants_exhaust: "scripts/hackernews.py exhaust"
  wants_user: "scripts/hackernews.py user <username>"
  wants_item: "scripts/hackernews.py item <id>"
user_wants_non_hn_scraping: "route to other deep-research skills"
```

