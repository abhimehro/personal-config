# PR Inventory — 2026-07-27 (Phase 2 Salvage)

**Source:** Live `gh pr list` after Phase 1 `tasks/pr-review-2026-07-26.md`  
**Preflight:** PASS 7/7 · `unset GH_TOKEN` (0eo) · `make cursor-cloud-hooks`  
**Branch:** `cursor-agent/automated-pr-salvage-workflow-3074`

## Scope filter

Bot / automation-authored open PRs (dependabot, renovate, Jules/Sentinel/Bolt/Palette branch patterns, cursor-agent, Devin, Copilot). Phase 2 focuses on **CONFLICTING** + Phase 1 **ESCALATE** remainder.

## Live open counts

| Repo | Open | CONFLICTING | Notes |
|------|-----:|------------:|-------|
| personal-config | 5 | 0 | New since Phase 1 (Sentinel/security/Bolt) — Phase 1 territory |
| ctrld-sync | 3 | 0 | #1060 escalated; #1066 CodeScene fail |
| email-security-pipeline | 3 | 1 | #1362 DIRTY; #1370 preferred twin; #1366 skew |
| Seatek_Analysis | 5 | 0 | #507/#518/#525 cluster; #521 MERGED since Phase 1 |
| Hydrograph… | 4 | 1 | #413 DIRTY; #418 preferred twin |
| series_correction… | 5 | 0 | New CLEAN queue — not Phase 2 conflict salvage |
| repoprompt-ce | 0 | 0 | Quiet |
| **Total** | **25** | **2** | |

## CONFLICTING (Phase 2 primary)

| Repo | PR | Title | Author pattern | Sibling |
|------|---:|-------|----------------|---------|
| email-security-pipeline | [1362](https://github.com/abhimehro/email-security-pipeline/pull/1362) | Sentinel TOCTOU config perms | Jules/Sentinel | [#1370](https://github.com/abhimehro/email-security-pipeline/pull/1370) CLEAN |
| Hydrograph… | [413](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/413) | Sentinel device-file DoS | Jules/Sentinel | [#418](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/418) CLEAN |

## Phase 1 remainder — live status

| PR | Phase 1 reason | Live state | Phase 2 action |
|----|----------------|------------|----------------|
| cs [#1060](https://github.com/abhimehro/ctrld-sync/pull/1060) | Sentinel exception chaining | OPEN CLEAN all checks green | ESCALATE T1 |
| esp [#1366](https://github.com/abhimehro/email-security-pipeline/pull/1366) | artifact v7/v8 skew (0er) | OPEN CLEAN | REQUEST_CHANGES |
| esp [#1362](https://github.com/abhimehro/email-security-pipeline/pull/1362) | TOCTOU CONFLICTING | OPEN DIRTY | CLOSE-SUPERSEDED |
| Seatek [#525](https://github.com/abhimehro/Seatek_Analysis/pull/525)/[#518](https://github.com/abhimehro/Seatek_Analysis/pull/518)/[#507](https://github.com/abhimehro/Seatek_Analysis/pull/507) | env-filter 0ej | OPEN CLEAN | ESCALATE cluster |
| Seatek [#521](https://github.com/abhimehro/Seatek_Analysis/pull/521) | pandas major 0ek | **MERGED** 2026-07-27 | DROP |
| hg [#413](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/413) | DoS salvage only | OPEN DIRTY | CLOSE-SUPERSEDED by #418 |

## New CLEAN (inventory only — not Phase 2 salvage)

personal-config #1791/#1789/#1787/#1786/#1784 · ctrld #1066/#1064 · Seatek #535/#533 · hg #422/#420/#418 · series #297/#296/#295/#294/#293
