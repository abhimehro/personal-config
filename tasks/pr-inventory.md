# PR Inventory — 2026-06-20

**Preflight:** PASS (6/6 configured repos; repoprompt-ce checked ad hoc)\
**Session:** cron `0 17 * * *` (Phase 2 salvage-and-cleanup)\
**Branch:** `cursor-agent/pr-salvage-and-cleanup-ce7c`\
**Config:** `tasks/pr-review-agent.config.yaml`

## Scope summary

| Repo                                     | Open at start | Salvaged (draft) | Closed superseded | Deferred EOD | Open EOD |
| ---------------------------------------- | ------------: | ---------------: | ----------------: | -----------: | -------: |
| personal-config                          |             3 |                0 |                 1 |            2 |        2 |
| ctrld-sync                               |             1 |                0 |                 0 |            1 |        1 |
| email-security-pipeline                  |             1 |                0 |                 0 |            1 |        1 |
| Seatek_Analysis                          |             0 |                0 |                 0 |            0 |        0 |
| Hydrograph_Versus_Seatek_Sensors_Project |             4 |                0 |                 0 |            4 |        4 |
| series_correction_project_updated        |             2 |                0 |                 1 |            1 |        1 |
| repoprompt-ce                            |             4 |                3 |                 3 |            1 |        4 |

**Conflicted at start:** 3 (`DIRTY` — rp#19, rp#20, rp#21)\
**Conflicted at end:** 0

## Prior tail reconciliation (since 2026-06-19)

| PR | Prior status | Current outcome |
| --- | --- | --- |
| pc #1284 | DEFER Phase 1 merge | **CLOSED** (not merged — maintainer closed 2026-06-20) |
| pc #1287, #1288 | T1/T3 draft salvage | **Still open** — UNSTABLE (Trunk Merge Queue checkbox only) |
| pc #1299 | Draft session doc | **CLOSED** superseded by agent branch |
| sc #121 | CodeScene DEFER | **Still open** — canonical perf PR |
| sc #132 | New Bolt PR | **CLOSED** duplicate of #121 |

## Full inventory at session start

| Repo | PR | Author | Merge | CI | Disposition |
| --- | ---: | --- | --- | --- | --- |
| personal-config | [#1287](https://github.com/abhimehro/personal-config/pull/1287) | abhimehro (salvage) | CLEAN | Trunk MQ fail | **DEFER** — human T1 review |
| personal-config | [#1288](https://github.com/abhimehro/personal-config/pull/1288) | abhimehro (salvage) | CLEAN | Trunk MQ fail | **DEFER** — human T3 review |
| personal-config | [#1299](https://github.com/abhimehro/personal-config/pull/1299) | app/cursor | CLEAN | green | **CLOSE-SUPERSEDED** |
| ctrld-sync | [#928](https://github.com/abhimehro/ctrld-sync/pull/928) | abhimehro (Palette) | CLEAN | benchmark alert | **DEFER** |
| email-security-pipeline | [#1136](https://github.com/abhimehro/email-security-pipeline/pull/1136) | abhimehro (Palette) | CLEAN | green | **DEFER** → Phase 1 merge |
| Hydrograph | [#281–284](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pulls) | dependabot | CLEAN | green | **DEFER** → Phase 1 merge |
| series_correction | [#121](https://github.com/abhimehro/series_correction_project_updated/pull/121) | abhimehro (Bolt) | CLEAN | CodeScene fail | **DEFER** |
| series_correction | [#132](https://github.com/abhimehro/series_correction_project_updated/pull/132) | abhimehro (Bolt) | CLEAN | CodeScene fail | **CLOSE-DUPLICATE** |
| repoprompt-ce | [#19](https://github.com/abhimehro/repoprompt-ce/pull/19) | abhimehro (Sentinel) | DIRTY | n/a | **SALVAGE → #23** |
| repoprompt-ce | [#20](https://github.com/abhimehro/repoprompt-ce/pull/20) | abhimehro | DIRTY | n/a | **SALVAGE → #24** |
| repoprompt-ce | [#21](https://github.com/abhimehro/repoprompt-ce/pull/21) | abhimehro (Palette) | DIRTY | n/a | **SALVAGE → #25** |
| repoprompt-ce | [#22](https://github.com/abhimehro/repoprompt-ce/pull/22) | abhimehro (Bolt) | CLEAN | Style fail | **DEFER** |

## New salvage PRs opened (Phase 2)

| Repo | Old PR(s) | New draft PR | Notes |
| --- | --- | ---: | --- |
| repoprompt-ce | #19 | [#23](https://github.com/abhimehro/repoprompt-ce/pull/23) | T1 security: Keychain accessibility |
| repoprompt-ce | #20 | [#24](https://github.com/abhimehro/repoprompt-ce/pull/24) | T3: Linux cross-platform test fixes |
| repoprompt-ce | #21 | [#25](https://github.com/abhimehro/repoprompt-ce/pull/25) | T3: icon button a11y labels |

## Remainder (EOD)

| Repo | PR | Reason |
| --- | ---: | --- |
| personal-config | 1287 | T1 draft salvage; Trunk MQ checkbox; await human security review |
| personal-config | 1288 | T3 draft salvage; Trunk MQ checkbox; await human review |
| ctrld-sync | 928 | Benchmark perf alert (1.59× regression); not a conflict |
| email-security-pipeline | 1136 | CLEAN; Phase 1 merge candidate |
| Hydrograph | 281–284 | CLEAN dependabot; Phase 1 merge candidates |
| series_correction | 121 | CodeScene fail; cs-agent history on canonical PR |
| repoprompt-ce | 23–25 | New draft salvages; await human review |
| repoprompt-ce | 22 | Style/dependency-review fail; no salvage opened |
