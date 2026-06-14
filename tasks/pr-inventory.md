# PR Inventory — 2026-06-14

**Preflight:** PASS (6/6 configured repos; repoprompt-ce checked ad hoc — 0 open PRs)  
**Session:** cron `0 17 * * *` (Phase 2 salvage-and-cleanup)  
**Branch:** `cursor-agent/pr-salvage-and-cleanup-e035`  
**Config:** `tasks/pr-review-agent.config.yaml`

## Scope summary (session start → end)

| Repo | Open at start | Salvaged (draft) | Closed superseded/stale/duplicate | Deferred EOD | Open EOD |
| --- | ---: | ---: | ---: | ---: | ---: |
| personal-config | 8 | 0 | 3 | 4 | 5 |
| ctrld-sync | 1 | 1 | 1 | 0 | 1 |
| email-security-pipeline | 4 | 0 | 1 | 3 | 3 |
| Seatek_Analysis | 1 | 0 | 1 | 0 | 0 |
| Hydrograph_Versus_Seatek_Sensors_Project | 1 | 0 | 0 | 1 | 1 |
| series_correction_project_updated | 1 | 0 | 0 | 1 | 1 |
| repoprompt-ce | 0 | 0 | 0 | 0 | 0 |

**Conflicted at start:** 3 (`DIRTY` / `CONFLICTING`) — pc#1244, ctrld#898, sa#261  
**Conflicted at end:** 0

## Full inventory at session start

| Repo | PR | Author | Merge | CI | Disposition |
| --- | ---: | --- | --- | --- | --- |
| personal-config | [#1244](https://github.com/abhimehro/personal-config/pull/1244) | app/cursor | DIRTY | green | **CLOSE** (session doc) |
| personal-config | [#1245](https://github.com/abhimehro/personal-config/pull/1245) | abhimehro (Palette) | MERGEABLE | test fail (infra) | **CLOSE** (dup #1242) |
| personal-config | [#1243](https://github.com/abhimehro/personal-config/pull/1243) | abhimehro (Bolt) | MERGEABLE | test fail (infra) | **DEFER** (Phase 1) |
| personal-config | [#1242](https://github.com/abhimehro/personal-config/pull/1242) | abhimehro (Palette) | MERGEABLE | test fail (infra) | **DEFER** (Phase 1) |
| personal-config | [#1240](https://github.com/abhimehro/personal-config/pull/1240) | app/cursor | MERGEABLE | green | **ESCALATE T0** (infra-fix) |
| personal-config | [#1235](https://github.com/abhimehro/personal-config/pull/1235) | abhimehro (Bolt) | MERGEABLE | test fail (infra) | **DEFER** (Phase 1) |
| personal-config | [#1234](https://github.com/abhimehro/personal-config/pull/1234) | abhimehro (Palette) | MERGEABLE | test fail (infra) | **DEFER** (Phase 1) |
| personal-config | [#1231](https://github.com/abhimehro/personal-config/pull/1231) | app/cursor | MERGEABLE | green | **CLOSE** (dup #1240) |
| ctrld-sync | [#898](https://github.com/abhimehro/ctrld-sync/pull/898) | abhimehro (Bolt) | DIRTY | CodeScene fail | **SALVAGE → #899** |
| email-security-pipeline | [#1112](https://github.com/abhimehro/email-security-pipeline/pull/1112) | abhimehro (Palette) | MERGEABLE | green | **DEFER** (Phase 1) |
| email-security-pipeline | [#1111](https://github.com/abhimehro/email-security-pipeline/pull/1111) | abhimehro (Jules QA) | CLEAN | green | **DEFER** (Phase 1) |
| email-security-pipeline | [#1109](https://github.com/abhimehro/email-security-pipeline/pull/1109) | abhimehro (Palette) | CLEAN | green | **CLOSE** (dup #1112) |
| email-security-pipeline | [#1107](https://github.com/abhimehro/email-security-pipeline/pull/1107) | abhimehro (salvage) | MERGEABLE | green | **DEFER** (human merge) |
| Seatek_Analysis | [#261](https://github.com/abhimehro/Seatek_Analysis/pull/261) | abhimehro (salvage) | DIRTY | green | **CLOSE** (Gate 2) |
| Hydrograph_Versus_Seatek_Sensors_Project | [#257](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/257) | abhimehro (Jules) | MERGEABLE | CodeScene fail | **DEFER** |
| series_correction_project_updated | [#119](https://github.com/abhimehro/series_correction_project_updated/pull/119) | abhimehro (Bolt) | MERGEABLE | CodeScene fail | **DEFER** |

## Prior tail reconciliation (from 2026-06-13)

| PR | Prior status | Current outcome |
| --- | --- | --- |
| pc #1237 | draft salvage | **CLOSED** (dup #1242) |
| pc #1236 | DEFER session doc | **CLOSED** |
| ctrld #892, #893 | Phase 1 merge | **#892 MERGED**; #893 closed |
| esp #1108 | draft salvage | **MERGED** |
| sc #114 | DEFER CodeScene | **CLOSED**; superseded by #119 |

## New salvage PR opened this session

| Repo | Old PR | New draft PR | Notes |
| --- | ---: | ---: | --- |
| ctrld-sync | #898 | [#899](https://github.com/abhimehro/ctrld-sync/pull/899) | Content-Type `any()` unroll on post-#892 `main` |
