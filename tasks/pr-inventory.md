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
# PR Inventory — 2026-07-28 (Phase 1)

**Preflight:** PASS 7/7 · **Mode:** review-and-merge · squash · stale 30d · auto-fix on  
**Auth:** `unset GH_TOKEN` (Lesson 0eo); Cursor hosts.yml for merges; MCP for reviews  
**Branch:** `cursor-agent/automated-pr-workflow-3d54`

## Summary

| Repo | Open at start | In-scope | Merged | Open EOD |
|------|--------------:|---------:|-------:|---------:|
| personal-config | 13 | 13 | 3 | 10 |
| ctrld-sync | 8 | 8 | 4 | 4 |
| email-security-pipeline | 7 | 7 | 3 | 4 |
| Seatek_Analysis | 6 | 6 | 2 | 4 |
| Hydrograph_Versus_Seatek_Sensors_Project | 7 | 7 | 2 | 5 |
| series_correction_project_updated | 6 | 6 | 2 | 4 |
| repoprompt-ce | 0 | 0 | 0 | 0 |
| **Total** | **47** | **47** | **16** | **31** |

## Inventory table (start-of-session)

| Repo | PR | Author | Category | CI | Conflicts | Age | Disposition |
|------|---:|--------|----------|----|-----------|----:|-------------|
| personal-config | 1801 | abhimehro | PERFORMANCE | PASS | MERGEABLE | 0 | MERGE |
| personal-config | 1800 | abhimehro | PERFORMANCE | PASS | →CONFLICTING | 0 | DEFER |
| personal-config | 1798 | abhimehro | CI/INFRA | PASS | MERGEABLE | 0 | MERGE |
| personal-config | 1796 | abhimehro | SECURITY | PASS | MERGEABLE | 0 | ESCALATE |
| personal-config | 1795 | abhimehro | UI | PASS | MERGEABLE | 0 | MERGE |
| personal-config | 1794 | abhimehro | SECURITY | PASS | MERGEABLE | 0 | ESCALATE |
| personal-config | 1793 | app/cursor | CI/INFRA | PASS | draft | 0 | DEFER |
| personal-config | 1792 | abhimehro | UI | PASS | MERGEABLE | 0 | REQUEST_CHANGES |
| personal-config | 1791 | abhimehro | PERFORMANCE | PASS | →CONFLICTING | 1 | DEFER |
| personal-config | 1789 | abhimehro | SECURITY | PASS | MERGEABLE | 1 | ESCALATE |
| personal-config | 1787 | abhimehro | SECURITY | PASS | MERGEABLE | 1 | ESCALATE |
| personal-config | 1786 | abhimehro | SECURITY | PASS | MERGEABLE | 1 | ESCALATE |
| personal-config | 1784 | abhimehro | SECURITY | PASS | MERGEABLE | 1 | ESCALATE |
| ctrld-sync | 1071 | dependabot | DEPENDENCY | PASS | MERGEABLE | 0 | MERGE |
| ctrld-sync | 1070 | dependabot | DEPENDENCY | PASS | MERGEABLE | 0 | MERGE |
| ctrld-sync | 1069 | abhimehro | UI | PASS | MERGEABLE | 0 | CLOSE-DUP (rec) |
| ctrld-sync | 1068 | abhimehro | CI/INFRA | PASS | ZERO | 0 | MERGE |
| ctrld-sync | 1067 | abhimehro | UI | PASS | MERGEABLE | 0 | MERGE |
| ctrld-sync | 1066 | abhimehro | UI | FAIL CS | MERGEABLE | 1 | CLOSE-DUP (rec) |
| ctrld-sync | 1064 | abhimehro | UI | PASS | →CONFLICTING | 1 | DEFER |
| ctrld-sync | 1060 | abhimehro | SECURITY | PASS | MERGEABLE | 3 | ESCALATE |
| email-security-pipeline | 1376 | abhimehro | CI/INFRA | PASS | ZERO | 0 | MERGE |
| email-security-pipeline | 1375 | abhimehro | SECURITY | PASS | MERGEABLE | 0 | ESCALATE |
| email-security-pipeline | 1373 | dependabot | DEPENDENCY | PASS | MERGEABLE | 0 | MERGE |
| email-security-pipeline | 1372 | abhimehro | UI | PASS | MERGEABLE | 0 | MERGE |
| email-security-pipeline | 1370 | abhimehro | SECURITY | PASS | MERGEABLE | 1 | ESCALATE |
| email-security-pipeline | 1366 | abhimehro | CI/INFRA | PASS | MERGEABLE | 2 | REQUEST_CHANGES |
| email-security-pipeline | 1362 | abhimehro | SECURITY | PASS | CONFLICTING | 2 | ESCALATE |
| Seatek_Analysis | 537 | abhimehro | CI/INFRA | PASS | ZERO | 0 | MERGE |
| Seatek_Analysis | 535 | app/cursor | CI/INFRA | FAIL | MERGEABLE | 0 | REQUEST_CHANGES |
| Seatek_Analysis | 533 | abhimehro | CI/INFRA | PASS | ZERO | 1 | MERGE |
| Seatek_Analysis | 525 | abhimehro | SECURITY | PASS | MERGEABLE | 4 | ESCALATE |
| Seatek_Analysis | 518 | abhimehro | SECURITY | PASS | MERGEABLE | 5 | ESCALATE |
| Seatek_Analysis | 507 | abhimehro | SECURITY | PASS | MERGEABLE | 6 | ESCALATE |
| Hydrograph… | 428 | abhimehro | PERFORMANCE | PASS | MERGEABLE | 0 | MERGE |
| Hydrograph… | 427 | abhimehro | PERFORMANCE | PASS | MERGEABLE | 0 | CLOSE-DUP (rec) |
| Hydrograph… | 425 | abhimehro | SECURITY | PASS | MERGEABLE | 0 | ESCALATE |
| Hydrograph… | 422 | app/cursor | CI/INFRA | PASS | MERGEABLE | 0 | MERGE |
| Hydrograph… | 420 | abhimehro | PERFORMANCE | PASS | MERGEABLE | 1 | CLOSE-DUP (rec) |
| Hydrograph… | 418 | abhimehro | SECURITY | PASS | MERGEABLE | 1 | ESCALATE |
| Hydrograph… | 413 | abhimehro | SECURITY | PASS | CONFLICTING | 3 | ESCALATE |
| series_correction… | 299 | abhimehro | REFACTOR | PASS | MERGEABLE | 0 | MERGE |
| series_correction… | 297 | app/cursor | CI/INFRA | PASS | draft | 0 | DEFER |
| series_correction… | 296 | abhimehro | PERFORMANCE | PASS | MERGEABLE | 1 | ESCALATE |
| series_correction… | 295 | abhimehro | SECURITY | PASS | MERGEABLE | 1 | ESCALATE |
| series_correction… | 294 | dependabot | DEPENDENCY | PASS | MERGEABLE | 1 | MERGE |
| series_correction… | 293 | abhimehro | REFACTOR | PASS | MERGEABLE | 1 | CLOSE-DUP (rec) |
| repoprompt-ce | — | — | — | — | — | — | none open |
