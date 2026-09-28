# dev-loop-template

Ciclo di sviluppo con specialisti per Claude Code, riutilizzabile in ogni progetto. Nato dal workflow di Fronte Interno, ma indipendente: cambiare questo non tocca quello.

Il principio: **ciò che è deterministico lo fanno gli script, a zero token; gli agent lavorano solo dove serve giudizio.** Ogni controllo ha livelli regolabili, per profilo, globalmente o per singolo task.

## Avvio rapido
1. Su GitHub: **Use this template** → nuovo repo.
2. `.claude/loop.json`: compila `paths` (cartelle backend e frontend) e `commands` (lint, build, test, e2e).
3. `scripts/loop/level.sh mode backend|frontend|fullstack`: in backend e frontend gli agent dell'altra area vengono parcheggiati in `.claude/agents-off/`.
4. `CLAUDE.md`, `docs/spec.md` e la sezione «Specifiche» di `.claude/security-guidance.md`.
5. Nelle impostazioni dell'environment cloud, come setup script: `bash scripts/cloud-setup.sh`.
6. `scripts/tests/test-hooks.sh` deve dire «0 falliti».
7. Scrivi i task in `tasks/coda.md` e chiedi a Claude Code: «procedi con la coda».

## Profili

| Controllo | eco | standard | strict | Valori |
|---|---|---|---|---|
| plan | inline | auto | agent | inline · auto (agent solo per task M/L) · agent |
| lint | off | on | on | off · on |
| build | off | on | on | off · on |
| test | script | script | agent | off · script · agent |
| e2e | off | smoke | full | off · smoke · full |
| docs | off | touched | full | off · touched · full |
| gate | scan | lite | full | scan · lite · full |
| secrets | regex | auto | full | regex · auto · full |
| modelli | tutti sonnet/haiku | reviewer sonnet | planner e reviewer opus | haiku · sonnet · opus · inherit |

- **gate** — `scan`: solo scanner, niente agent. `lite`: reviewer sul diff del codice. `full`: reviewer su diff, docs, messaggio, secrets del branch e output di build.
- **secrets** — `regex`: pattern di `.claude/security-patterns.json`. `auto`: aggiunge gitleaks se è installato. `full`: gitleaks obbligatorio.
- **Pavimento:** lo scanner su commit e push non si spegne mai. Costa zero token, quindi spegnerlo non fa risparmiare nulla.

## Manopole
```
scripts/loop/level.sh                    # stato attuale
scripts/loop/level.sh profile eco        # cambia profilo
scripts/loop/level.sh set gate full      # override globale di un controllo
scripts/loop/level.sh model dev opus     # override del modello di un ruolo
scripts/loop/level.sh reset              # via gli override
```
Per un solo task, in coda: `- [ ] T07 [MIX] [L] Login — ... {gate=full test=agent model.dev=opus}`.

## Dove si risparmia
- **Test, lint, build, commit e push sono script.** Stampano solo l'esito e, su errore, le ultime righe; il log completo resta in `.claude/run/`. Niente agent git-ops.
- **Tester e planner sono opzionali:** in `script` e `inline` non partono affatto.
- **Retry sullo stesso dev:** su un fallimento il dev viene ripreso con SendMessage invece di crearne uno nuovo, e riceve solo le righe d'errore.
- **Modelli per ruolo e per profilo,** passati a ogni invocazione. Nel frontmatter restano `effort` e `maxTurns` come tetto ai cicli a vuoto.
- **`omitClaudeMd`** per tester, reviewer ed Explore: ricevono dal prompt ciò che serve.
- **Explore su haiku:** sostituisce quello integrato, che ora eredita il modello della sessione.
- **Niente subagent annidati** (`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=1`), niente memoria degli agent, niente MCP Playwright: l'e2e passa dal test runner.
- **Prompt corti:** agent e skill si ricaricano a ogni avvio, quindi ogni riga costa.

## Sicurezza (sempre attiva, zero token)
- `guard-paths`: ogni dev scrive solo nelle sue cartelle; gli altri subagent non scrivono.
- `guard-bash`: tester e reviewer solo con `check.sh` e git in lettura, senza pipe né concatenazioni; i dev senza commit, push, nuove dipendenze o download.
- `scan-secrets`: su ogni `git commit` e `git push`, di chiunque. Cerca chiavi, email, telefoni, IBAN e codici fiscali nel diff in uscita e nel messaggio. I dati fittizi dichiarati vanno in `allowlist`.
- La sessione principale non ha limiti di cartelle: aggiorna contratto e file condivisi.

## Da verificare al primo avvio
- **agent_type negli hook.** Lancia una sessione con `LOOP_DEBUG=1`, fai partire un dev e controlla che in `.claude/run/hook-debug.log` compaia `"agent_type":"backend-dev"`. Senza questo, le restrizioni per ruolo non si applicano.
- **Consumo reale.** `/tasks` mostra modello ed effort di ogni subagent: confrontalo con il profilo.

## Limiti noti
- Gli hook sono bash con grep e realpath GNU: su Windows servono WSL o Git Bash, su macOS `brew install grep coreutils`.
- I fork della sessione non scrivono file: il lavoro passa dai dev.
- Il plugin `security-guidance` non è attivo di default. Per aggiungerlo nei progetti sensibili: `enabledPlugins` in `.claude/settings.json`.
