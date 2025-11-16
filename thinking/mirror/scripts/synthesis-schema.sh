#!/usr/bin/env zsh
# synthesis-schema.sh - print the JSON schema for canonical synthesis structures
# Usage: synthesis-schema.sh [structure_name]
# Per mirror/registry/synthesis-structures.yaml
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Emit list of structures, or details for one named structure
target="${1:-}"
if [[ -z "$target" ]]; then
  python3 -c "
import yaml
d = yaml.safe_load(open('$ROOT/registry/synthesis-structures.yaml'))
for k in d.keys():
    print(k)
"
else
  python3 -c "
import yaml, json
d = yaml.safe_load(open('$ROOT/registry/synthesis-structures.yaml'))
if '$target' not in d:
    import sys
    print(f'ERR: unknown structure: $target', file=sys.stderr)
    print('available: ' + ', '.join(d.keys()), file=sys.stderr)
    sys.exit(1)
print(json.dumps(d['$target'], indent=2))
"
fi
