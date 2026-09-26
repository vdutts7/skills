---
name: github
description: "GitHub repo metadata, user profiles, search, releases, issues via public API v3. Trigger: /github, look up repo, github user, repo stars, open issues, latest release."
---

# /github

GitHub API v3. Optional token for rate limits. REST only.

## Planes

```yaml
control: SKILL.md
data:
  endpoints: registry/endpoints.json
execution:
  entry:     scripts/github.py
verify: tests/smoke.sh
```

## Execution

```yaml
on_invoke:
  1_read: "registry/endpoints.json"
  2_route: "match subcommand"
  3_run: "scripts/github.py <subcommand> [args]"
  auth: "set GITHUB_TOKEN env var for higher rate limits (optional)"

subcommands:
  repo:     "fetch repo metadata - github.py repo <owner/name>"
  user:     "fetch user profile + public repos - github.py user <username>"
  search:   "search repos or code - github.py search '<query>' [--type repos|code|users]"
  releases: "list releases for a repo - github.py releases <owner/name> [--max 5]"
  issues:   "list open issues - github.py issues <owner/name> [--max 20] [--state open|closed]"
```

## Decision tree

```yaml
intent:
  know_repo: "repo <owner/name>"
  know_user: "user <username>"
  searching: "search '<query>' --type repos"
  want_releases: "releases <owner/name>"
  want_issues: "issues <owner/name>"
  rate_limited:
    - set GITHUB_TOKEN from environment
    - retry
```

## Auth

```yaml
unauthenticated: "60 req/hr - sufficient for one-off lookups"
token:
  env: GITHUB_TOKEN
  header: "Authorization: Bearer $GITHUB_TOKEN"
  rate: "5000 req/hr"
  scope: "public_repo read:user (no write scopes needed)"
```

## Constraints

```yaml
format: "JSON (GitHub API v3)"
pagination: "--max controls how many items fetched (default caps per subcommand)"
private_repos: "requires token with repo scope - out of scope for this skill"
graphql: "not supported - use REST only"
```
