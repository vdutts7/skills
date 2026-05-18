#!/usr/bin/env zsh
# audit-line.sh - emit a standardized audit line for test-fix iteration
# Usage: audit-line.sh <case-number> <input> <expected> <actual>
# Per loop/registry/rules.yaml audit_trail rule
set -euo pipefail
[[ $# -eq 4 ]] || { echo "usage: audit-line.sh <N> <input> <expected> <actual>" >&2; exit 2; }
N="$1"; IN="$2"; EXP="$3"; ACT="$4"
echo "Test ${N}: [${IN}] -> expected [${EXP}] got [${ACT}]"
