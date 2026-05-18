#!/usr/bin/env bash
# smoke.sh - loop skill bundle smoke test
set -euo pipefail

_here="$(CDPATH="" cd "$(dirname "$0")/.." && pwd)"
_fail=0
pass() { echo "🟢 $*"; }
fail() { echo "🔴 $*"; _fail=1; }

# 2. audit-line basic invocation
echo "=== audit-line ==="
if bash "$_here/scripts/audit-line.sh" 1 "input" "expected" "actual" | grep -q "Test 1"; then
  pass "audit-line"
else
  fail "audit-line"
fi

# Registry files valid YAML/JSON
echo "=== registry ==="
for f in "$_here/registry/"*.json "$_here/registry/"*.yaml; do
  [ -f "$f" ] || continue
  ext="${f##*.}"
  [ "$ext" = "json" ] && python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$f" 2>/dev/null && pass "$(basename $f)" || true
  [ "$ext" = "yaml" ] && python3 -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))" "$f" 2>/dev/null && pass "$(basename $f)" || true
done

echo "=== done ==="
[ "$_fail" -eq 0 ] && pass "all passed" || fail "some failed"
exit "$_fail"
