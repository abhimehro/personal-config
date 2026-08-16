# PR Inventory — 2026-08-02

Phase 1 cron. Preflight PASS 7/7. Auth: `abhimehro` PAT.
Scope: automation-driven open PRs (bot authors + human-authored Bolt/Jules/Sentinel/Palette/salvage/demo-stack).

| Repo | PR | Author signal | Category | CI rollup | Conflicts | Age | Files | Status |
| ---- | -- | ------------- | -------- | --------- | --------- | --- | ----- | ------ |
| personal-config | 1883 | Bolt | PERFORMANCE | SUCCESS | MERGEABLE | 0 | 2 | REVIEW — journal wipe risk |
| personal-config | 1882 | Bolt | PERFORMANCE | SUCCESS | MERGEABLE | 0 | 0 | MERGE (zero-diff) |
| personal-config | 1876 | salvage | UI | SUCCESS | MERGEABLE | 0 | 3 | MERGE |
| personal-config | 1875 | salvage | PERFORMANCE | SUCCESS | MERGEABLE | 0 | 3 | MERGE |
| personal-config | 1873 | demo-stack | CI/INFRA | SUCCESS | MERGEABLE | 0 | 1 | MERGE (stack top) |
| personal-config | 1872 | demo-stack | CI/INFRA | SUCCESS | MERGEABLE | 0 | 1 | MERGE (stack mid) |
| personal-config | 1871 | demo-stack | CI/INFRA | SUCCESS | MERGEABLE | 0 | 1 | MERGE (stack base) |
| personal-config | 1867 | Bolt | PERFORMANCE | SUCCESS | MERGEABLE | 1 | 1 | MERGE-AFTER-FIX (inline import) |
| personal-config | 1841 | Sentinel | SECURITY | SUCCESS | MERGEABLE | 3 | — | ESCALATE |
| ctrld-sync | 1109 | Jules style | REFACTOR | SUCCESS | MERGEABLE | 0 | 9 | MERGE |
| ctrld-sync | 1107 | Palette | UI | SUCCESS | MERGEABLE | 0 | 2 | MERGE |
| email-security-pipeline | 1405 | Bolt | PERFORMANCE | SUCCESS | MERGEABLE | 0 | 2 | CLOSE after #1401 (overlap) |
| email-security-pipeline | 1404 | Jules QA | CI/INFRA | SUCCESS | MERGEABLE | 0 | 0 | MERGE (zero-diff) |
| email-security-pipeline | 1401 | salvage | PERFORMANCE | SUCCESS | MERGEABLE | 0 | 2 | MERGE (prefer) |
| Seatek_Analysis | 581 | Bolt | PERFORMANCE | SUCCESS | MERGEABLE | 0 | 2 | MERGE |
| Seatek_Analysis | 580 | Sentinel | SECURITY | SUCCESS | MERGEABLE | 0 | 2 | ESCALATE |
| Seatek_Analysis | 578 | Jules QA | CI/INFRA | SUCCESS | MERGEABLE | 0 | 0 | MERGE (zero-diff) |
| Seatek_Analysis | 576 | salvage | REFACTOR | SUCCESS | MERGEABLE | 0 | 2 | MERGE |
| Seatek_Analysis | 573 | Sentinel | SECURITY | SUCCESS | MERGEABLE | 1 | 3 | ESCALATE |
| Hydrograph… | 450 | Sentinel | SECURITY | SUCCESS* | CONFLICTING | 1 | 3 | ESCALATE/DEFER |
| Hydrograph… | 448 | Sentinel | SECURITY | SUCCESS* | CONFLICTING | 1 | 3 | ESCALATE/DEFER |
| Hydrograph… | 445 | Sentinel | SECURITY | SUCCESS* | CONFLICTING | 2 | 2 | ESCALATE/DEFER |
| series_correction… | 340 | Jules QA | CI/INFRA | SUCCESS | MERGEABLE | 0 | 0 | MERGE (zero-diff) |
| repoprompt-ce | 170 | Bolt | PERFORMANCE | FAILURE | MERGEABLE | 0 | 5 | REQUEST_CHANGES |
| repoprompt-ce | 169 | Palette | UI | FAILURE | MERGEABLE | 0 | 1 | REQUEST_CHANGES |
| repoprompt-ce | 168 | Agentic QA | CI/INFRA | FAILURE | MERGEABLE | 0 | 6 | REQUEST_CHANGES |
| repoprompt-ce | 165 | Sentinel | SECURITY | FAILURE | MERGEABLE | 0 | 7 | ESCALATE |
| repoprompt-ce | 164 | Bolt | PERFORMANCE | FAILURE | MERGEABLE | 1 | 8 | REQUEST_CHANGES |
| repoprompt-ce | 163 | Palette | UI | FAILURE | MERGEABLE | 1 | 6 | REQUEST_CHANGES |
| repoprompt-ce | 161 | Palette | UI | — | CONFLICTING | 2 | — | DEFER Phase 2 |
| repoprompt-ce | 158 | Sentinel | SECURITY | — | CONFLICTING | 2 | — | ESCALATE/DEFER |
| repoprompt-ce | 157 | salvage | PERFORMANCE | — | CONFLICTING | 2 | — | DEFER Phase 2 |
| repoprompt-ce | 152 | FSEvents | REFACTOR | — | CONFLICTING | 3 | — | DEFER Phase 2 |
| repoprompt-ce | 148 | ChatPreset | FEATURE | — | CONFLICTING | 3 | — | DEFER Phase 2 |
| repoprompt-ce | 147 | Code Health | REFACTOR | — | CONFLICTING | 3 | 56 | DEFER Phase 2 |
| repoprompt-ce | 144 | Palette | UI | — | CONFLICTING | 4 | — | DEFER Phase 2 |

