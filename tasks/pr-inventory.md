# PR Inventory — 2026-07-24 (Phase 1)

**Preflight:** PASS 7/7 (+ `make cursor-cloud-hooks`)  
**Mode:** review-and-merge (squash) · **Stale:** 30d · **Auto-fix:** on  
**Branch:** `cursor-agent/pr-workflow-automation-95f6`  
**Open total:** 43 · **In-scope:** 41 (incl. Sentinel #525 + QA #285)

| Repo | # | Author | Cat | CI | Mergeable | Age | Notes |
|------|--:|--------|-----|----|-----------|----:|-------|
| personal-config | 1763 | abhimehro (Bolt) | PERFORMANCE | PASS | CLEAN | 0 | regex hoist morning-brief |
| personal-config | 1758 | dependabot | DEPENDENCY | PASS* | CLEAN | 0 | gh-aw setup 0.83.1 (*stale CANCELLED in rollup; `gh pr checks` green) |
| personal-config | 1756 | cursor | CI/INFRA | PASS | CLEAN | 0 | draft Phase 2 salvage docs |
| personal-config | 1748 | abhimehro | CI/INFRA | PASS | CLEAN | 1 | visual-recap salvage; toolchain |
| personal-config | 1744 | abhimehro | CI/INFRA | PASS | CLEAN | 2 | SHA→tag unpin (Lesson 0z) |
| personal-config | 1721 | abhimehro (Bolt) | SECURITY | PASS | CONFLICTING | 3 | GH_TOKEN env cache |
| ctrld-sync | 1058 | dependabot | DEPENDENCY | PASS | CLEAN | 0 | gh-aw setup |
| ctrld-sync | 1057 | dependabot | DEPENDENCY | PASS | CLEAN | 0 | ruby/setup-ruby |
| ctrld-sync | 1056 | dependabot | DEPENDENCY | PASS | CLEAN | 0 | gh-aw |
| ctrld-sync | 1055 | abhimehro (Palette) | UI | PASS | CLEAN | 0 | **zero-diff** |
| ctrld-sync | 1053 | abhimehro (Palette) | REFACTOR | PASS | CLEAN | 0 | clear-cache helper |
| email-security-pipeline | 1355 | abhimehro (Jules QA) | REFACTOR | PASS | CLEAN | 0 | E303 blank line |
| email-security-pipeline | 1354 | abhimehro (Bolt) | PERFORMANCE | PASS | CLEAN | 0 | address format loop |
| email-security-pipeline | 1353 | abhimehro (Sentinel) | SECURITY | PASS | CLEAN | 0 | TOCTOU chmod |
| email-security-pipeline | 1352 | dependabot | DEPENDENCY | PASS | CLEAN | 0 | gh-aw setup |
| email-security-pipeline | 1351 | dependabot | DEPENDENCY | PASS | CLEAN | 0 | gh-aw setup-cli |
| email-security-pipeline | 1350 | dependabot | DEPENDENCY | PASS | CLEAN | 0 | ruby/setup-ruby |
| email-security-pipeline | 1348 | cursor | CI/INFRA | PASS | CLEAN | — | draft AGENTS.md note |
| email-security-pipeline | 1347 | abhimehro | REFACTOR | PASS | CLEAN | — | salvage subject validator |
| email-security-pipeline | 1346 | abhimehro | PERFORMANCE | PASS | CLEAN | — | salvage SPF helper |
| email-security-pipeline | 1342 | abhimehro | REFACTOR | PASS | CLEAN | — | IMAPClient config API |
| email-security-pipeline | 1341 | abhimehro | PERFORMANCE | PASS | CLEAN | — | extend+comprehension |
| email-security-pipeline | 1328 | abhimehro | SECURITY | PASS | CLEAN | — | TOCTOU sibling |
| email-security-pipeline | 1324 | abhimehro (Bolt) | SECURITY | PASS | CLEAN | — | Auth-Results scoring |
| email-security-pipeline | 1319 | abhimehro (Bolt) | SECURITY | PASS | CLEAN | — | gh_token_cli writes |
| Seatek_Analysis | 525 | abhimehro (Sentinel) | SECURITY | PASS | CLEAN | 0 | env filter order |
| Seatek_Analysis | 524 | abhimehro (Jules) | CI/INFRA | PASS | CLEAN | 0 | **zero-diff** |
| Seatek_Analysis | 522 | cursor | DEPENDENCY | PASS | CLEAN | 0 | draft pillow≥12.3.0 CVE pin |
| Seatek_Analysis | 521 | dependabot | DEPENDENCY | PASS | CLEAN | 0 | pandas 2→3 major |
| Seatek_Analysis | 520 | dependabot | DEPENDENCY | PASS | CLEAN | 0 | ruby/setup-ruby |
| Seatek_Analysis | 518 | abhimehro (Sentinel) | SECURITY | PASS | CLEAN | 1 | env denylist |
| Seatek_Analysis | 511 | devin | SECURITY | FAIL | CLEAN | 2 | Trunk MQ fail |
| Seatek_Analysis | 507 | abhimehro (Sentinel) | SECURITY | PASS | CLEAN | 2 | env merge sibling |
| Hydrograph… | 408 | dependabot | DEPENDENCY | PASS | CLEAN | 0 | pre-commit |
| Hydrograph… | 407 | dependabot | DEPENDENCY | PASS | CLEAN | 0 | colorlog |
| Hydrograph… | 406 | dependabot | DEPENDENCY | PASS | CLEAN | 0 | ruby/setup-ruby |
| series_correction… | 288 | abhimehro (Jules QA) | REFACTOR | PASS | CLEAN | 0 | typing/import hygiene |
| series_correction… | 285 | abhimehro | SECURITY | FAIL | CLEAN | 1 | dummy_todos + CodeScene |
| series_correction… | 276 | abhimehro (Jules) | SECURITY | PASS | CLEAN | 3 | DoS whitespace |
| series_correction… | 275 | abhimehro (Jules) | SECURITY | PASS | CONFLICTING | 3 | auth+DoS |
| series_correction… | 268 | abhimehro (Jules) | SECURITY | PASS | CLEAN | 3 | json loop |
| repoprompt-ce | 127 | dependabot | DEPENDENCY | PASS | CLEAN | 7 | upload-artifact 4→7 |
| repoprompt-ce | 126 | dependabot | DEPENDENCY | PASS | CLEAN | 7 | download-artifact 4→8 |

## Out of autonomous merge scope (still listed)

Ordinary human PRs without automation signals: none beyond the Sentinel/QA cases above (already in-scope via title/branch).
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
