# PR Inventory — 2026-06-19

**Preflight:** PASS (6/6 configured repos; repoprompt-ce checked ad hoc — 0 open PRs)\
**Session:** cron `0 17 * * *` (Phase 2 salvage-and-cleanup)\
**Branch:** `cursor-agent/pr-salvage-and-cleanup-15b5`\
**Config:** `tasks/pr-review-agent.config.yaml`

## Scope summary

| Repo                                     | Open at start | Salvaged (draft) | Closed superseded | Deferred EOD | Open EOD |
| ---------------------------------------- | ------------: | ---------------: | ----------------: | -----------: | -------: |
| personal-config                          |             4 |                2 |                 3 |            1 |        3 |
| ctrld-sync                               |             0 |                0 |                 0 |            0 |        0 |
| email-security-pipeline                  |             0 |                0 |                 0 |            0 |        0 |
| Seatek_Analysis                          |             0 |                0 |                 0 |            0 |        0 |
| Hydrograph_Versus_Seatek_Sensors_Project |             0 |                0 |                 0 |            0 |        0 |
| series_correction_project_updated        |             1 |                0 |                 0 |            1 |        1 |
| repoprompt-ce                            |             0 |                0 |                 0 |            0 |        0 |

**Conflicted at start:** 3 (`DIRTY` — pc#1279, pc#1281, pc#1280)\
**Conflicted at end:** 0

## Prior tail reconciliation (since 2026-06-16)

| PR | Prior status | Current outcome |
| --- | --- | --- |
| pc #1261, #1249 | DEFER Phase 1 | **CLOSED** (merged or superseded by later automation) |
| ctrld #908 | Draft salvage | **CLOSED/MERGED** — queue cleared |
| esp #1115+ | DEFER | **MERGED** — queue cleared |
| hg #262 | Draft salvage | **CLOSED/MERGED** — queue cleared |
| sc #121 | CodeScene DEFER | **Still open** — cs-agent posted 2026-06-15 |

## Full inventory at session start

| Repo | PR | Author | Merge | CI | Disposition |
| --- | ---: | --- | --- | --- | --- |
| personal-config | [#1284](https://github.com/abhimehro/personal-config/pull/1284) | abhimehro (automation) | CLEAN | green | **DEFER** → Phase 1 merge candidate |
| personal-config | [#1281](https://github.com/abhimehro/personal-config/pull/1281) | abhimehro (Jules/Palette) | DIRTY | green | **SALVAGE → #1288** |
| personal-config | [#1280](https://github.com/abhimehro/personal-config/pull/1280) | app/cursor | DIRTY | green | **CLOSE-SUPERSEDED** |
| personal-config | [#1279](https://github.com/abhimehro/personal-config/pull/1279) | abhimehro (Jules/Sentinel) | DIRTY | green | **SALVAGE → #1287** |
| series_correction | [#121](https://github.com/abhimehro/series_correction_project_updated/pull/121) | abhimehro (Bolt) | MERGEABLE | CodeScene fail | **DEFER** |

## New salvage PRs opened (Phase 2)

| Repo | Old PR(s) | New draft PR | Notes |
| --- | --- | ---: | --- |
| personal-config | #1279 | [#1287](https://github.com/abhimehro/personal-config/pull/1287) | T1 security: osascript `--` separator (CWE-74) |
| personal-config | #1281 | [#1288](https://github.com/abhimehro/personal-config/pull/1288) | T3 a11y: podcast error `html_section()` only |

## Remainder (EOD)

| Repo | PR | Reason |
| --- | ---: | --- |
| personal-config | 1284 | CLEAN; all checks green — Phase 1 merge candidate |
| personal-config | 1287 | T1 draft salvage; await human security review |
| personal-config | 1288 | T3 draft salvage; await human review |
| series_correction | 121 | CodeScene fail; cs-agent already posted |
