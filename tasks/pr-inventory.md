# PR Inventory — 2026-07-23 (Phase 2 Salvage)

**Preflight:** PASS 7/7 (+ `make cursor-cloud-hooks`)  
**Mode:** salvage (draft-only; never auto-merge)  
**Agent branch:** `cursor-agent/automated-pr-salvage-031d`  
**Input:** Phase 1 remainder from draft [#1755](https://github.com/abhimehro/personal-config/pull/1755) / `tasks/pr-review-2026-07-23.md` + live re-fetch

| Repo | PR | Author | Category | CI | Conflicts | Draft | Disposition |
|------|-----|--------|----------|----|-----------|-------|-------------|
| personal-config | 1755 | app/cursor | DOCS | OK | CLEAN | Y | DEFER human (Phase 1 docs) |
| personal-config | 1749 | app/cursor | DOCS | OK | CLEAN | Y | DEFER human (prior Phase 2 docs) |
| personal-config | 1748 | abhimehro | FEATURE | OK | CLEAN | Y | DEFER human (visual-recap salvage) |
| personal-config | 1744 | abhimehro | CI/INFRA | OK | CLEAN | N | ESCALATE SHA unpin |
| personal-config | 1721 | abhimehro | PERFORMANCE | OK | DIRTY | N | ESCALATE GH_TOKEN cache |
| ctrld-sync | — | — | — | — | — | — | zero open |
| email-security-pipeline | 1347 | abhimehro | REFACTOR | — | CLEAN | Y | **NEW** salvage #1320 |
| email-security-pipeline | 1346 | abhimehro | PERFORMANCE | — | CLEAN | Y | **NEW** salvage #1327 |
| email-security-pipeline | 1345 | abhimehro | CI/INFRA | OK | CLEAN | N | **CLOSED** no-op blank line |
| email-security-pipeline | 1342 | abhimehro | REFACTOR | OK | CLEAN | Y | DEFER human (prior salvage) |
| email-security-pipeline | 1341 | abhimehro | PERFORMANCE | OK | CLEAN | Y | DEFER human (prior salvage) |
| email-security-pipeline | 1328 | abhimehro | SECURITY | OK | CLEAN | N | ESCALATE TOCTOU |
| email-security-pipeline | 1327 | abhimehro | PERFORMANCE | FAIL CS | DIRTY | N | **CLOSED** → #1346 |
| email-security-pipeline | 1324 | abhimehro | SECURITY | OK | CLEAN | N | ESCALATE auth-results |
| email-security-pipeline | 1320 | abhimehro | REFACTOR | OK | CLEAN | N | **CLOSED** → #1347 |
| email-security-pipeline | 1319 | abhimehro | PERFORMANCE | OK | CLEAN | N | ESCALATE gh_token_cli |
| Seatek_Analysis | 518 | abhimehro | SECURITY | OK | CLEAN | N | ESCALATE env denylist |
| Seatek_Analysis | 514 | dependabot | DEPENDENCY | OK | CLEAN | N | ESCALATE pandas major |
| Seatek_Analysis | 511 | app/devin-ai-integration | REFACTOR | FAIL Trunk | CLEAN | N | ESCALATE path/IO |
| Seatek_Analysis | 507 | abhimehro | SECURITY | OK | CLEAN | N | ESCALATE sibling of #518 |
| Hydrograph… | — | — | — | — | — | — | zero open |
| series_correction… | 285 | abhimehro | SECURITY | FAIL CS | CLEAN | N | ESCALATE dummy_todos+CS |
| series_correction… | 276 | abhimehro | SECURITY | OK | CLEAN | N | ESCALATE 0ef |
| series_correction… | 275 | abhimehro | SECURITY | OK | DIRTY | N | ESCALATE 0ef |
| series_correction… | 268 | abhimehro | REFACTOR | OK | CLEAN | N | ESCALATE 0ef |
| repoprompt-ce | 127 | dependabot | DEPENDENCY | OK | CLEAN | N | ESCALATE tip artifact |
| repoprompt-ce | 126 | dependabot | DEPENDENCY | OK | CLEAN | N | ESCALATE tip artifact |

**Counts this run:** salvaged 2 · closed 3 · escalated 16 · deferred human drafts 5 · autonomous merges **0**
