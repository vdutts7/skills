---
name: twitter
description: "User timeline and activity via syndication endpoint. Trigger: /twitter, user timeline, social intel, scrape tweets."
---

# /twitter

## Planes

```yaml
control: SKILL.md
data:
  graphql:  registry/twitter-graphql.json  # endpoints, query IDs, features blobs, bearer, WOEIDs
execution:
  entry:    scripts/twittercli.py
verify: tests/smoke.sh
```

## Subcommands

```yaml
tweet:        "--tweet ID|URL (cascade: fxtwitter -> GraphQL TweetResultByRestId)"
search:       "--search QUERY [--deep] (DDG site:x.com -> cascade resolve)"
user:         "--user HANDLE [--exhaust] [--profile-only] (GraphQL UserByScreenName + UserTweets)"
users:        "--users FILE|CSV (batch with resume)"
trends:       "--trends [--woeid N] (v1.1 guest API)"
refresh-qids: "--refresh-qids (rip x.com JS bundle for current query IDs)"
```

## Flags

```yaml
--json: "stdout JSON, no file write"
--output: "output directory (default: ./x-data)"
--max-results: "max results per search (default: 50)"
--delay: "delay between requests (default: 1.0)"
--deep: "rotated multi-query DDG search for max coverage"
--exhaust: "GQL 99 + DDG sweep for max tweets per user"
--workers: "parallel resolve workers (default: 1)"
--cookie-file: "optional auth boost (see --help-auth)"
--debug: "print raw responses"
--no-resume: "don't resume multi-user from state file"
--dry-run: "print plan only"
```

## Capabilities

```yaml
anonymous_guest_token:
  user_profile: "full (name, bio, followers, following, avatar, banner, created_at)"
  user_tweets: "~99 top by engagement, no pagination cursor"
  single_tweet: "cascade fxtwitter (bookmarks, source, lang, full author) -> GQL"
  search: "DDG site:x.com -> cascade resolve (--deep for rotation)"
  trends: "50 per location via v1.1"
  thread_replies: "not available (TweetDetail auth-gated)"

with_cookie_file:
  unlocks: ["SearchTimeline", "TweetDetail", "pagination cursors", "thread replies"]
```

## Decision tree

```yaml
user_wants_tweet:
  has_id_or_url: "--tweet ID|URL"
  wants_thread: "thread replies require --cookie-file"

user_wants_search:
  broad_topic: "--search QUERY --deep"
  specific:    "--search QUERY"

user_wants_user_data:
  single:       "--user HANDLE"
  max_coverage: "--user HANDLE --exhaust"
  profile_only: "--user HANDLE --profile-only"
  multiple:     "--users FILE|CSV"

user_wants_trends:
  worldwide:     "--trends"
  specific_city: "--trends --woeid WOEID"

user_wants_more_data: "--exhaust for GQL+DDG sweep, --deep for rotated search, --cookie-file for auth boost"
query_ids_stale: "--refresh-qids"
```

## Invariants

```yaml
- never_ask: [which handle, which format, permission]
- run_always: "never describe what it would do"
- session_bootstrap: "GET x.com/ for cookies before any GQL call"
- token_rotation: "fresh guest token every 15 requests"
- cascade_order: "fxtwitter first (richer), GQL fallback"
- atomic_writes: "all output via tmp + rename"
- resume: "multi-user state persisted to .user_state.json"
```
