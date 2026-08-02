# PR Triage — 2026-08-02

## Duplicate / overlap groups

1. **esp spam_analyzer fast-path:** #1401 (salvage of #1399 — auth + headers) vs #1405 (headers-only frozenset). Prefer **#1401**; close #1405 as overlapping after #1401 lands.
2. **pc parse_inventory:** #1875 (split bound + dotenv bulk-read) vs #1883 (defaultdict + **destroys** `.jules/bolt.md` 848→11 lines). Merge #1875; auto-fix #1883 by restoring journal or REQUEST_CHANGES if fix fails.
3. **pc defaultdict markers:** #1867 (repository_automation_tasks) — distinct from #1883; fix inline import then merge.
4. **Hydrograph path-hardening cluster:** #445/#448/#450 — all Sentinel, all CONFLICTING → Phase 2 consolidation (do not merge).
5. **rpce a11y / TOCTOU / perf:** #144/#161/#163/#169 a11y; #158/#165 TOCTOU; #157/#164/#170 DateFormatter — mostly CONFLICTING or red CI → Phase 2 / REQUEST_CHANGES.
6. **Demo stack:** #1871 → #1872 → #1873 (bases chained). Merge via `merge-async` on **#1873** (Lesson 0ez).

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

## Security gate notes

- All Sentinel PRs stay ESCALATE even if CI green (trust-boundary / path / TOCTOU / DoS).
- No secrets observed in merge-candidate diffs reviewed.
- `github-advanced-security` FAILURE noise ignored when overall rollup SUCCESS and required checks pass.
