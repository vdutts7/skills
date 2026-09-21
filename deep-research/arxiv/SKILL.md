---
name: arxiv
description: "arXiv paper search, fetch by ID, recent by category. Trigger: /arxiv, find papers on, search arxiv, recent cs.AI papers, fetch abstract."
---

# /arxiv

Public arXiv API. No auth. Atom XML parsed with stdlib.

## Planes

```yaml
control: SKILL.md
data:
  endpoints:   registry/endpoints.json    # API surface
  categories:  registry/categories.json   # cs/math/stat/econ/q-bio codes
execution:
  entry:       scripts/arxiv.py
verify: tests/smoke.sh
```

## Execution

```yaml
on_invoke:
  1_read: "registry/endpoints.json"
  2_route: "match subcommand"
  3_run: "scripts/arxiv.py <subcommand> [args]"

subcommands:
  search: "query arXiv full-text search - arxiv.py search '<query>' [--max 10] [--cat cs.AI]"
  paper:  "fetch single paper by ID - arxiv.py paper <arxiv-id>  (e.g. 2303.08774)"
  recent: "list recent submissions in a category - arxiv.py recent <cat> [--max 20]"
```

## Decision tree

```yaml
intent:
  search_by_topic: "search '<topic>' [--cat <cat>]"
  known_id: "paper <id>"
  browse_category: "recent <cat>"
  unknown_cat_code:
    - read registry/categories.json
    - match user term to cs/math/stat/econ/q-bio etc.
```

## Output format

```yaml
per_paper:
  id: "arXiv ID (e.g. 2303.08774)"
  title: string
  authors: list
  abstract: string (first 300 chars unless --full)
  published: date
  categories: list
  pdf: "https://arxiv.org/pdf/<id>"
  abs: "https://arxiv.org/abs/<id>"
```

## Constraints

```yaml
rate: "no enforced limit on public API; be civil - 1 req/s default"
auth: "none required"
format: "Atom XML feed - parsed with stdlib xml.etree.ElementTree"
max_results: "100 per call (arXiv enforces server-side)"
```
