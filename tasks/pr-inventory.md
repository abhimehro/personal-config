# PR Inventory — 2026-06-13

**Preflight:** PASS (6/6 configured repos; repoprompt-ce checked ad hoc)  
**Session:** cron `0 17 * * *` (Phase 2 salvage-and-cleanup)  
**Branch:** `cursor-agent/pr-salvage-and-cleanup-2e02`  
**Config:** `tasks/pr-review-agent.config.yaml`

## Scope summary (session start → end)

| Repo | Open at start | Salvaged (draft) | Closed superseded/stale | Deferred EOD | Open EOD |
| --- | ---: | ---: | ---: | ---: | ---: |
| personal-config | 5 | 1 | 1 | 4 | 5 |
| ctrld-sync | 3 | 0 | 1 | 2 | 2 |
| email-security-pipeline | 2 | 2 | 2 | 0 | 2 |
| Seatek_Analysis | 4 | 0 | 3 | 1 | 1 |
| Hydrograph_Versus_Seatek_Sensors_Project | 1 | 0 | 0 | 1 | 1 |
| series_correction_project_updated | 1 | 0 | 0 | 1 | 1 |
| repoprompt-ce | 0 | 0 | 0 | 0 | 0 |

**Conflicted at start:** 8 (`DIRTY` / `CONFLICTING`)  
**Conflicted at end:** 2 (#1236 session doc, #261 Gate-2 salvage)

## Full inventory at session start

| Repo | PR | Author | Merge | CI | Disposition |
| --- | ---: | --- | --- | --- | --- |
| personal-config | [#1236](https://github.com/abhimehro/personal-config/pull/1236) | app/cursor | DIRTY | green | **DEFER** (session doc conflict) |
| personal-config | [#1235](https://github.com/abhimehro/personal-config/pull/1235) | abhimehro (Bolt) | MERGEABLE | test fail (infra) | **DEFER** |
| personal-config | [#1234](https://github.com/abhimehro/personal-config/pull/1234) | abhimehro (Palette) | MERGEABLE | test fail (infra) | **DEFER** |
| personal-config | [#1231](https://github.com/abhimehro/personal-config/pull/1231) | app/cursor | MERGEABLE | green | **ESCALATE T0** (infra-fix) |
| personal-config | [#1230](https://github.com/abhimehro/personal-config/pull/1230) | abhimehro (Palette) | DIRTY | CodeScene fail | **SALVAGE → #1237** |
| ctrld-sync | [#893](https://github.com/abhimehro/ctrld-sync/pull/893) | abhimehro (Palette) | MERGEABLE | green | **DEFER** (Phase 1) |
| ctrld-sync | [#892](https://github.com/abhimehro/ctrld-sync/pull/892) | abhimehro (Bolt) | MERGEABLE | green | **DEFER** (Phase 1) |
| ctrld-sync | [#886](https://github.com/abhimehro/ctrld-sync/pull/886) | abhimehro (Palette) | DIRTY | green | **CLOSE → #893** |
| email-security-pipeline | [#1103](https://github.com/abhimehro/email-security-pipeline/pull/1103) | abhimehro (Bolt) | DIRTY | CodeScene fail | **SALVAGE → #1108** |
| email-security-pipeline | [#1096](https://github.com/abhimehro/email-security-pipeline/pull/1096) | abhimehro (Jules) | DIRTY | green | **SALVAGE → #1107** |
| Seatek_Analysis | [#283](https://github.com/abhimehro/Seatek_Analysis/pull/283) | abhimehro (Sentinel) | DIRTY | green | **CLOSE** (on main) |
| Seatek_Analysis | [#282](https://github.com/abhimehro/Seatek_Analysis/pull/282) | abhimehro (Bolt) | DIRTY | green | **CLOSE** (stale) |
| Seatek_Analysis | [#278](https://github.com/abhimehro/Seatek_Analysis/pull/278) | abhimehro (Bolt) | DIRTY | green | **CLOSE** (stale) |
| Seatek_Analysis | [#261](https://github.com/abhimehro/Seatek_Analysis/pull/261) | abhimehro (salvage) | DIRTY | green | **DEFER** (Gate 2) |
| Hydrograph_Versus_Seatek_Sensors_Project | [#257](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/257) | abhimehro (Jules) | MERGEABLE | CodeScene fail | **DEFER** |
| series_correction_project_updated | [#114](https://github.com/abhimehro/series_correction_project_updated/pull/114) | abhimehro (Bolt) | MERGEABLE | CodeScene fail | **DEFER** |

## Prior tail reconciliation (from 2026-06-12)

| PR | Prior status | Current outcome |
| --- | --- | --- |
| ctrld #882 | DEFER benchmark | **MERGED** 2026-06-13 |
| esp #1075 | DEFER salvage | **CLOSED** (superseded) |
| sa #276, #291 | DEFER salvage batch | **CLOSED** |
| sc #114 | DEFER CodeScene | Still open; cs-agent posted |
| pc #1227 | MERGED | — |

## New salvage PRs opened this session

| Repo | Old PR | New draft PR | Notes |
| --- | ---: | ---: | --- |
| personal-config | #1230 | [#1237](https://github.com/abhimehro/personal-config/pull/1237) | `analytics_dashboard.sh` ARIA only |
| email-security-pipeline | #1096 | [#1107](https://github.com/abhimehro/email-security-pipeline/pull/1107) | `ConnectionConfig` refactor |
| email-security-pipeline | #1103 | [#1108](https://github.com/abhimehro/email-security-pipeline/pull/1108) | `media_analyzer.py` parallelization |
