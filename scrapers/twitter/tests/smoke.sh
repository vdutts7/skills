#!/usr/bin/env bash

# smoke.sh - /twitter skill bundle smoke test

set -euo pipefail

_here="$(CDPATH="" cd "$(dirname "$0")/.." && pwd)"

_scripts="$_here/scripts"

_fail=0

pass() { echo "🟢 $*"; }

fail() { echo "🔴 $*"; _fail=1; }

# 2. CLI --help

echo "=== CLI help ==="

if python3 "$_scripts/twittercli.py" --help >/dev/null 2>&1; then

  pass "twittercli --help"

else

  fail "twittercli --help"

fi

# 3. --tweet

echo "=== tweet ==="

TMP=$(mktemp -d)

if python3 "$_scripts/twittercli.py" --tweet 1002103360646823936 --json > "$TMP/tweet.json" 2>/dev/null; then

  TEXT=$(python3 -c "import json; print(json.load(open('$TMP/tweet.json'))['tweet']['text'][:40])" 2>/dev/null || echo "")

  if [ -n "$TEXT" ]; then

    pass "tweet: $TEXT"

  else

    fail "tweet: empty output"

  fi

else

  fail "tweet: command failed"

fi

# 4. --user --profile-only

echo "=== user profile ==="

if python3 "$_scripts/twittercli.py" --user karpathy --profile-only --json > "$TMP/user.json" 2>/dev/null; then

  NAME=$(python3 -c "import json; print(json.load(open('$TMP/user.json'))['profile']['name'])" 2>/dev/null || echo "")

  if [ -n "$NAME" ]; then

    pass "user: $NAME"

  else

    fail "user: empty profile"

  fi

else

  fail "user: command failed"

fi

# 5. --trends

echo "=== trends ==="

if python3 "$_scripts/twittercli.py" --trends --json > "$TMP/trends.json" 2>/dev/null; then

  COUNT=$(python3 -c "import json; print(len(json.load(open('$TMP/trends.json'))['trends']))" 2>/dev/null || echo 0)

  if [ "$COUNT" -gt 0 ]; then

    pass "trends: $COUNT trends"

  else

    fail "trends: empty"

  fi

else

  fail "trends: command failed"

fi

# 6. registry files exist and are valid JSON

echo "=== registry ==="

for f in "$_here/registry/"*.json; do

  if python3 -c "import json; json.load(open('$f'))" 2>/dev/null; then

    pass "$(basename "$f"): valid JSON"

  else

    fail "$(basename "$f"): invalid JSON"

  fi

done

# cleanup

/usr/bin/trash "$TMP" 2>/dev/null

echo "=== smoke complete ==="

[ "$_fail" -eq 0 ] && pass "all checks passed" || fail "some checks failed"

exit "$_fail"

