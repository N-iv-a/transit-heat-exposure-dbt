#!/usr/bin/env bash
# PreToolUse Bash — su git commit e git push, per chiunque, scansiona ciò che esce.
source "$(dirname "$0")/lib.sh"
INPUT=$(cat)
if ! has_jq; then
  grep -qE 'git[[:space:]]+(commit|push)' <<<"$INPUT" && deny "jq non installato: commit e push bloccati"
  exit 0
fi
CMD=$(jq -r '.tool_input.command // empty' <<<"$INPUT")
SEP='(^|[;&|(`[:space:]])'
if   grep -qE "${SEP}git([[:space:]]+-[cC][[:space:]]+[^[:space:]]+)*[[:space:]]+commit" <<<"$CMD"; then MODE=commit
elif grep -qE "${SEP}git([[:space:]]+-[cC][[:space:]]+[^[:space:]]+)*[[:space:]]+push"   <<<"$CMD"; then MODE=push
else exit 0; fi
"$ROOT/scripts/loop/scan.sh" "$MODE" "$CMD" >&2 || exit 2
exit 0
