# PR Inventory — 2026-06-21

**Preflight:** PASS (6/6 configured repos; repoprompt-ce checked ad hoc)\
**Session:** cron `0 13 * * *` (review-and-merge)\
**Branch:** `cursor-agent/automated-pr-workflow-2684`\
**Config:** `tasks/pr-review-agent.config.yaml`

## Scope summary

| Repo | Open at start | Merged | Closed dup/stale | Auto-fixed | Escalated | Deferred EOD | Open EOD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| personal-config | 8 | 5 | 2 | 1 | 1 | 0 | 1 |
| ctrld-sync | 2 | 1 | 1 | 0 | 0 | 0 | 0 |
| email-security-pipeline | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| Seatek_Analysis | 2 | 1 | 1 | 0 | 0 | 0 | 0 |
| Hydrograph_Versus_Seatek_Sensors_Project | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| series_correction_project_updated | 3 | 1 | 1 | 0 | 0 | 1 | 1 |
| repoprompt-ce | 6 | 0 | 2 | 0 | 0 | 4 | 4 |

**Totals:** 22 PRs inventoried · 9 squash-merges · 7 closes · 1 auto-fix merge · 1 escalate · 5 deferred

## Full inventory at session start

| Repo | PR | Author | Category | Merge | CI | Age | Disposition |
| --- | ---: | --- | --- | --- | --- | ---: | --- |
| personal-config | [#1308](https://github.com/abhimehro/personal-config/pull/1308) | abhimehro (Bolt) | PERFORMANCE | CONFLICTING→CLEAN | green | 0 | **MERGE-AFTER-FIX** |
| personal-config | [#1307](https://github.com/abhimehro/personal-config/pull/1307) | abhimehro (Bolt) | PERFORMANCE | CLEAN | green | 0 | **MERGE** |
| personal-config | [#1304](https://github.com/abhimehro/personal-config/pull/1304) | abhimehro (automation) | CI/INFRA | CLEAN | green | 0 | **ESCALATE** |
| personal-config | [#1303](https://github.com/abhimehro/personal-config/pull/1303) | abhimehro (Palette) | UI | CLEAN | green | 0 | **MERGE** |
| personal-config | [#1301](https://github.com/abhimehro/personal-config/pull/1301) | abhimehro (Palette) | UI | CLEAN | green | 0 | **CLOSE-DUPLICATE** |
| personal-config | [#1300](https://github.com/abhimehro/personal-config/pull/1300) | app/cursor | CI/INFRA | CLEAN | green | 0 | **CLOSE-SUPERSEDED** |
| personal-config | [#1288](https://github.com/abhimehro/personal-config/pull/1288) | abhimehro (salvage) | UI | UNSTABLE | green | 1 | **MERGE** |
| personal-config | [#1287](https://github.com/abhimehro/personal-config/pull/1287) | abhimehro (salvage) | SECURITY | UNSTABLE | green | 1 | **MERGE** |
| ctrld-sync | [#930](https://github.com/abhimehro/ctrld-sync/pull/930) | abhimehro (Palette) | UI | UNSTABLE | green | 0 | **MERGE** |
| ctrld-sync | [#928](https://github.com/abhimehro/ctrld-sync/pull/928) | abhimehro (Palette) | UI | UNSTABLE | green | 0 | **CLOSE-DUPLICATE** |
| email-security-pipeline | [#1136](https://github.com/abhimehro/email-security-pipeline/pull/1136) | abhimehro (Palette) | UI | CLEAN | green | 0 | **MERGE** |
| Seatek_Analysis | [#343](https://github.com/abhimehro/Seatek_Analysis/pull/343) | abhimehro (Sentinel) | SECURITY | CLEAN | green | 0 | **MERGE** |
| Seatek_Analysis | [#342](https://github.com/abhimehro/Seatek_Analysis/pull/342) | abhimehro (QA) | CI/INFRA | CLEAN | green | 0 | **CLOSE-STALE** (zero-diff) |
| series_correction | [#135](https://github.com/abhimehro/series_correction_project_updated/pull/135) | abhimehro (Bolt) | PERFORMANCE | UNSTABLE | CodeScene fail | 0 | **DEFER** |
| series_correction | [#134](https://github.com/abhimehro/series_correction_project_updated/pull/134) | abhimehro (QA) | REFACTOR | CLEAN | green | 0 | **MERGE** |
| series_correction | [#121](https://github.com/abhimehro/series_correction_project_updated/pull/121) | abhimehro (Bolt) | PERFORMANCE | UNSTABLE | CodeScene fail | 6 | **CLOSE-DUPLICATE** |
| repoprompt-ce | [#27](https://github.com/abhimehro/repoprompt-ce/pull/27) | abhimehro (Bolt) | PERFORMANCE | UNSTABLE | Style fail | 0 | **DEFER** |
| repoprompt-ce | [#26](https://github.com/abhimehro/repoprompt-ce/pull/26) | abhimehro (Palette) | UI | UNSTABLE | Style fail | 0 | **CLOSE-DUPLICATE** |
| repoprompt-ce | [#25](https://github.com/abhimehro/repoprompt-ce/pull/25) | abhimehro (salvage) | UI | UNSTABLE | Style fail | 0 | **DEFER** |
| repoprompt-ce | [#24](https://github.com/abhimehro/repoprompt-ce/pull/24) | abhimehro (salvage) | CI/INFRA | UNSTABLE | Style fail | 0 | **DEFER** |
| repoprompt-ce | [#23](https://github.com/abhimehro/repoprompt-ce/pull/23) | abhimehro (salvage) | SECURITY | UNSTABLE | Style+test fail | 0 | **ESCALATE→SALVAGE** |
| repoprompt-ce | [#22](https://github.com/abhimehro/repoprompt-ce/pull/22) | abhimehro (Bolt) | PERFORMANCE | UNSTABLE | Style fail | 1 | **CLOSE-DUPLICATE** |

## Open at session end

| Repo | PR | Reason |
| --- | ---: | --- |
| personal-config | [#1304](https://github.com/abhimehro/personal-config/pull/1304) | ESCALATE — workflow YAML corruption + SHA→tag pin regression |
| series_correction | [#135](https://github.com/abhimehro/series_correction_project_updated/pull/135) | DEFER — CodeScene fail; `/cs-agent` posted |
| repoprompt-ce | [#23](https://github.com/abhimehro/repoprompt-ce/pull/23) | DEFER — security salvage; Style + Build fail |
| repoprompt-ce | [#24](https://github.com/abhimehro/repoprompt-ce/pull/24) | DEFER — salvage; Style fail |
| repoprompt-ce | [#25](https://github.com/abhimehro/repoprompt-ce/pull/25) | DEFER — salvage; Style fail |
| repoprompt-ce | [#27](https://github.com/abhimehro/repoprompt-ce/pull/27) | DEFER — Style + dependency-review fail |
