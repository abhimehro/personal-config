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
