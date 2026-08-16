# PR Triage — 2026-08-02
# PR Triage — Phase 2 Salvage 2026-08-02

Decision tree applied per `docs/automated-pr-salvage-agent.md` (S1–S6).
Input: Phase 1 remainder + live CONFLICTING re-fetch. Autonomous merges: **0**.

## Disposition summary

| Disposition | Count | PRs |
| ----------- | ----: | --- |
| SALVAGE (draft) | 1 | rpce #171 ← #165/#158 |
| CLOSE-SUPERSEDED | 4 | hg #445/#448/#450; rpce #158 |
| ESCALATE (human) | 3 | pc #1841; seatek #580/#573 |
| DEFER | 6 | rpce #144/#147/#148/#152/#157/#161 |
| Phase 1 hold (UNSTABLE) | 6 | rpce #163/#164/#168/#169/#170 + note on #165 |
| Empty queues | 3 repos | ctrld / esp / series |

## Deep-dive notes

### Hydrograph #445/#448/#450

`main` already imports `is_safe_path` and guards `--output` in `validate_data.py`.
#448 contained ×7 duplicated `is_safe_path` blocks (corruption). #450 only
extracted a `ValidationReporter` refactor. No residual security gap → close.

### rpce #158 vs #165 → #171

#165 MERGEABLE but UNSTABLE: real TOCTOU fix in `MCPConfigExportService` /
`MCPTerminalRecord` mixed with `ToolOutputFormatter` `.text(text:)` churn.
Salvaged **security files only** onto draft [#171](https://github.com/abhimehro/repoprompt-ce/pull/171).
Closed CONFLICTING twin #158.

### rpce DIRTY drift pile

100–400 files vs `main` each; titled intent buried in skill/CI/vendor noise.
DEFER with re-roll guidance; prefer MERGEABLE a11y/Bolt twins after CI green.

## Security gates

- No auth/payment/schema changes implemented.
- Security salvage #171 remains **draft** for human merge (S1).
- CLEAN Sentinels left open for human (never auto-merged).
# PR Triage — Phase 2 Salvage 2026-08-01

## Duplicate / overlap groups

1. **esp spam_analyzer fast-path:** #1401 (salvage of #1399 — auth + headers) vs #1405 (headers-only frozenset). Prefer **#1401**; close #1405 as overlapping after #1401 lands.
2. **pc parse_inventory:** #1875 (split bound + dotenv bulk-read) vs #1883 (defaultdict + **destroys** `.jules/bolt.md` 848→11 lines). Merge #1875; auto-fix #1883 by restoring journal or REQUEST_CHANGES if fix fails.
3. **pc defaultdict markers:** #1867 (repository_automation_tasks) — distinct from #1883; fix inline import then merge.
4. **Hydrograph path-hardening cluster:** #445/#448/#450 — all Sentinel, all CONFLICTING → Phase 2 consolidation (do not merge).
5. **rpce a11y / TOCTOU / perf:** #144/#161/#163/#169 a11y; #158/#165 TOCTOU; #157/#164/#170 DateFormatter — mostly CONFLICTING or red CI → Phase 2 / REQUEST_CHANGES.
6. **Demo stack:** #1871 → #1872 → #1873 (bases chained). Merge via `merge-async` on **#1873** (Lesson 0ez).
| Remainder item              | Live state         | Phase 2 action                                                      |
| --------------------------- | ------------------ | ------------------------------------------------------------------- |
| pc #1822 CORS               | DIRTY              | ESCALATE comment                                                    |
| pc #1841 timeout/auth       | CLEAN              | leave for human / Phase 1                                           |
| pc #1867 defaultdict        | MERGEABLE/UNSTABLE | leave (CI red)                                                      |
| pc #1857 microopts          | DIRTY              | SALVAGE → #1875; close #1857                                        |
| pc #1859 empty-state        | DIRTY              | SALVAGE a11y-safe → #1876; close #1859                              |
| pc #1825 asyncio            | DIRTY              | CLOSE no-op (junk files only)                                       |
| ctrld #1086 format          | CLEAN + prior RC   | leave                                                               |
| ctrld #1081 housekeeping    | DIRTY              | SALVAGE → #1105; close #1081                                        |
| esp #1399 Bolt spam         | DIRTY + CodeScene  | `/cs-agent` + spam-only SALVAGE → #1401; close #1399                |
| seatek #571 list-only       | CLEAN              | leave (T1 human)                                                    |
| seatek #573 file-read DoS   | CLEAN              | leave (security human)                                              |
| seatek #568 path hijack     | DIRTY              | ESCALATE                                                            |
| seatek #555 multi-root      | DIRTY              | ESCALATE                                                            |
| seatek #560 parallelize     | DIRTY              | REQUEST_CHANGES                                                     |
| seatek #554 warn tests      | DIRTY              | SALVAGE → #576; close #554                                          |
| hg #441/#443/#445/#448/#450 | CLEAN              | leave (security/deps human); #443 auto-resolved vs Phase 1 snapshot |
| series #336                 | gone               | queue drained                                                       |
| rpce #158 TOCTOU            | DIRTY drift        | ESCALATE                                                            |
| rpce #163/#164              | UNSTABLE           | leave Phase 1                                                       |
| rpce #144/#157/#161…        | DIRTY drift        | DEFER (focused re-roll needed)                                      |

## Disposition plan

| Disposition | PRs |
| ----------- | --- |
| MERGE (zero-diff) | pc#1882, esp#1404, Seatek#578, series#340 |
| MERGE | pc#1875, #1876; ctrld#1107, #1109; Seatek#581, #576; esp#1401 |
| MERGE (stack) | pc#1871–#1873 via merge-async top |
| MERGE-AFTER-FIX | pc#1867 (hoist import); pc#1883 (restore bolt.md) |
| CLOSE-DUPLICATE | esp#1405 after #1401 |
| ESCALATE | pc#1841; Seatek#580, #573; hg#445/#448/#450; rpce#165, #158 |
| REQUEST_CHANGES | rpce#170/#169/#168/#164/#163 (failing required Build/Secret Scan) |
| DEFER Phase 2 | rpce CONFLICTING remainder; Hydrograph Sentinels |
1. **ESP #1399 module collapse** — deletes `alert_*` / `media_*` modules into
   monoliths.
2. **PC #1859 a11y regression** — removes skip-link / landmarks while adding
   `empty-state`.
3. **PC #1825** — `patch3.diff` + `scratch_triage.py` only.
4. **RPCE DIRTY pile** — 10k–37k line branch drift; extract-on-demand only.

## Security gate notes

- All Sentinel PRs stay ESCALATE even if CI green (trust-boundary / path / TOCTOU / DoS).
- No secrets observed in merge-candidate diffs reviewed.
- `github-advanced-security` FAILURE noise ignored when overall rollup SUCCESS and required checks pass.
1. Seatek #571 (list-only shell) before #576 (warn rename) — same file.
2. pc #1875, #1876
3. ctrld #1105
4. esp #1401
5. Security CLEAN cluster (hg #445/#448/#450; seatek #573; pc #1841) — human
   only
