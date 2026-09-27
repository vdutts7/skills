#!/usr/bin/env bash
# pack.sh - bundle any skill in this repo into a .skill file
# Usage:
#   ./pack.sh thinking/mirror              → ~/Downloads/mirror.skill
#   ./pack.sh mirror                       → search all groups, same output
#   ./pack.sh thinking/mirror --out /tmp   → /tmp/mirror.skill
#   ./pack.sh thinking/mirror --install    → also unpack to ~/.agents/skills/mirror/
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"

usage() {
  cat <<'EOF'
usage: ./pack.sh <skill> [--out DIR] [--install [DIR]]

  <skill>       skill path (e.g. thinking/mirror) or bare name (e.g. mirror)
  --out DIR     output directory for .skill file (default: ~/Downloads)
  --install     unpack into ~/.agents/skills/<name>/ after packing
                reads by: Claude Code (~/.claude/skills/), Codex, Cursor, Copilot (~/.agents/skills/)
  --install DIR unpack into a custom path instead
EOF
  exit 2
}

SKILL_ARG=""
OUT_DIR="${HOME}/Downloads"
DO_INSTALL=0
INSTALL_DIR=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --out) OUT_DIR="${2:?}"; shift 2 ;;
    --install)
      DO_INSTALL=1
      if [[ -n "${2:-}" && "${2}" != --* ]]; then
        INSTALL_DIR="$2"; shift
      fi
      shift ;;
    -h|--help) usage ;;
    -*) echo "unknown flag: $1" >&2; usage ;;
    *) SKILL_ARG="$1"; shift ;;
  esac
done

[[ -n "$SKILL_ARG" ]] || usage

# Resolve skill directory
if [[ -d "$ROOT/$SKILL_ARG" && -f "$ROOT/$SKILL_ARG/SKILL.md" ]]; then
  SKILL_DIR="$ROOT/$SKILL_ARG"
  SKILL_NAME="$(basename "$SKILL_ARG")"
else
  FOUND=""
  for group in deep-research thinking tools voice; do
    candidate="$ROOT/$group/$SKILL_ARG"
    if [[ -d "$candidate" && -f "$candidate/SKILL.md" ]]; then
      FOUND="$candidate"; break
    fi
  done
  if [[ -z "$FOUND" ]]; then
    echo "pack: skill not found: $SKILL_ARG" >&2
    echo "available:" >&2
    find "$ROOT" -name "SKILL.md" | sed "s|$ROOT/||; s|/SKILL.md||" | sort >&2
    exit 1
  fi
  SKILL_DIR="$FOUND"
  SKILL_NAME="$SKILL_ARG"
fi

[[ -z "$INSTALL_DIR" ]] && INSTALL_DIR="${HOME}/.agents/skills/${SKILL_NAME}"

OUT_DIR="$(python3 -c "import os,sys; print(os.path.expanduser(os.path.abspath(sys.argv[1])))" "$OUT_DIR")"
ARCHIVE="${OUT_DIR}/${SKILL_NAME}.skill"

mkdir -p "$OUT_DIR"
[[ -f "$ARCHIVE" ]] && { command -v trash &>/dev/null && trash "$ARCHIVE" 2>/dev/null || /bin/rm -f "$ARCHIVE"; }

python3 - "$SKILL_DIR" "$SKILL_NAME" "$ARCHIVE" <<'PY'
import sys, zipfile
from pathlib import Path

skill_dir = Path(sys.argv[1])
name      = sys.argv[2]
archive   = Path(sys.argv[3])
SKIP = {'.DS_Store', '__pycache__', '.gitkeep'}

with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
    for f in sorted(skill_dir.rglob("*")):
        if f.is_file() and f.name not in SKIP and not f.name.startswith('.'):
            zf.write(f, f"{name}/{f.relative_to(skill_dir).as_posix()}")
print(f"packed {name}: {archive}")
PY

if [[ "$DO_INSTALL" -eq 1 ]]; then
  [[ -d "$INSTALL_DIR" ]] && { command -v trash &>/dev/null && trash "$INSTALL_DIR" 2>/dev/null || /bin/rm -rf "$INSTALL_DIR"; }
  mkdir -p "$(dirname "$INSTALL_DIR")"
  unzip -q "$ARCHIVE" -d "$(dirname "$INSTALL_DIR")"
  echo "installed: ${INSTALL_DIR/#$HOME/~}"
fi

echo ""
echo "${ARCHIVE/#$HOME/~}"
echo ""
echo "install paths:"
echo "  ~/.claude/skills/${SKILL_NAME}/   ← Claude Code, Cursor"
echo "  ~/.agents/skills/${SKILL_NAME}/   ← Codex, Copilot, Gemini CLI"
echo ""
echo "  unzip -o '${ARCHIVE/#$HOME/~}' -d ~/.agents/skills/"
