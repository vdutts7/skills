#!/usr/bin/env zsh
# sanitize.sh - apply humanize hard invariants (R-000 em-dash, R-027 unicode pipeline subset)
# Usage: sanitize.sh < input.txt  OR  sanitize.sh file.txt
# Per registry/laws.json#R-000 and registry/parsing-binding.yaml
set -euo pipefail

if [[ -n "${1:-}" ]]; then
  python3 "$(dirname "$0")/sanitize.py" "$1"
else
  python3 "$(dirname "$0")/sanitize.py"
fi
