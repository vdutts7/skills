#!/usr/bin/env bash
# smoke.sh - yaml-workflow skill bundle smoke test
set -euo pipefail

_here="$(CDPATH="" cd "$(dirname "$0")/.." && pwd)"
_fail=0
pass() { echo "🟢 $*"; }
fail() { echo "🔴 $*"; _fail=1; }

# 2. validate-workflow basic invocation
if python3 "$_here/scripts/validate-workflow.py" <<'EOF'
id: test
version: 1
shape: skeleton_flow
goal: test
steps:
  - id: s1
    cmd: echo test
EOF
then
  pass "validate-workflow"
else
  fail "validate-workflow"
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
