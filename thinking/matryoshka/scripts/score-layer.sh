#!/usr/bin/env zsh
# score-layer.sh - emit a JSON record template for one layer (Phase 2 helper)
# Usage: score-layer.sh <name> <enforcement_type> <hardness> <bypass_cost>
set -euo pipefail
[[ $# -eq 4 ]] || { echo "usage: score-layer.sh <name> <type> <hardness> <bypass_cost>" >&2; exit 2; }
name="$1"; type="$2"; hardness="$3"; bypass="$4"

# Validate type
case "$type" in
  mechanical|contractual|normative|behavioral|trust) ;;
  *) echo "🔴 invalid enforcement_type: $type (must be mechanical|contractual|normative|behavioral|trust)" >&2; exit 2 ;;
esac

# Validate hardness 0-1
python3 -c "
h = float('$hardness')
assert 0.0 <= h <= 1.0, f'hardness out of range: {h}'
" 2>/dev/null || { echo "🔴 hardness must be 0.0-1.0: $hardness" >&2; exit 2; }

# Validate bypass_cost
case "$bypass" in
  impossible|expensive|moderate|cheap|free) ;;
  *) echo "🔴 invalid bypass_cost: $bypass" >&2; exit 2 ;;
esac

cat << JSON
{
  "name": "$name",
  "enforcement_type": "$type",
  "hardness": $hardness,
  "bypass_cost": "$bypass",
  "is_transition_candidate": $(python3 -c "print('true' if float('$hardness') < 0.5 else 'false')")
}
JSON
