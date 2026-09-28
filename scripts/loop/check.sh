#!/usr/bin/env bash
# Controlli deterministici: girano senza agent, a zero token.
# Stampano solo esito e, se falliscono, le ultime righe; il log completo resta in .claude/run/.
#   check.sh lint|build|test|e2e <backend|frontend>
#   check.sh all <backend|frontend>     lint, build, test ed e2e secondo i livelli
#   check.sh baseline                   stato di partenza delle aree attive
#   check.sh secrets [base]             scanner sul branch
#   check.sh bundle                     build, poi scanner sull'output
source "$(dirname "$0")/../../.claude/hooks/lib.sh"
cd "$ROOT" || exit 2
command -v jq >/dev/null || { echo "check: jq non installato"; exit 2; }
mkdir -p "$RUN"
TAIL=$(cfg .limits.log_tail_lines); TAIL=${TAIL:-40}
MODE=$(cfg .mode)

area_active() {
  case "$MODE:$1" in
    fullstack:*|backend:backend|frontend:frontend) return 0 ;;
    *) return 1 ;;
  esac
}

run_stage() { # stage area
  local stage=$1 area=$2 level key cmd log start rc
  area_active "$area" || { echo "SKIP $stage $area (area non attiva in mode=$MODE)"; return 0; }
  level=$(lvl "$stage"); key=$stage
  [ "$stage" = e2e ] && key="e2e_$level"
  if [ -z "$level" ] || [ "$level" = off ]; then echo "SKIP $stage $area (livello off)"; return 0; fi
  cmd=$(jq -r --arg a "$area" --arg k "$key" '.commands[$a][$k] // empty' "$CFG")
  [ -z "$cmd" ] && { echo "SKIP $stage $area (comando non configurato)"; return 0; }
  log="$RUN/$stage-$area.log"; start=$(date +%s)
  bash -c "$cmd" > "$log" 2>&1; rc=$?
  if [ $rc -eq 0 ]; then echo "PASS $stage $area ($(( $(date +%s) - start ))s)"; return 0; fi
  echo "FAIL $stage $area (exit $rc) — ultime $TAIL righe, log completo in ${log#"$ROOT"/}:"
  tail -n "$TAIL" "$log"
  return 1
}

case "${1:-}" in
  lint|build|test|e2e) run_stage "$1" "${2:?area: backend|frontend}" ;;
  all)
    rc=0
    for s in lint build test e2e; do
      [ "$s" = e2e ] && [ "$2" != frontend ] && continue
      run_stage "$s" "$2" || { rc=1; break; }
    done
    exit $rc ;;
  baseline)
    out="$RUN/baseline.txt"; : > "$out"
    for a in backend frontend; do
      area_active "$a" || continue
      for s in lint build test; do run_stage "$s" "$a" 2>&1 | head -1 >> "$out"; done
    done
    echo "baseline in ${out#"$ROOT"/}:"; cat "$out" ;;
  secrets) "$ROOT/scripts/loop/scan.sh" branch "${2:-}" ;;
  bundle)
    out=$(cfg .paths.build_output)
    [ -z "$out" ] && { echo "SKIP bundle (paths.build_output vuoto)"; exit 0; }
    run_stage build frontend || exit 1
    "$ROOT/scripts/loop/scan.sh" path "$out" ;;
  *) sed -n '2,9p' "$0"; exit 2 ;;
esac
