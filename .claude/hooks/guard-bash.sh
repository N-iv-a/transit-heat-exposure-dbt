#!/usr/bin/env bash
# PreToolUse Bash — comandi ammessi per ruolo. Sessione principale libera.
source "$(dirname "$0")/lib.sh"
INPUT=$(cat)
debug_log "guard-bash $INPUT"
AGENT=$(agent_type "$INPUT")
[ -z "$AGENT" ] && exit 0
has_jq || deny "jq non installato: Bash dei subagent bloccato"
CMD=$(jq -r '.tool_input.command // empty' <<<"$INPUT")

# Toglie i redirect innocui prima dei controlli (2>&1, >/dev/null).
CLEAN=$(sed -E 's/[0-9]?>&[0-9]//g; s#[0-9]?>[[:space:]]*/dev/null##g' <<<"$CMD")

allow_only() {
  if grep -qE '[;&|`<>]|\$\(' <<<"$CLEAN"; then
    deny "$AGENT: niente concatenazioni, pipe o redirect ($CMD)"
  fi
  local re
  for re in "$@"; do
    grep -qE "^[[:space:]]*($re)([[:space:]]|$)" <<<"$CLEAN" && exit 0
  done
  deny "$AGENT: comando non ammesso ($CMD)"
}

CHECK='(bash[[:space:]]+)?(\./)?scripts/loop/check\.sh'
GITRO='git[[:space:]]+(diff|status|log|show)'

case "$AGENT" in
  backend-tester|frontend-tester)
    allow_only "$CHECK" "$GITRO" ;;
  security-reviewer)
    allow_only "$CHECK[[:space:]]+(secrets|bundle|build)" "$GITRO" ;;
  backend-dev|frontend-dev)
    SEP='(^|[;&|(`[:space:]])'
    BLOCK="${SEP}(git[[:space:]]+(commit|push|rebase|merge|tag|reset[[:space:]]+--hard|checkout[[:space:]]+--|clean[[:space:]]+-[a-zA-Z]*f|branch[[:space:]]+-D)|--no-verify|(npm|pnpm|yarn|bun)[[:space:]]+(install|i|add|remove|rm|uninstall|update|up)([[:space:]]|$)|pip3?[[:space:]]+install|uv[[:space:]]+(add|pip)|poetry[[:space:]]+add|curl|wget)"
    if grep -qE "$BLOCK" <<<"$CMD"; then
      deny "$AGENT: git di scrittura, nuove dipendenze e download spettano alla sessione principale ($CMD)"
    fi
    exit 0 ;;
  planner|Explore)
    deny "$AGENT: Bash non previsto" ;;
  *) exit 0 ;;
esac
