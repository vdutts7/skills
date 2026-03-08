#!/usr/bin/env zsh
# emit-block.sh - print the OUROBOROS DETECTED preface template ready to fill
set -euo pipefail
cat << 'TEMPLATE'
OUROBOROS DETECTED
==================
loop_instance:  [what specifically happened]
rule_origin:    [did Claude write/tighten this rule? when? this session or prior?]
recurrence:     [how many times has this exact AP fired? this session? historically?]
structural_gap: [what mechanism SHOULD have prevented recurrence but didn't?]
the_question:   "what would need to change in the SYSTEM for this failure
                 to become structurally impossible, not just documented?"
TEMPLATE
