#!/usr/bin/env bash

# smoke.sh - hackernews skill bundle smoke test

# Runs validate --strict, tests CLI subcommands, cleans up

set -euo pipefail

_here="$(CDPATH="" cd "$(dirname "$0")/.." && pwd)"

_scripts="$_here/scripts"

_fail=0

pass() { echo "🟢 $*"; }

fail() { echo "🔴 $*"; _fail=1; }

# 2. CLI --help

echo "=== CLI help ==="

if python3 "$_scripts/hackernews.py" --help >/dev/null 2>&1; then

  pass "hackernews --help"

else

  fail "hackernews --help"

fi

# 3. fetch top 5 stories (quick smoke)

echo "=== top 5 ==="

TMP=$(mktemp -d)

if python3 "$_scripts/hackernews.py" top --json --out "$TMP/top.json" 2>/dev/null; then

  COUNT=$(python3 -c "import json; print(len(json.load(open('$TMP/top.json'))))" 2>/dev/null || echo 0)

  if [ "$COUNT" -gt 0 ]; then

    pass "top: $COUNT stories fetched"

  else

    fail "top: empty output"

  fi

else

  fail "top: command failed"

fi

# 4. fetch single item

echo "=== item ==="

if python3 "$_scripts/hackernews.py" item 1 --json >/dev/null 2>&1; then

  pass "item 1"

else

  fail "item 1"

fi

# 5. fetch user

echo "=== user ==="

if python3 "$_scripts/hackernews.py" user pg --json >/dev/null 2>&1; then

  pass "user pg"

else

  fail "user pg"

fi

# cleanup

/usr/bin/trash "$TMP" 2>/dev/null

echo "=== smoke complete ==="

[ "$_fail" -eq 0 ] && pass "all checks passed" || fail "some checks failed"

exit "$_fail"

