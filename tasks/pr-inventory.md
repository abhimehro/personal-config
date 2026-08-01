# PR Inventory — 2026-08-01

Phase 1 cron (`0 13 * * *`). Preflight **PASS 7/7**. Inventoried **39**
automation / bot-signal PRs across 7 repos (plus a few stacked human docs PRs
seen at recheck).

| Repo | PR | Author | Category | CI | Conflicts | Age | Status |
| ---- | -- | ------ | -------- | -- | --------- | --- | ------ |
| personal-config | 1822 | abhimehro | SECURITY | PASS | CONFLICTING | 2d | ESCALATE |
| personal-config | 1841 | abhimehro | SECURITY | PASS | MERGEABLE | 1d | ESCALATE |
| personal-config | 1857 | abhimehro | PERFORMANCE | FAIL | MERGEABLE | 0d | DEFER (salvage CI) |
| personal-config | 1859 | abhimehro | UI | PASS | CONFLICTING | 0d | DEFER Phase 2 |
| personal-config | 1867 | abhimehro | PERFORMANCE | FAIL | MERGEABLE | 0d | REQUEST_CHANGES |
| personal-config | 1868 | abhimehro | REFACTOR | PASS | MERGEABLE | 0d | MERGED |
| ctrld-sync | 1081 | app/cursor | CI/INFRA | FAIL | CONFLICTING | 1d | DEFER |
| ctrld-sync | 1086 | abhimehro | REFACTOR | PASS | MERGEABLE | 1d | REQUEST_CHANGES |
| ctrld-sync | 1090 | abhimehro | UI | PASS | MERGEABLE | 0d | CLOSED (twin of 1092) |
| ctrld-sync | 1091 | abhimehro | REFACTOR | PASS | MERGEABLE | 0d | MERGED |
| ctrld-sync | 1092 | abhimehro | UI | PASS | MERGEABLE | 0d | MERGED |
| email-security-pipeline | 1395 | abhimehro | CI/INFRA | PASS | MERGEABLE | 0d | MERGED |
| email-security-pipeline | 1397 | abhimehro | UI | PASS | MERGEABLE | 0d | MERGED |
| email-security-pipeline | 1398 | dependabot | DEPENDENCY | PASS | MERGEABLE | 0d | CLOSED (twin of 1395) |
| email-security-pipeline | 1399 | abhimehro | PERFORMANCE | FAIL (CodeScene) | MERGEABLE | 0d | DEFER (+cs-agent) |
| Seatek_Analysis | 555 | abhimehro | SECURITY | PASS | CONFLICTING | 2d | ESCALATE |
| Seatek_Analysis | 560 | abhimehro | PERFORMANCE | PASS | CONFLICTING | 2d | DEFER Phase 2 |
| Seatek_Analysis | 568 | abhimehro | SECURITY | PASS | CONFLICTING | 1d | ESCALATE |
| Seatek_Analysis | 571 | abhimehro | SECURITY | PASS | MERGEABLE | 0d | ESCALATE |
| Seatek_Analysis | 572 | abhimehro | CI/INFRA | PASS | MERGEABLE | 0d | MERGED (zero-diff) |
| Seatek_Analysis | 573 | abhimehro | SECURITY | PASS | MERGEABLE | 0d | ESCALATE |
| Seatek_Analysis | 574 | abhimehro | PERFORMANCE | PASS | MERGEABLE | 0d | MERGED |
| Hydrograph | 441 | dependabot | DEPENDENCY | PASS | MERGEABLE | 1d | ESCALATE (numpy floor) |
| Hydrograph | 442 | dependabot | DEPENDENCY | PASS | MERGEABLE | 1d | MERGED |
| Hydrograph | 443 | dependabot | DEPENDENCY | PASS→CONFLICT | was MERGEABLE | 1d | DEFER Phase 2 (lock after 442) |
| Hydrograph | 445 | abhimehro | SECURITY | PASS | MERGEABLE | 1d | ESCALATE |
| Hydrograph | 448 | abhimehro | SECURITY | PASS | MERGEABLE | 0d | ESCALATE |
| Hydrograph | 449 | dependabot | DEPENDENCY | PASS | MERGEABLE | 0d | MERGED |
| Hydrograph | 450 | abhimehro | SECURITY | PASS | MERGEABLE | 0d | ESCALATE |
| Hydrograph | 451 | abhimehro | PERFORMANCE | PASS | MERGEABLE | 0d | MERGED |
| series_correction | 336 | abhimehro | REFACTOR | FAIL (CodeScene) | CONFLICTING | 1d | DEFER |
| series_correction | 337 | abhimehro | PERFORMANCE | PASS | MERGEABLE | 1d | MERGED |
| series_correction | 338 | abhimehro | CI/INFRA | PASS | MERGEABLE | 0d | MERGED |
| repoprompt-ce | 144 | abhimehro | UI | PASS | CONFLICTING | 3d | DEFER Phase 2 |
| repoprompt-ce | 157 | abhimehro | PERFORMANCE | FAIL | CONFLICTING | 1d | DEFER Phase 2 |
| repoprompt-ce | 158 | abhimehro | SECURITY | FAIL | CONFLICTING | 1d | ESCALATE |
| repoprompt-ce | 161 | abhimehro | UI | PASS | CONFLICTING | 1d | DEFER Phase 2 |
| repoprompt-ce | 163 | abhimehro | UI | FAIL (Secret Scan) | MERGEABLE | 0d | REQUEST_CHANGES |
| repoprompt-ce | 164 | abhimehro | PERFORMANCE | FAIL | MERGEABLE | 0d | REQUEST_CHANGES |

Hydrograph = `Hydrograph_Versus_Seatek_Sensors_Project`;
series_correction = `series_correction_project_updated`.
