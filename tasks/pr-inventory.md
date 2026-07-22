# PR Inventory — 2026-07-21 (Phase 2 Salvage)

**Preflight:** PASS 7/7 (+ `make cursor-cloud-hooks`)  
**Mode:** salvage (draft-only; never auto-merge)  
**Input:** Phase 1 remainder from `tasks/pr-review-2026-07-21.md` (23 PRs)  
**Live re-fetch:** 23 → survivors classified below

| Repo | Open (EOD Phase 2) | Notes |
|------|-------------------:|-------|
| personal-config | 6 | 3 new salvage drafts + escalations/Phase-1 candidates |
| ctrld-sync | 0 | — |
| email-security-pipeline | 9 | 2 new salvage drafts + escalations/CodeScene defers |
| Seatek_Analysis | 0 | — |
| Hydrograph… | 0 | #374 numpy major **MERGED** since Phase 1 |
| series_correction… | 3 | auth cluster escalated |
| repoprompt-ce | 2 | tip artifact majors escalated |

## Phase 1 remainder disposition (live)

| Prior | Live state | Phase 2 action |
|-------|------------|----------------|
| pc #1724 | CLEAN (CodeScene green) | AUTO-RESOLVED → next Phase 1 |
| pc #1723/#1717/#1716 | DIRTY | SALVAGE → draft [#1734](https://github.com/abhimehro/personal-config/pull/1734) |
| pc #1726 | DIRTY | SALVAGE → draft [#1735](https://github.com/abhimehro/personal-config/pull/1735) |
| pc #1718 | DIRTY | SALVAGE → draft [#1736](https://github.com/abhimehro/personal-config/pull/1736) |
| pc #1721 | DIRTY | ESCALATE (GH_TOKEN.env cache) |
| pc #1706 | DIRTY docs | CLOSE-SUPERSEDED (this session) |
| esp #1320 | CLEAN | AUTO-RESOLVED → next Phase 1 |
| esp #1331/#1314 | DIRTY | SALVAGE → drafts [#1334](https://github.com/abhimehro/email-security-pipeline/pull/1334)/[#1335](https://github.com/abhimehro/email-security-pipeline/pull/1335) |
| esp #1328/#1324/#1319 | CLEAN | ESCALATE (secrets/auth) |
| esp #1327/#1330/#1311 | UNSTABLE | DEFER (+ `/cs-agent` posted on #1330/#1311) |
| hg #374 | MERGED | DROP |
| sc #275/#276/#268 | OPEN | ESCALATE (auth `dummy_todos.py`) |
| rpce #126/#127 | CLEAN | ESCALATE (Lesson 0dw tip artifacts) |
