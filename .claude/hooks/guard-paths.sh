#!/usr/bin/env bash
# PreToolUse Edit|Write|MultiEdit|NotebookEdit
# Ogni dev scrive solo nelle cartelle del suo ruolo (loop.json → paths).
# Sessione principale libera; ogni altro subagent non scrive.
source "$(dirname "$0")/lib.sh"
INPUT=$(cat)
debug_log "guard-paths $INPUT"
AGENT=$(agent_type "$INPUT")
[ -z "$AGENT" ] && exit 0
has_jq || deny "jq non installato: scritture dei subagent bloccate"

FILE=$(jq -r '.tool_input.file_path // .tool_input.notebook_path // empty' <<<"$INPUT")
[ -z "$FILE" ] && exit 0
case "$FILE" in /*) ABS="$FILE" ;; *) ABS="$ROOT/$FILE" ;; esac
ABS=$(realpath -m "$ABS")
REL="${ABS#"$ROOT"/}"
[ "$REL" = "$ABS" ] && deny "$AGENT: scrittura fuori dal repo ($FILE)"

case "$AGENT" in
  backend-dev)  KEY=backend ;;
  frontend-dev) KEY=frontend ;;
  *) deny "$AGENT: questo ruolo non scrive file" ;;
esac

while IFS= read -r P; do
  P="${P%/}"; [ -z "$P" ] && continue
  if [ "$REL" = "$P" ] || [[ "$REL" == "$P/"* ]]; then exit 0; fi
done < <(jq -r --arg k "$KEY" '.paths[$k][]?' "$CFG")

deny "$AGENT scrive solo in $(jq -r --arg k "$KEY" '.paths[$k] | join(", ")' "$CFG"); rifiutato: $REL. Se serve toccare altro, fermati e segnalalo."
