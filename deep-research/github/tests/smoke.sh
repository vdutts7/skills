#!/usr/bin/env bash
# smoke.sh - github skill smoke test
set -euo pipefail

_here="$(CDPATH="" cd "$(dirname "$0")/.." && pwd)"
_fail=0
pass() { echo "🟢 $*"; }
fail() { echo "🔴 $*"; _fail=1; }

# 2. registry JSON valid
echo "=== registry ==="
python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$_here/registry/endpoints.json" 2>/dev/null \
  && pass "endpoints.json" || fail "endpoints.json"

# 3. script syntax
echo "=== scripts ==="
python3 -m py_compile "$_here/scripts/github.py" 2>/dev/null && pass "github.py syntax" || fail "github.py syntax"

# 4. help text
python3 "$_here/scripts/github.py" --help > /dev/null 2>&1 && pass "github.py --help" || fail "github.py --help"

echo "=== done ==="
[ "$_fail" -eq 0 ] && pass "all passed" || fail "some failed"
exit "$_fail"
