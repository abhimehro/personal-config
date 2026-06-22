# PR Inventory — 2026-06-22

**Preflight:** PASS (6/6 configured repos; repoprompt-ce checked ad hoc)\
**Phase 1:** cron `0 13 * * *` — review-and-merge (`cursor-agent/automated-pr-workflow-7912`)\
**Config:** `tasks/pr-review-agent.config.yaml`

## Scope summary

| Repo | Open at start | Merged | Closed dup/stale | Auto-fixed | Escalated | Deferred EOD | Open EOD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| personal-config | 5 | 5 | 0 | 1 | 0 | 0 | 0 |
| ctrld-sync | 3 | 2 | 1 | 0 | 0 | 0 | 0 |
| email-security-pipeline | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| Seatek_Analysis | 2 | 2 | 0 | 0 | 0 | 0 | 0 |
| Hydrograph_Versus_Seatek_Sensors_Project | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| series_correction_project_updated | 8 | 5 | 1 | 0 | 0 | 1 | 1 |
| repoprompt-ce | 6 | 0 | 2 | 0 | 0 | 4 | 4 |

**Totals:** 24 PRs inventoried · 15 squash-merges · 4 closes · 1 auto-fix merge · 0 escalate · 5 deferred

## Full inventory at session start

| Repo | PR | Author | Category | Merge | CI | Age | Disposition |
| --- | ---: | --- | --- | --- | --- | ---: | --- |
| personal-config | [#1310](https://github.com/abhimehro/personal-config/pull/1310) | abhimehro (Sentinel) | SECURITY | CLEAN | green | 0 | **MERGE** |
| personal-config | [#1311](https://github.com/abhimehro/personal-config/pull/1311) | abhimehro (salvage) | CI/INFRA | CLEAN | green | 0 | **MERGE** |
| personal-config | [#1314](https://github.com/abhimehro/personal-config/pull/1314) | abhimehro (Palette) | UI | CLEAN | green | 0 | **MERGE** |
| personal-config | [#1322](https://github.com/abhimehro/personal-config/pull/1322) | abhimehro (Bolt) | PERFORMANCE | CLEAN | Codacy infra fail | 0 | **MERGE** |
| personal-config | [#1323](https://github.com/abhimehro/personal-config/pull/1323) | abhimehro (Bolt) | PERFORMANCE | CONFLICTING→CLEAN | Codacy infra fail | 0 | **MERGE-AFTER-FIX** |
| ctrld-sync | [#935](https://github.com/abhimehro/ctrld-sync/pull/935) | abhimehro (Sentinel) | SECURITY | CLEAN | green | 0 | **MERGE** |
| ctrld-sync | [#934](https://github.com/abhimehro/ctrld-sync/pull/934) | abhimehro (Sentinel) | SECURITY | CLEAN | green | 0 | **CLOSE-DUPLICATE** |
| ctrld-sync | [#932](https://github.com/abhimehro/ctrld-sync/pull/932) | abhimehro (Palette) | UI | CLEAN | green | 0 | **MERGE** |
| email-security-pipeline | [#1138](https://github.com/abhimehro/email-security-pipeline/pull/1138) | abhimehro (Palette) | UI | CLEAN | green | 0 | **MERGE** |
| Seatek_Analysis | [#347](https://github.com/abhimehro/Seatek_Analysis/pull/347) | abhimehro (Sentinel) | SECURITY | CLEAN | green | 0 | **MERGE** |
| Seatek_Analysis | [#348](https://github.com/abhimehro/Seatek_Analysis/pull/348) | abhimehro (Bolt) | PERFORMANCE | CLEAN | green | 0 | **MERGE** |
| series_correction | [#142](https://github.com/abhimehro/series_correction_project_updated/pull/142) | abhimehro (Bolt) | PERFORMANCE | CLEAN | CodeScene fail | 0 | **DEFER** |
| series_correction | [#141](https://github.com/abhimehro/series_correction_project_updated/pull/141) | dependabot | DEPENDENCY | CLEAN | green | 0 | **MERGE** |
| series_correction | [#140](https://github.com/abhimehro/series_correction_project_updated/pull/140) | dependabot | DEPENDENCY | CLEAN | green | 0 | **MERGE** |
| series_correction | [#139](https://github.com/abhimehro/series_correction_project_updated/pull/139) | dependabot | DEPENDENCY | CLEAN | green | 0 | **MERGE** |
| series_correction | [#138](https://github.com/abhimehro/series_correction_project_updated/pull/138) | dependabot | DEPENDENCY | CLEAN | green | 0 | **MERGE** |
| series_correction | [#137](https://github.com/abhimehro/series_correction_project_updated/pull/137) | dependabot | DEPENDENCY | CLEAN | green | 0 | **MERGE** |
| series_correction | [#135](https://github.com/abhimehro/series_correction_project_updated/pull/135) | abhimehro (Bolt) | PERFORMANCE | CLEAN | CodeScene fail | 1 | **CLOSE-DUPLICATE** |
| repoprompt-ce | [#39](https://github.com/abhimehro/repoprompt-ce/pull/39) | abhimehro (Bolt) | PERFORMANCE | CLEAN | pending/snyk fail | 0 | **DEFER** |
| repoprompt-ce | [#30](https://github.com/abhimehro/repoprompt-ce/pull/30) | abhimehro (Palette) | UI | CONFLICTING | Style fail | 0 | **CLOSE-DUPLICATE** |
| repoprompt-ce | [#28](https://github.com/abhimehro/repoprompt-ce/pull/28) | abhimehro (salvage) | SECURITY | CONFLICTING | Style fail | 0 | **DEFER** |
| repoprompt-ce | [#27](https://github.com/abhimehro/repoprompt-ce/pull/27) | abhimehro (Bolt) | PERFORMANCE | CONFLICTING | Style fail | 1 | **CLOSE-DUPLICATE** |
| repoprompt-ce | [#25](https://github.com/abhimehro/repoprompt-ce/pull/25) | abhimehro (salvage) | UI | CLEAN | Style fail | 1 | **DEFER** |
| repoprompt-ce | [#24](https://github.com/abhimehro/repoprompt-ce/pull/24) | abhimehro (salvage) | CI/INFRA | CLEAN | Style fail | 1 | **DEFER** |

## Open at session end

| Repo | PR | Reason |
| --- | ---: | --- |
| series_correction | [#142](https://github.com/abhimehro/series_correction_project_updated/pull/142) | DEFER — CodeScene fail; `/cs-agent` posted |
| repoprompt-ce | [#39](https://github.com/abhimehro/repoprompt-ce/pull/39) | DEFER — snyk fail + CI pending; Changelog DateFormatter |
| repoprompt-ce | [#28](https://github.com/abhimehro/repoprompt-ce/pull/28) | DEFER — security salvage; Style + CONFLICTING |
| repoprompt-ce | [#25](https://github.com/abhimehro/repoprompt-ce/pull/25) | DEFER — a11y salvage; Style fail |
| repoprompt-ce | [#24](https://github.com/abhimehro/repoprompt-ce/pull/24) | DEFER — Linux tests salvage; Style fail |

---

*Generated by automated PR review agent — 2026-06-22T13:10Z*
