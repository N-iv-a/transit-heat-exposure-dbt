#!/usr/bin/env bash
# Test di hook e script del dev-loop su una copia usa-e-getta del repo.
# Rilancialo ogni volta che tocchi hook, pattern o allowlist:  scripts/tests/test-hooks.sh
SRC="$(cd "$(dirname "$0")/../.." && pwd)"
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
cp -r "$SRC/." "$T/"; rm -rf "$T/.git" "$T/.claude/run"
cd "$T" || exit 1
# Cartelle fittizie fisse: i test non dipendono dai paths reali del progetto.
jq '.paths={backend:["src/core/","tests/core/"], frontend:["src/ui/","public/","e2e/"], contract:["contract/"], build_output:"dist/"}' \
  .claude/loop.json > c && mv c .claude/loop.json
git init -q -b main && git config user.email t@example.com && git config user.name t
git add -A && git commit -qm "chore: init" && git switch -qc loop/test
export CLAUDE_PROJECT_DIR="$T"
H="$T/.claude/hooks"; PASS=0; FAILN=0

j() { jq -nc --arg a "$1" --arg t "$2" --arg k "$3" --arg v "$4" \
  '{tool_name:$t, tool_input:{($k):$v}} + (if $a=="" then {} else {agent_type:$a} end)'; }
expect() { # descrizione esito-atteso(0|2) hook agent tool chiave valore
  local d=$1 want=$2 hook=$3; shift 3
  j "$@" | "$H/$hook" >/dev/null 2>&1; local got=$?
  if [ "$got" = "$want" ]; then PASS=$((PASS+1)); else FAILN=$((FAILN+1)); echo "FAIL: $d (atteso $want, ottenuto $got)"; fi
}
expect_rc() { # descrizione esito comando...
  local d=$1 want=$2; shift 2
  "$@" >/dev/null 2>&1; local got=$?
  if [ "$got" = "$want" ]; then PASS=$((PASS+1)); else FAILN=$((FAILN+1)); echo "FAIL: $d (atteso $want, ottenuto $got)"; fi
}
W=guard-paths.sh; B=guard-bash.sh; S=scan-secrets.sh

# --- cartelle per ruolo
expect "main scrive ovunque"            0 $W ""             Write file_path .claude/loop.json
expect "backend-dev in src/core"        0 $W backend-dev    Write file_path src/core/a.ts
expect "backend-dev assoluto ammesso"   0 $W backend-dev    Edit  file_path "$T/tests/core/a.test.ts"
expect "backend-dev in src/ui"          2 $W backend-dev    Write file_path src/ui/a.tsx
expect "backend-dev fuori dal repo"     2 $W backend-dev    Write file_path ../fuori.txt
expect "backend-dev traversal"          2 $W backend-dev    Write file_path src/core/../../.claude/loop.json
expect "backend-dev prefisso finto"     2 $W backend-dev    Write file_path src/core-evil/a.ts
expect "backend-dev nel contratto"      2 $W backend-dev    Write file_path contract/types.ts
expect "backend-dev nel package.json"   2 $W backend-dev    Write file_path package.json
expect "frontend-dev in public"         0 $W frontend-dev   Write file_path public/icon.svg
expect "frontend-dev in src/core"       2 $W frontend-dev   Edit  file_path src/core/a.ts
expect "tester non scrive"              2 $W backend-tester Write file_path src/core/a.ts
expect "agent generico non scrive"      2 $W general-purpose Write file_path src/core/a.ts

# --- comandi per ruolo
expect "tester check.sh"                0 $B backend-tester  Bash command "scripts/loop/check.sh all backend"
expect "tester check.sh con 2>&1"       0 $B frontend-tester Bash command "./scripts/loop/check.sh test frontend 2>&1"
expect "tester bash check.sh"           0 $B backend-tester  Bash command "bash scripts/loop/check.sh test backend"
expect "tester git diff"                0 $B backend-tester  Bash command "git diff main"
expect "tester npm diretto"             2 $B backend-tester  Bash command "npm test"
expect "tester concatenazione"          2 $B backend-tester  Bash command "scripts/loop/check.sh all backend; rm -rf src"
expect "tester pipe"                    2 $B backend-tester  Bash command "git diff | cat"
expect "tester sostituzione"            2 $B backend-tester  Bash command 'git diff $(rm -rf src)'
expect "tester redirect su file"        2 $B backend-tester  Bash command "git diff > /tmp/x"
expect "reviewer secrets"               0 $B security-reviewer Bash command "scripts/loop/check.sh secrets main"
expect "reviewer bundle"                0 $B security-reviewer Bash command "scripts/loop/check.sh bundle"
expect "reviewer check all"             2 $B security-reviewer Bash command "scripts/loop/check.sh all backend"
expect "dev npm test"                   0 $B backend-dev  Bash command "npm test"
expect "dev npm ci"                     0 $B backend-dev  Bash command "npm ci"
expect "dev lint --fix"                 0 $B frontend-dev Bash command "npm run lint -- --fix"
expect "dev git status"                 0 $B backend-dev  Bash command "git status"
expect "dev npm install pacchetto"      2 $B backend-dev  Bash command "npm install lodash"
expect "dev npm i"                      2 $B backend-dev  Bash command "npm i"
expect "dev pip install"                2 $B backend-dev  Bash command "pip install requests"
expect "dev git commit"                 2 $B backend-dev  Bash command "git commit -m x"
expect "dev push concatenato"           2 $B frontend-dev Bash command "echo ok && git push"
expect "dev reset --hard"               2 $B backend-dev  Bash command "git reset --hard HEAD~1"
expect "dev curl"                       2 $B backend-dev  Bash command "curl https://example.com"
expect "dev --no-verify"                2 $B backend-dev  Bash command "npm test --no-verify"
expect "planner senza bash"             2 $B planner      Bash command "ls"
expect "main libero"                    0 $B ""           Bash command "npm install lodash"

