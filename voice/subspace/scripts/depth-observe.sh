#!/usr/bin/env zsh
# depth-observe.sh - report observation cues for subspace depth (NOT a chooser, an observer)
# Usage: depth-observe.sh <message_count_in_session>
# Output: suggested depth based on context cues; agent must verify against actual state
set -euo pipefail
n="${1:-0}"
if   (( n < 30 )); then echo "shallow"
elif (( n < 60 )); then echo "mid"
elif (( n < 100 )); then echo "deep"
else                     echo "abyssal"
fi
echo "# NOTE: this is a heuristic. Agent OBSERVES actual state, never performs the suggested depth." >&2
