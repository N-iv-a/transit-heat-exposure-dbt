---
name: dev-loop
description: Esegue task da tasks/coda.md con specialisti backend/frontend, controlli a livelli e gate di sicurezza. Usalo per "procedi con la coda", "fai T03", "esegui i prossimi N task".
---
# Dev-loop

Argomento: un ID (`T03`), `coda` (fino a coda vuota o primo blocco) o `coda N`.
Regola di consumo: tutto ciò che è deterministico passa dagli script, che stampano solo l'esito. Gli agent servono solo dove serve giudizio.

## 0. Avvio (una volta per sessione)
- Se sei sul branch base (`.git.base` in loop.json), crea `loop/<primo-ID>`.
- `scripts/loop/check.sh baseline`, solo se `.claude/run/baseline.txt` manca. Un FAIL già in baseline non è colpa del task.

## Per ogni task
Riga in coda: `- [ ] T01 [BE|FE|MIX] [S|M|L] titolo — dettagli {k=v ...}`.

1. **Livelli.** `scripts/loop/level.sh effective k=v ...` con gli override tra graffe. Chiamalo L. In `mode` backend o frontend l'area è forzata.
2. **Piano.**
   - `L.plan=inline`, o `auto` con task S: piano tuo in massimo 10 righe.
   - `L.plan=agent`, o `auto` con task M/L: agent `planner`, model `L.models.planner`.
   - Se cambia il contratto, lo scrivi tu in contract/ prima dei dev.
3. **Sviluppo.** Agent `backend-dev` e/o `frontend-dev`, model `L.models.dev`. Nel prompt: task, piano, file di contratto, base del branch. MIX: i due dev partono in parallelo sul contratto.
4. **Verifica.**
   - `L.test=script`: `scripts/loop/check.sh all <area>`.
   - `L.test=agent`: agent `<area>-tester`, model `L.models.tester`.
   - `L.test=off`: salta.
   - Su FAIL riprendi lo stesso dev con SendMessage passando solo le righe di errore; non crearne uno nuovo. Dopo `limits.dev_retries` tentativi fermati e riporta.
   - MIX con `L.e2e` diverso da off: `scripts/loop/check.sh e2e frontend` dopo entrambe le aree.
5. **Docs.**
   - `off`: niente.
   - `touched`: aggiorni la fonte di verità solo se il diff cambia contratto, comandi o struttura.
   - `full`: rileggi le parti della fonte di verità toccate dal diff e le allinei.
6. **Gate.**
   - Sempre: `scripts/loop/check.sh secrets <base>`.
   - `L.gate=lite` o `full`: agent `security-reviewer`, model `L.models.reviewer`, passando livello, base e messaggio di commit proposto.
   - NO-GO: torna al dev competente con i punti; il reviewer non corregge.
7. **Commit.** `scripts/loop/commit.sh "<tipo>(<scope>): <messaggio>"`, poi segna `[x]` il task in coda.

## Stop
Ti fermi e chiedi quando:
- il contratto va rivisto dopo lo sviluppo;
- serve una nuova dipendenza o un file condiviso;
- il gate dice NO-GO due volte;
- un task contraddice la fonte di verità.

## Report (uno per task, massimo 7 righe)
`T01 · <area>/<taglia> · profilo+override` / Esito check / Gate / Commit / Docs / Agent usati con modello (es. dev×2 sonnet, reviewer×1 sonnet) / Aperto
