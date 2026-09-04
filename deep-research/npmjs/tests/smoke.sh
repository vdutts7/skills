#!/usr/bin/env bash

set -euo pipefail

_here="$(CDPATH="" cd "$(dirname "$0")/.." && pwd)"

_s="$_here/scripts"; _fail=0

pass() { echo "🟢 $*"; }; fail() { echo "🔴 $*"; _fail=1; }

echo "=== help ===" && python3 "$_s/npmcli.py" --help >/dev/null 2>&1 && pass "help" || fail "help"

echo "=== search ===" && python3 "$_s/npmcli.py" search react --top 3 --json >/dev/null 2>&1 && pass "search" || fail "search"

echo "=== info ===" && python3 "$_s/npmcli.py" info lodash --json >/dev/null 2>&1 && pass "info" || fail "info"

echo "=== versions ===" && python3 "$_s/npmcli.py" versions express --top 3 --json >/dev/null 2>&1 && pass "versions" || fail "versions"

echo "=== downloads ===" && python3 "$_s/npmcli.py" downloads react --json >/dev/null 2>&1 && pass "downloads" || fail "downloads"

echo "=== deps ===" && python3 "$_s/npmcli.py" deps express --json >/dev/null 2>&1 && pass "deps" || fail "deps"

echo "=== done ===" && [ "$_fail" -eq 0 ] && pass "all passed" || fail "some failed"

exit "$_fail"