# --- scanner su commit e push
mkdir -p src/core
expect "comando non git"                0 $S "" Bash command "ls -la"
echo 'export const x = 1;' > src/core/ok.ts; git add src/core/ok.ts
expect "commit pulito"                  0 $S "" Bash command "git commit -m 'feat(core): x'"
expect "messaggio con email vera"       2 $S "" Bash command "git commit -m 'fix: mario.rossi@gmail.com'"
expect "messaggio con email fittizia"   0 $S "" Bash command "git commit -m 'fix: test@example.com'"
echo 'const k = "sk-ant-api03-AAAAAAAAAAAAAAAAAAAAAAAAAAAA";' > src/core/key.ts; git add src/core/key.ts
expect "chiave anthropic in stage"      2 $S "" Bash command "git commit -m 'feat: k'"
expect "commit via git -C"              2 $S "" Bash command "git -C . commit -m 'feat: k'"
git reset -q src/core/key.ts; rm src/core/key.ts
printf -- '-----BEGIN OPENSSH PRIVATE KEY-----\n' > src/core/pk.txt; git add src/core/pk.txt
expect "chiave privata"                 2 $S "" Bash command "git commit -m 'feat: pk'"
git reset -q src/core/pk.txt; rm src/core/pk.txt
echo 'cf = "BNCLRA90A41F205X"' > src/core/cf.ts; git add src/core/cf.ts
expect "codice fiscale"                 2 $S "" Bash command "git commit -m 'feat: cf'"
echo 'cf = "RSSMRA85T10A562S"' > src/core/cf.ts; git add src/core/cf.ts
expect "codice fiscale in allowlist"    0 $S "" Bash command "git commit -m 'feat: cf'"
git reset -q; rm src/core/cf.ts
echo 'iban = "IT60 X054 2811 1010 0000 0123 456"' > src/core/i.ts
expect "iban non in stage con git add"  2 $S "" Bash command "git add -A && git commit -m 'feat: i'"
rm src/core/i.ts
echo '{"author":"mario.rossi@gmail.com"}' > package-lock.json; git add package-lock.json
expect "percorso ignorato"              0 $S "" Bash command "git commit -m 'chore: lock'"
git reset -q; rm package-lock.json
echo 'tel = "+39 347 1234567"' > src/core/t.ts; git add src/core/t.ts; git commit -qm "feat: t" --no-verify
expect "push con telefono"              2 $S "" Bash command "git push"
git reset -q --hard HEAD~1

# --- livelli
L=scripts/loop/level.sh
expect_rc "set valido"                  0 $L set gate full
[ "$($L effective | jq -r .gate)" = full ] && PASS=$((PASS+1)) || { FAILN=$((FAILN+1)); echo "FAIL: override globale"; }
expect_rc "valore non valido"           1 $L set gate massimo
expect_rc "override task non valido"    1 $L effective test=forse
[ "$($L effective test=agent model.dev=opus | jq -r '.test + .models.dev')" = agentopus ] && PASS=$((PASS+1)) || { FAILN=$((FAILN+1)); echo "FAIL: override task"; }
$L reset >/dev/null; $L profile eco >/dev/null
[ "$($L effective | jq -r .gate)" = scan ] && PASS=$((PASS+1)) || { FAILN=$((FAILN+1)); echo "FAIL: profilo eco"; }
$L mode backend >/dev/null
[ ! -f .claude/agents/frontend-dev.md ] && [ -f .claude/agents-off/frontend-dev.md ] && PASS=$((PASS+1)) || { FAILN=$((FAILN+1)); echo "FAIL: mode backend"; }
$L mode fullstack >/dev/null
[ -f .claude/agents/frontend-dev.md ] && PASS=$((PASS+1)) || { FAILN=$((FAILN+1)); echo "FAIL: mode fullstack"; }

# --- check e commit
jq '.commands.backend.test="echo tutto ok" | .commands.backend.lint="echo errore-lint; exit 3"' .claude/loop.json > c && mv c .claude/loop.json
$L profile standard >/dev/null
expect_rc "test che passa"              0 scripts/loop/check.sh test backend
expect_rc "lint che fallisce"           1 scripts/loop/check.sh lint backend
scripts/loop/check.sh lint backend | grep -q "errore-lint" && PASS=$((PASS+1)) || { FAILN=$((FAILN+1)); echo "FAIL: coda del log"; }
$L set lint off >/dev/null
scripts/loop/check.sh lint backend | grep -q "^SKIP" && PASS=$((PASS+1)) || { FAILN=$((FAILN+1)); echo "FAIL: livello off"; }
jq '.git.push=false' .claude/loop.json > c && mv c .claude/loop.json
echo 'export const y = 2;' > src/core/y.ts
expect_rc "commit non conventional"     1 scripts/loop/commit.sh "aggiunto y"
expect_rc "commit conventional"         0 scripts/loop/commit.sh "feat(core): aggiunge y"
git switch -q main; mkdir -p src/core
echo 'export const z = 3;' > src/core/z.ts
expect_rc "commit sul branch base"      1 scripts/loop/commit.sh "feat(core): z"

echo "hook e script: $PASS ok, $FAILN falliti"
[ "$FAILN" = 0 ]
