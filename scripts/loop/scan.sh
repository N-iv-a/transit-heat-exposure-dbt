#!/usr/bin/env bash
# Scanner deterministico di segreti e dati personali (zero token).
#   scan.sh commit "<comando>"   modifiche in uscita + messaggio (usato dall'hook)
#   scan.sh push   "<comando>"   commit non ancora pushati
#   scan.sh staged "<messaggio>" area di stage + messaggio (usato da commit.sh)
#   scan.sh branch [base]        tutto il branch rispetto alla base
#   scan.sh path <cartella>      file su disco (es. output di build)
# Livello da loop.json → secrets: regex | auto (gitleaks se c'è) | full (gitleaks obbligatorio)
source "$(dirname "$0")/../../.claude/hooks/lib.sh"
cd "$ROOT" || exit 2
command -v jq >/dev/null || { echo "scan: jq non installato, blocco per sicurezza"; exit 2; }
PAT="$ROOT/.claude/security-patterns.json"
MODE="${1:-}"; ARG="${2:-}"
LEVEL=$(lvl secrets); LEVEL="${LEVEL:-auto}"
TMP=$(mktemp); trap 'rm -f "$TMP" "$TMP".*' EXIT

# Formato interno: una riga per contenuto, "file<TAB>testo".
emit_diff()  { git diff --no-color -U0 "$@" 2>/dev/null | awk '
  /^\+\+\+ /{f=substr($0,5); sub(/^b\//,"",f); next}
  /^\+/{print f "\t" substr($0,2)}'; }
emit_log()   { git log --no-color -p -U0 --format='@@MSG@@%n%B' "$@" 2>/dev/null | awk '
  /^@@MSG@@$/{msg=1; next}
  /^diff --git/{msg=0; next}
  msg && NF {print "(messaggio di commit)\t" $0; next}
  /^\+\+\+ /{f=substr($0,5); sub(/^b\//,"",f); next}
  !msg && /^\+/{print f "\t" substr($0,2)}'; }
emit_text()  { printf '%s\n' "$2" | awk -v f="$1" 'NF{print f "\t" $0}'; }
emit_files() { local x; while IFS= read -r x; do [ -f "$x" ] && grep -Iv '^$' "$x" 2>/dev/null | awk -v f="$x" '{print f "\t" $0}'; done; }

has_head() { git rev-parse --verify -q HEAD >/dev/null; }

case "$MODE" in
  commit)
    if has_head; then emit_diff HEAD; else emit_diff --cached; fi > "$TMP"
    emit_text "(comando di commit)" "$ARG" >> "$TMP"
    F=$(grep -oE '(-F|--file)[= ]+[^ ]+' <<<"$ARG" | head -1 | sed -E 's/^(-F|--file)[= ]+//')
    [ -n "$F" ] && [ -f "$F" ] && emit_text "(messaggio di commit)" "$(cat "$F")" >> "$TMP"
    # "git add ... && git commit" nello stesso comando: i file nuovi non sono ancora in stage.
    grep -qE 'git[[:space:]]+add' <<<"$ARG" && git ls-files --others --exclude-standard | emit_files >> "$TMP"
    ;;
  staged)
    emit_diff --cached > "$TMP"
    emit_text "(messaggio di commit)" "$ARG" >> "$TMP" ;;
  push)
    if git rev-parse -q --verify '@{u}' >/dev/null 2>&1; then emit_log '@{u}..HEAD'
    else emit_log HEAD --not --remotes; fi > "$TMP" ;;
  branch)
    BASE="${ARG:-$(cfg .git.base)}"; BASE="${BASE:-main}"
    if git rev-parse -q --verify "$BASE" >/dev/null; then emit_log "$BASE..HEAD" > "$TMP"
    else emit_log HEAD > "$TMP"; fi
    emit_diff HEAD >> "$TMP" 2>/dev/null ;;
  path)
    [ -d "$ARG" ] || { echo "scan: cartella $ARG assente (build eseguita?)"; exit 1; }
    find "$ARG" -type f | emit_files > "$TMP" ;;
  *) echo "uso: scan.sh commit|push|staged|branch|path [arg]"; exit 2 ;;
esac

# Percorsi ignorati
IGN=$(jq -r '.ignore_paths[]' "$PAT" | sed -E 's/[.]/\\./g; s#^#^#' | paste -sd'|' -)
if [ -n "$IGN" ]; then grep -vE "($IGN)" "$TMP" > "$TMP.f"; else cp "$TMP" "$TMP.f"; fi

# Toglie dal testo le occorrenze in allowlist (dati fittizi dichiarati)
cp "$TMP.f" "$TMP.a"
while IFS= read -r A; do sed -E -i "s/$A//g" "$TMP.a"; done < <(jq -r '.allowlist[]' "$PAT")

FOUND=0
while IFS=$'\t' read -r NAME RE ICASE; do
  FLAGS=-E; [ "$ICASE" = "true" ] && FLAGS=-Ei
  HITS=$(cut -f2- "$TMP.a" | grep -n $FLAGS -e "$RE" | cut -d: -f1 | head -5)
  for N in $HITS; do
    LINE=$(sed -n "${N}p" "$TMP.a")
    VAL=$(cut -f2- <<<"$LINE" | grep -o $FLAGS -e "$RE" | head -1)
    echo "SEGRETO? ${LINE%%$'\t'*}: $NAME (${VAL:0:4}***)"
    FOUND=1
  done
done < <(jq -r '.patterns[] | [.name, .regex, (.icase // false | tostring)] | @tsv' "$PAT" | sed 's/\\\\/\\/g')

# gitleaks
if [ "$LEVEL" != "regex" ]; then
  if command -v gitleaks >/dev/null 2>&1; then
    if [ "$MODE" = "path" ]; then OUT=$(gitleaks dir "$ARG" --no-banner --redact -v -l error 2>&1)
    else OUT=$(cut -f2- "$TMP.f" | gitleaks stdin --no-banner --redact -v -l error 2>&1); fi
    if [ $? -ne 0 ]; then echo "SEGRETO? gitleaks:"; sed 's/\x1b\[[0-9;]*m//g' <<<"$OUT" | grep -E 'Finding|RuleID|File' | head -12; FOUND=1; fi
  elif [ "$LEVEL" = "full" ]; then
    echo "scan: gitleaks assente e secrets=full (installa con scripts/cloud-setup.sh o passa a secrets=auto)"; exit 1
  else
    echo "scan: gitleaks assente, solo regex (secrets=auto)"
  fi
fi

if [ "$FOUND" = 1 ]; then
  echo "BLOCCATO: rimuovi i dati sopra o, se fittizi, aggiungili ad allowlist in .claude/security-patterns.json"
  exit 1
fi
echo "scan $MODE: pulito"
