#!/usr/bin/env zsh
# scaffold-report.sh - emit empty premortem report + transcript filenames with timestamp.
# Usage: scaffold-report.sh [target_label]
set -euo pipefail
ts=$(date -u +%Y%m%dT%H%M%SZ)
label="${1:-premortem}"
printf 'report:%s-report-%s.html\n' "$label" "$ts"
printf 'transcript:%s-transcript-%s.md\n' "$label" "$ts"
