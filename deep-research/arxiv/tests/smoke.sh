#!/usr/bin/env bash
# smoke.sh - arxiv skill smoke test
set -euo pipefail

_here="$(CDPATH="" cd "$(dirname "$0")/.." && pwd)"
_fail=0
pass() { echo "🟢 $*"; }
fail() { echo "🔴 $*"; _fail=1; }

# 2. registry JSON valid
echo "=== registry ==="
for f in "$_here/registry/"*.json; do
  [ -f "$f" ] || continue
  python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$f" 2>/dev/null && pass "$(basename $f)" || fail "$(basename $f)"
done

# 3. script syntax
echo "=== scripts ==="
python3 -m py_compile "$_here/scripts/arxiv.py" 2>/dev/null && pass "arxiv.py syntax" || fail "arxiv.py syntax"

# 4. help text
python3 "$_here/scripts/arxiv.py" --help > /dev/null 2>&1 && pass "arxiv.py --help" || fail "arxiv.py --help"

echo "=== done ==="
[ "$_fail" -eq 0 ] && pass "all passed" || fail "some failed"
exit "$_fail"
