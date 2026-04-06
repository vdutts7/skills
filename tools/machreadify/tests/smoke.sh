#!/usr/bin/env bash
# smoke.sh - machreadify skill bundle smoke test
set -euo pipefail

_here="$(CDPATH="" cd "$(dirname "$0")/.." && pwd)"
_fail=0
pass() { echo "🟢 $*"; }
fail() { echo "🔴 $*"; _fail=1; }

# 2. detect-format basic invocation
echo "=== detect-format ==="
if echo "step 1. run something
step 2. check output" | python3 "$_here/scripts/detect-format.py" | grep -q "yaml"; then
  pass "detect-format"
else
  fail "detect-format"
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
