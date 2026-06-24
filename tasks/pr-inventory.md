# PR Inventory — 2026-06-24

**Preflight:** PASS (6/6 configured repos; repoprompt-ce checked ad hoc)\
**Phase 1:** cron `0 13 * * *` — review-and-merge (`cursor-agent/automated-pr-workflow-9b39`)\
**Config:** `tasks/pr-review-agent.config.yaml`

## Scope summary

| Repo | Open at start | Merged | Closed dup/stale | Auto-fixed | Escalated | Deferred EOD | Open EOD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| personal-config | 11 | 0 | 1 | 0 | 1 | 9 | 10 |
| ctrld-sync | 9 | 2 | 2 | 1 | 0 | 5 | 5 |
| email-security-pipeline | 4 | 1 | 1 | 0 | 0 | 2 | 2 |
| Seatek_Analysis | 2 | 0 | 1 | 0 | 0 | 1 | 1 |
| Hydrograph_Versus_Seatek_Sensors_Project | 3 | 1 | 1 | 0 | 0 | 1 | 1 |
| series_correction_project_updated | 5 | 2 | 2 | 0 | 0 | 1 | 1 |
| repoprompt-ce | 12 | 0 | 0 | 0 | 1 | 11 | 12 |

**Totals:** 45 in-scope PRs inventoried · 6 squash-merges · 8 closes · 1 auto-fix merge · 2 escalate clusters · 31 deferred/blocked EOD

## Full inventory at session start

| Repo | PR | Author | Category | CI | Age | Disposition |
| --- | ---: | --- | --- | --- | ---: | --- |
| Hydrograph | [#295](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/295) | abhimehro (Sentinel) | SECURITY | green | 1 | **MERGE** |
| Hydrograph | [#293](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/293) | app/cursor | CI/INFRA | green | 1 | **CLOSE-SUPERSEDED** (by #295) |
| Hydrograph | [#292](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/292) | app/dependabot | DEPENDENCY | fail | 1 | **DEFER** (submit-pypi) |
| series_correction | [#150](https://github.com/abhimehro/series_correction_project_updated/pull/150) | abhimehro (Bolt) | PERFORMANCE | green | 0 | **MERGE** |
| series_correction | [#146](https://github.com/abhimehro/series_correction_project_updated/pull/146) | abhimehro (Sentinel) | SECURITY | green | 1 | **MERGE** |
| series_correction | [#149](https://github.com/abhimehro/series_correction_project_updated/pull/149) | app/dependabot | DEPENDENCY | pending | 0 | **DEFER** (CodeQL) |
| series_correction | [#148](https://github.com/abhimehro/series_correction_project_updated/pull/148) | abhimehro (QA) | CI/INFRA | green | 1 | **CLOSE-STALE** (zero-diff) |
| series_correction | [#144](https://github.com/abhimehro/series_correction_project_updated/pull/144) | abhimehro (QA) | REFACTOR | green | 2 | **CLOSE-STALE** (zero-diff) |
| ctrld-sync | [#947](https://github.com/abhimehro/ctrld-sync/pull/947) | abhimehro (Bolt) | PERFORMANCE | green→CONFLICT | 0 | **MERGE-AFTER-FIX** |
| ctrld-sync | [#946](https://github.com/abhimehro/ctrld-sync/pull/946) | abhimehro (Bolt) | PERFORMANCE | CodeScene fail | 1 | **CLOSE-DUPLICATE** |
| ctrld-sync | [#944](https://github.com/abhimehro/ctrld-sync/pull/944) | app/cursor | REFACTOR | mypy fail | 1 | **CLOSE-SUPERSEDED** (by #943) |
| ctrld-sync | [#943](https://github.com/abhimehro/ctrld-sync/pull/943) | abhimehro (QA) | REFACTOR | green | 2 | **MERGE** |
| ctrld-sync | [#938–942](https://github.com/abhimehro/ctrld-sync/pulls) | app/dependabot | DEPENDENCY | mypy/ruff fail | 2 | **DEFER** (rebase requested) |
| email-security-pipeline | [#1144](https://github.com/abhimehro/email-security-pipeline/pull/1144) | abhimehro (Palette) | UI | green | 1 | **MERGE** |
| email-security-pipeline | [#1148](https://github.com/abhimehro/email-security-pipeline/pull/1148) | abhimehro (QA) | CI/INFRA | green | 0 | **CLOSE-STALE** (zero-diff) |
| email-security-pipeline | [#1146–1147](https://github.com/abhimehro/email-security-pipeline/pulls) | app/dependabot | DEPENDENCY | pending | 1 | **DEFER** |
| Seatek_Analysis | [#362](https://github.com/abhimehro/Seatek_Analysis/pull/362) | abhimehro (QA) | CI/INFRA | green | 1 | **CLOSE-STALE** (zero-diff) |
| Seatek_Analysis | [#360](https://github.com/abhimehro/Seatek_Analysis/pull/360) | app/dependabot | DEPENDENCY | pending | 1 | **DEFER** |
| personal-config | [#1340](https://github.com/abhimehro/personal-config/pull/1340) | abhimehro (Palette) | UI | Codacy fail | 1 | **DEFER** |
| personal-config | [#1326](https://github.com/abhimehro/personal-config/pull/1326) | abhimehro (Palette) | UI | Codacy fail | 2 | **CLOSE-DUPLICATE** |
| personal-config | [#1334–1339](https://github.com/abhimehro/personal-config/pulls) | abhimehro / app/cursor | CI/INFRA / PERF | Codacy fail | 1 | **DEFER** |
| personal-config | [#1330–1343](https://github.com/abhimehro/personal-config/pulls) | app/dependabot | DEPENDENCY | Codacy fail | 1 | **DEFER** |
| repoprompt-ce | [#41](https://github.com/abhimehro/repoprompt-ce/pull/41) | abhimehro (salvage) | SECURITY | Style+build fail | 2 | **ESCALATE→SALVAGE** |
| repoprompt-ce | [#24–52](https://github.com/abhimehro/repoprompt-ce/pulls) | abhimehro / app/dependabot | mixed | Style/Codacy fail | 1–4 | **DEFER** (Style cluster) |

## Open at session end

| Repo | Open | Primary blockers |
| --- | ---: | --- |
| personal-config | 10 | Codacy Security Scan (infra; all open PRs) |
| ctrld-sync | 5 | Dependabot mypy/ruff on stale branches (rebase triggered) |
| email-security-pipeline | 2 | Dependabot CodeQL pending |
| Seatek_Analysis | 1 | Dependabot CodeQL pending |
| Hydrograph_Versus_Seatek_Sensors_Project | 1 | Dependabot submit-pypi fail |
| series_correction_project_updated | 1 | Dependabot CodeQL pending |
| repoprompt-ce | 12 | Style + Codacy + snyk cluster |
