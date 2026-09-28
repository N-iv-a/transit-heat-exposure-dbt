#!/usr/bin/env bash
# Manopole del dev-loop.
#   level.sh                          mostra profilo, modalità e livelli effettivi
#   level.sh profile eco|standard|strict
#   level.sh set <controllo> <valore>  override globale (es. set gate full)
#   level.sh model <ruolo> <modello>   override del modello (planner|dev|tester|reviewer)
#   level.sh reset                    toglie gli override globali
#   level.sh mode backend|frontend|fullstack
#   level.sh effective [k=v ...]      JSON dei livelli per un task (override del task in coda)
source "$(dirname "$0")/../../.claude/hooks/lib.sh"
cd "$ROOT" || exit 2
command -v jq >/dev/null || { echo "level: jq non installato"; exit 2; }

save() { local t; t=$(mktemp); jq "$@" "$CFG" > "$t" && mv "$t" "$CFG"; }
valid() { jq -e --arg k "$1" --arg v "$2" '.levels[$k] // [] | index($v)' "$CFG" >/dev/null \
  || { echo "valore non valido: $1=$2 (ammessi: $(jq -r --arg k "$1" '.levels[$k] // [] | join(", ")' "$CFG"))"; exit 1; }; }

effective() { # stampa JSON: profilo + override globali + override del task
  local task='{}' kv k v
  for kv in "$@"; do
    k=${kv%%=*}; v=${kv#*=}
    case "$k" in
      model.*) valid models "$v"; task=$(jq --arg r "${k#model.}" --arg v "$v" '.models[$r]=$v' <<<"$task") ;;
      *) valid "$k" "$v"; task=$(jq --arg k "$k" --arg v "$v" '.[$k]=$v' <<<"$task") ;;
    esac
  done
  jq --argjson t "$task" '
    (.profiles[.profile]) as $p | (.overrides // {}) as $o |
    ($p + $o + $t) + {models: (($p.models // {}) + ($o.models // {}) + ($t.models // {}))}
    + {profile: .profile, mode: .mode}' "$CFG"
}

agents_for_mode() {
  local on="$ROOT/.claude/agents" off="$ROOT/.claude/agents-off"; mkdir -p "$off"
  mv "$off"/*.md "$on"/ 2>/dev/null
  case "$1" in
    backend)  mv "$on"/frontend-*.md "$off"/ 2>/dev/null ;;
    frontend) mv "$on"/backend-*.md  "$off"/ 2>/dev/null ;;
  esac
  rmdir "$off" 2>/dev/null; true
}

case "${1:-show}" in
  show)
    echo "profilo: $(cfg .profile) · modalità: $(cfg .mode) · override: $(jq -c '.overrides' "$CFG")"
    effective | jq -r 'del(.profile,.mode) | to_entries[] |
      if .key=="models" then "  modelli: " + (.value|to_entries|map(.key+"="+.value)|join(" "))
      else "  \(.key): \(.value)" end' ;;
  profile)
    jq -e --arg p "$2" '.profiles[$p]' "$CFG" >/dev/null || { echo "profilo inesistente: $2"; exit 1; }
    save --arg p "$2" '.profile=$p'; echo "profilo → $2" ;;
  set)   valid "$2" "$3"; save --arg k "$2" --arg v "$3" '.overrides[$k]=$v'; echo "override $2 → $3" ;;
  model) valid models "$3"; save --arg r "$2" --arg v "$3" '.overrides.models[$r]=$v'; echo "modello $2 → $3" ;;
  reset) save '.overrides={}'; echo "override azzerati" ;;
  mode)
    case "$2" in backend|frontend|fullstack) ;; *) echo "mode: backend|frontend|fullstack"; exit 1 ;; esac
    save --arg m "$2" '.mode=$m'; agents_for_mode "$2"; echo "modalità → $2" ;;
  effective) shift; effective "$@" ;;
  *) sed -n '2,10p' "$0"; exit 2 ;;
esac
