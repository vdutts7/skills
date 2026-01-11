#!/usr/bin/env bash
# smoke.sh - redfin skill
set -euo pipefail
_here="$(CDPATH="" cd "$(dirname "$0")/.." && pwd)"
_fail=0
pass() { echo "🟢 $*"; }
fail() { echo "🔴 $*"; _fail=1; }

echo "=== registry ==="
python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$_here/registry/stingray.json" && pass "stingray.json" || fail "stingray.json"

echo "=== scripts ==="
python3 -m py_compile "$_here/scripts/redfin-stingray.py" && pass "redfin-stingray.py syntax" || fail "redfin-stingray.py syntax"
python3 "$_here/scripts/redfin-stingray.py" --help >/dev/null && pass "redfin-stingray.py --help" || fail "redfin-stingray.py --help"

echo "=== done ==="
[ "$_fail" -eq 0 ] && pass "all passed" || fail "some failed"
exit "$_fail"
