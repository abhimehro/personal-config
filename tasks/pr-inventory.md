# PR Inventory — 2026-06-03

**Preflight:** PASS (6/6 repos)  
**Session:** Salvage cron `0 17 * * *`  
**Agent branch:** `cursor-agent/automated-pr-salvage-workflow-58fc`  
**Config:** `tasks/pr-review-agent.config.yaml`

## Scope summary (end of session)

| Repo | Open in-scope (EOD) | CONFLICTING / DIRTY (start) |
| --- | ---: | ---: |
| personal-config | 4 | 1 (#1151) |
| ctrld-sync | 0 | 0 |
| email-security-pipeline | 5 | 2 (#1022, #1024) |
| Seatek_Analysis | 2 | 2 (#247, #249) |
| Hydrograph_Versus_Seatek_Sensors_Project | 2 | 2 (#223, #224) |
| series_correction_project_updated | 0 | 0 |

## Salvage actions (this session)

| Repo | Old PR | Disposition | New PR | Notes |
| --- | ---: | --- | ---: | --- |
| Hydrograph | #223, #224 | CLOSE-SUPERSEDED | [#227](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/227) | 5 src files only; #224 had scope creep |
| Seatek_Analysis | #249 | CLOSE-SUPERSEDED | [#260](https://github.com/abhimehro/Seatek_Analysis/pull/260) | test-clean_vals.R only |
| Seatek_Analysis | #247 | CLOSE-SUPERSEDED | [#261](https://github.com/abhimehro/Seatek_Analysis/pull/261) | scanner + tests only |
| email-security-pipeline | #1024 | CLOSE-DUPLICATE | [#1023](https://github.com/abhimehro/email-security-pipeline/pull/1023) | Twin NLP eval fix (Lesson 0dd) |
| email-security-pipeline | #1022 | CLOSE-SUPERSEDED | [#1030](https://github.com/abhimehro/email-security-pipeline/pull/1030) | v3 rebuild from main |

## Open tail (human review)

| Repo | PR | State | Tier | Disposition |
| --- | ---: | --- | --- | --- |
| email-security-pipeline | [#1008](https://github.com/abhimehro/email-security-pipeline/pull/1008) | draft, UNSTABLE | T1 | MERGE when CI green (Zip Slip) |
| email-security-pipeline | [#1023](https://github.com/abhimehro/email-security-pipeline/pull/1023) | draft, CLEAN | T1 | MERGE (NLP eval FP) |
| email-security-pipeline | [#1021](https://github.com/abhimehro/email-security-pipeline/pull/1021) | draft, CLEAN | T3 | MERGE (import os) |
| email-security-pipeline | [#1030](https://github.com/abhimehro/email-security-pipeline/pull/1030) | draft, UNSTABLE | T3 | MERGE when CI green |
| email-security-pipeline | [#1006](https://github.com/abhimehro/email-security-pipeline/pull/1006) | open, UNSTABLE | CI/INFRA | MERGE-AFTER-FIX (bandit/hooks) |
| personal-config | [#1154](https://github.com/abhimehro/personal-config/pull/1154) | draft, UNSTABLE | T3 | Fix Shell Script Quality, then merge |
| personal-config | [#1155](https://github.com/abhimehro/personal-config/pull/1155), [#1160](https://github.com/abhimehro/personal-config/pull/1160) | draft, CLEAN | DOCS | Merge session artifacts |
| personal-config | [#1151](https://github.com/abhimehro/personal-config/pull/1151) | draft, DIRTY | DOCS | CLOSE after #1160 lands |
| Hydrograph | [#227](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/227) | draft, UNSTABLE | T3 | MERGE when CI green |
| Seatek_Analysis | [#260](https://github.com/abhimehro/Seatek_Analysis/pull/260), [#261](https://github.com/abhimehro/Seatek_Analysis/pull/261) | draft, UNSTABLE | T3 | MERGE when CI green |

## Full inventory table

| Repo | PR | Author | Category | Merge | CI | Draft | Title |
| --- | ---: | --- | --- | --- | --- | --- | --- |
| personal-config | 1151 | app/cursor | CI/INFRA | CONFLICTING | DIRTY | yes | docs(pr-review) 2026-06-02 |
| personal-config | 1154 | abhimehro | PERFORMANCE | MERGEABLE | UNSTABLE | yes | run_merges parallel (salvage v3) |
| personal-config | 1155 | app/cursor | CI/INFRA | MERGEABLE | CLEAN | yes | docs(pr-salvage) 2026-06-02 |
| personal-config | 1160 | app/cursor | CI/INFRA | MERGEABLE | CLEAN | yes | docs(pr-review) 2026-06-03 |
| email-security-pipeline | 1006 | abhimehro | CI/INFRA | MERGEABLE | UNSTABLE | no | workflow consolidation |
| email-security-pipeline | 1008 | abhimehro | SECURITY | MERGEABLE | UNSTABLE | yes | tarfile Zip Slip salvage |
| email-security-pipeline | 1021 | abhimehro | REFACTOR | MERGEABLE | CLEAN | yes | import os salvage |
| email-security-pipeline | 1023 | abhimehro | SECURITY | MERGEABLE | CLEAN | yes | NLP eval FP salvage |
| email-security-pipeline | 1030 | abhimehro | REFACTOR | MERGEABLE | UNSTABLE | yes | threat metrics v3 salvage |
| Hydrograph | 227 | abhimehro | PERFORMANCE | MERGEABLE | UNSTABLE | yes | Bolt perf salvage #223+#224 |
| Seatek_Analysis | 260 | abhimehro | CI/TEST | MERGEABLE | UNSTABLE | yes | clean_vals tests salvage |
| Seatek_Analysis | 261 | abhimehro | PERFORMANCE | MERGEABLE | UNSTABLE | yes | scanner perf salvage |