\* Hydrograph rollup SUCCESS but `github-advanced-security` noise; CONFLICTING blocks merge.

**Totals:** 36 inventoried automation PRs.
# PR Inventory — Salvage Session 2026-08-02

Live re-fetch after Phase 1 remainder (`tasks/pr-review-2026-08-02.md` / [#1884](https://github.com/abhimehro/personal-config/pull/1884)).
Scope: bot/automation PRs that are CONFLICTING/DIRTY (or prior deferred/escalated still open).

## Counts (live at Phase 2 start)

| Repo | Open | CONFLICTING/DIRTY | Notes |
| ---- | ---- | ----------------- | ----- |
| personal-config | 2 | 0 | #1841 CLEAN Sentinel escalate; #1884 Phase 1 docs |
| ctrld-sync | 0 | 0 | Queue drained (yesterday #1105 merged) |
| email-security-pipeline | 0 | 0 | Queue drained (#1401 merged) |
| Seatek_Analysis | 2 | 0 | #580/#573 CLEAN Sentinel escalate |
| Hydrograph… | 3 | 3 (#445/#448/#450) | All Sentinel path cluster → CLOSE-SUPERSEDED |
| series_correction… | 0 | 0 | Queue drained |
| repoprompt-ce | 13 | 7 DIRTY + 6 UNSTABLE | Salvage #171 from #165/#158; defer drift pile |

## Salvage drafts opened this run

| New draft | Salvages | Repo |
| --------- | -------- | ---- |
| [#171](https://github.com/abhimehro/repoprompt-ce/pull/171) | #165/#158 TOCTOU-only | repoprompt-ce |

## Closed this run

| PR | Disposition |
| -- | ----------- |
| hg #445 | CLOSE-SUPERSEDED — `is_safe_path` already on `main` |
| hg #448 | CLOSE-SUPERSEDED — duplicate-check corruption; fix on `main` |
| hg #450 | CLOSE-SUPERSEDED — refactor only; security on `main` |
| rpce #158 | CLOSE-SUPERSEDED by #171 |
| Repo                    | Open | CONFLICTING/DIRTY (start)   | Notes                                          |
| ----------------------- | ---- | --------------------------- | ---------------------------------------------- |
| personal-config         | 9    | 4 (#1859/#1857/#1825/#1822) | Salvaged 1857/1859; closed 1825; escalate 1822 |
| ctrld-sync              | 3    | 1 (#1081)                   | Salvaged → #1105                               |
| email-security-pipeline | 1    | 1 (#1399) + CodeScene       | Spam-only salvage → #1401                      |
| Seatek_Analysis         | 6    | 4 (#568/#555/#560/#554)     | #554 → #576; security escalate                 |
| Hydrograph…             | 5    | 0                           | All CLEAN (Phase 1 remainder stale on #443)    |
| series_correction…      | 0    | 0                           | Queue drained                                  |
| repoprompt-ce           | 9    | 7 DIRTY + UNSTABLE CI       | Security escalate #158; defer drift pile       |

## Salvage drafts opened this run

| New draft                                                               | Salvages                   | Repo                    |
| ----------------------------------------------------------------------- | -------------------------- | ----------------------- |
| [#1875](https://github.com/abhimehro/personal-config/pull/1875)         | #1857                      | personal-config         |
| [#1876](https://github.com/abhimehro/personal-config/pull/1876)         | #1859 (empty-state only)   | personal-config         |
| [#1105](https://github.com/abhimehro/ctrld-sync/pull/1105)              | #1081                      | ctrld-sync              |
| [#1401](https://github.com/abhimehro/email-security-pipeline/pull/1401) | #1399 (spam_analyzer only) | email-security-pipeline |
| [#576](https://github.com/abhimehro/Seatek_Analysis/pull/576)           | #554                       | Seatek_Analysis         |

## Closed this run

| PR          | Disposition         |
| ----------- | ------------------- |
| pc #1857    | superseded by #1875 |
| pc #1859    | superseded by #1876 |
| pc #1825    | no-op junk          |
| ctrld #1081 | superseded by #1105 |
| esp #1399   | superseded by #1401 |
| seatek #554 | superseded by #576  |

## Still escalated / deferred (human)

- pc #1841 Sentinel timeout/auth env (CLEAN)
- seatek #580 path hijack, #573 file-read DoS (CLEAN)
- rpce #165 prefer #171; Build/Test red on original
- rpce DIRTY drift: #161/#157/#152/#148/#147/#144 (DEFER)
- rpce UNSTABLE MERGEABLE: #170/#169/#168/#164/#163 (Phase 1 REQUEST_CHANGES)
