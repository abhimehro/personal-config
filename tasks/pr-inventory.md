# PR Inventory — Phase 2 Salvage — 2026-07-16

**Trigger:** Cron Phase 2 `0 17 * * *`  
**Agent branch:** `cursor-agent/automated-pr-salvage-2f38`  
**Input:** Phase 1 report from [#1659](https://github.com/abhimehro/personal-config/pull/1659) + live GitHub re-fetch  
**Preflight:** PASS 6/6 (+ repoprompt-ce read; cursor-cloud-hooks)

## Scope repos

| Repo | Open at Phase 2 start (approx) | Open at Phase 2 end |
|------|-------------------------------:|--------------------:|
| personal-config | 16 | 8 |
| ctrld-sync | 1 | 1 |
| email-security-pipeline | 6 | 5 |
| Seatek_Analysis | 3 | 2 |
| Hydrograph_Versus_Seatek_Sensors_Project | 3 | 3 |
| series_correction_project_updated | 4 | 4 |
| repoprompt-ce | 0 | 0 |

## Bot / automation authors in scope

dependabot, renovate, google-labs-jules, cursor, devin, copilot, plus abhimehro-authored bot branches (Jules/Bolt/Palette/cursor-agent).

## Prior remainder reconciliation (from 2026-07-15)

| PR | Prior status | Live status |
|----|--------------|-------------|
| pc #1623 | draft salvage | DIRTY → re-salvaged as #1664 |
| pc #1609 | deferred Devin | **MERGED** |
| cs #990 | escalated SSRF | **MERGED** |
| esp #1259 | escalated deps | **MERGED** |
| esp #1264 | CI green | **MERGED** (Phase 1 today) |
| hg #366 | draft salvage | **MERGED** (Phase 1 today) |
| hg #357 | escalated poetry | **MERGED** |
| rpce #112 | escalated auth | **MERGED** |
| sc #210 | escalated | **CLOSED** (superseded earlier) |

## Phase 1 deferred conflict queue (23) — disposition summary

See `tasks/pr-triage.md` for full decision tree outcomes.
