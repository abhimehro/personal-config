# Phase 2 Salvage — 2026-07-30 (cron 17:00 UTC)

## Preflight
- [x] `gh auth` as abhimehro PAT (Lesson 0ew)
- [x] Preflight PASS 7/7 + `make cursor-cloud-hooks`
- [x] Re-fetch live PR state vs Phase 1 remainder

## Phase 1 remainder actions
- [x] CLOSE-SUPERSEDED pc #1827
- [x] CLOSE-SUPERSEDED rpce #151
- [x] ESCALATE pc #1822, seatek #552, series #315
- [x] Salvage pc #1820 → #1836; close #1820/#1821
- [x] CLOSE #1819 prefer #1831
- [x] REQUEST_CHANGES rpce #144

## Additional CONFLICTING
- [x] Seatek tests salvage → #565; close #551/#553/#557/#558; defer #554/#563
- [x] series #313 → #332; #329 → #333; close #320; defer #327
- [x] rpce #146/#149/#150 → #157

## Deliverables
- [x] `pr-inventory.md`, `pr-triage.md`, `pr-review-2026-07-30.md`
- [x] Append `salvage-session-reports.md` + Lesson **0ey**
- [x] Commit/push docs branch + open_git_pr
- [x] Notion + Memory update
- [x] Autonomous merges: **0**
# Weekly Repository Health — General (2026-07-30)

## personal-config
- [x] Fix README broken ProtonDrive / dns-setup references
- [x] Fix monthly_maintenance.sh undefined $EXIT_CODE
- [x] Fix workflows README count (greetings.yml)
- [x] File issue for maintenance orchestration split (#1834)

## email-security-pipeline
- [x] Remove tracked root junk / dump artifacts
- [x] Fix README Quick Start Option gap + test_config path
- [x] File issue for god modules / stale branches (#1391)

## ctrld-sync
- [x] Remove tracked junk files
- [x] Fix AGENTS.md multi-module + Docker reality
- [x] Extend CI coverage to api_client/cache + root test_main.py
- [x] File issue for main.py further extraction (#1082)

## repoprompt-ce
- [x] Fix version.env merge conflict garbage
- [x] File issue for AgentMode god-files / missing PR templates (#155)

## Deliverables
- Draft PRs: #1833, #1081, #1390, #154
