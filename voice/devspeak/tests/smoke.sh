#!/usr/bin/env bash
# smoke.sh - devspeak skill bundle verify
set -eo pipefail

HERE="$(cd "$(dirname "$0")/.." && pwd)"
GATE="$HERE/scripts/devspeak-gate.sh"
FIX="$HERE/tests/fixtures"
MANIFEST="$HERE/registry/manifest.json"
_fail=0

pass() { echo "🟢 $*"; }
fail() { echo "🔴 $*"; _fail=1; }

echo "=== manifest routes ==="
for key in entry core logic_flow antipatterns banned_phrases operator_preferences; do
  rel="$(python3 -c "import json; print(json.load(open('$MANIFEST'))['routes']['$key'])")"
  if [[ -f "$HERE/registry/$rel" ]]; then
    pass "route $key -> $rel"
  else
    fail "route $key missing: $rel"
  fi
done

echo "=== devspeak-gate fixtures ==="
chmod +x "$GATE" "$HERE/scripts/gate.py" 2>/dev/null || true

if "$GATE" "$FIX/good.sample.md"; then pass "good fixture pass"; else fail "good fixture should pass"; fi
if "$GATE" "$FIX/bad.sample.md"; then fail "bad fixture should fail"; else pass "bad fixture fail as expected"; fi

python3 -c "import json; json.load(open('$HERE/registry/banned-phrases.json'))" && pass "banned-phrases.json valid"
python3 -c "import json; json.load(open('$HERE/registry/operator-preferences.json'))" && pass "operator-preferences.json valid"

[ "$_fail" -eq 0 ] && pass "smoke-ok" || fail "smoke-fail"
exit "$_fail"
