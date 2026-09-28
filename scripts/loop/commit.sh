#!/usr/bin/env bash
# Commit e push senza agent: stage, scanner, conventional commit, push (mai force).
#   commit.sh "feat(core): messaggio"
source "$(dirname "$0")/../../.claude/hooks/lib.sh"
cd "$ROOT" || exit 2
MSG="${1:?uso: commit.sh \"tipo(scope): messaggio\"}"
RE='^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([a-z0-9._/-]+\))?!?: .+'
grep -qE "$RE" <<<"$(head -1 <<<"$MSG")" || { echo "commit: messaggio non conventional ($MSG)"; exit 1; }

BASE=$(cfg .git.base); BR=$(git branch --show-current)
[ -n "$BASE" ] && [ "$BR" = "$BASE" ] && { echo "commit: sei su $BASE, crea prima un branch di lavoro"; exit 1; }

git add -A
git diff --cached --quiet && { echo "commit: niente da committare"; exit 0; }
"$ROOT/scripts/loop/scan.sh" staged "$MSG" || { git reset -q; exit 1; }
git commit -q -m "$MSG" || exit 1
echo "commit $(git rev-parse --short HEAD) su $BR"

if [ "$(cfg .git.push)" = "true" ] && git remote | grep -q .; then
  git push -q -u origin HEAD && echo "push ok" || { echo "push fallito"; exit 1; }
fi
