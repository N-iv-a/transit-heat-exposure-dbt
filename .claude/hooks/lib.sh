#!/usr/bin/env bash
# Funzioni comuni a hook e script del dev-loop.
ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
ROOT="$(cd "$ROOT" && pwd -P)"
CFG="$ROOT/.claude/loop.json"
RUN="$ROOT/.claude/run"

deny() { echo "dev-loop: $1" >&2; exit 2; }
has_jq() { command -v jq >/dev/null 2>&1; }

# agent_type dall'input dell'hook; vuoto = sessione principale. Funziona anche senza jq.
agent_type() {
  if has_jq; then jq -r '.agent_type // empty' <<<"$1"
  else grep -oE '"agent_type"[[:space:]]*:[[:space:]]*"[^"]*"' <<<"$1" | head -1 | sed -E 's/.*"([^"]*)"$/\1/'
  fi
}

# Livello effettivo di un controllo: profilo attivo + override globali.
lvl() { jq -r --arg k "$1" '((.profiles[.profile] // {}) + (.overrides // {}))[$k] // empty' "$CFG"; }
cfg() { jq -r "$1 // empty" "$CFG"; }

debug_log() {
  [ "${LOOP_DEBUG:-0}" = "1" ] || return 0
  mkdir -p "$RUN"; printf '%s %s\n' "$(date -u +%FT%TZ)" "$1" >> "$RUN/hook-debug.log"
}
