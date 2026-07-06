#!/usr/bin/env zsh
# execution plane; routes to scripts/gate.py + this skill's registry/
setopt errexit pipefail
HERE="${0:A:h}"
ROOT="${HERE:h}"
MANIFEST="$ROOT/registry/manifest.json"
PY="$HERE/gate.py"

typeset -i STRICT=0
typeset -a FILES=()

usage() {
  print -u2 "usage: devspeak-gate.sh [--strict] [file...]"
  print -u2 "       devspeak-gate.sh [--strict] --stdin"
  exit 2
}

[[ -f "$MANIFEST" && -f "$PY" ]] || { print -u2 "devspeak bundle incomplete: missing manifest or gate.py"; exit 1; }

while (( $# )); do
  case "$1" in
    --strict) STRICT=1; shift ;;
    --stdin)
      tmp="$(mktemp "${TMPDIR:-/tmp}/devspeak.XXXXXX")"
      cat > "$tmp"
      FILES+=("$tmp")
      shift
      ;;
    -h|--help) usage ;;
    --) shift; FILES+=("$@"); break ;;
    *) FILES+=("$1"); shift ;;
  esac
done

(( ${#FILES[@]} )) || usage

args=(python3 "$PY" --manifest "$MANIFEST")
(( STRICT )) && args+=(--strict)
args+=("${FILES[@]}")
"${args[@]}"
