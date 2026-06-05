# PR Inventory — 2026-06-05

**Preflight:** PASS (6/6 repos)  
**Session:** Review cron `0 13 * * *`  
**Branch:** `cursor-agent/automated-pr-workflow-d2f3`  
**Config:** `tasks/pr-review-agent.config.yaml`  
**Mode:** review-and-merge

## Scope summary

| Repo | Open in-scope | Notes |
| --- | ---: | --- |
| personal-config | 7 | Jules + Cursor session docs + salvage drafts |
| ctrld-sync | 0 | — |
| email-security-pipeline | 6 | Salvage tail + health-check fix |
| Seatek_Analysis | 2 | Sentinel security + perf salvage draft |
| Hydrograph_Versus_Seatek_Sensors_Project | 1 | Bolt perf salvage draft |
| series_correction_project_updated | 0 | — |

**Total in-scope:** 16 PRs (none stale >30d)

## Full inventory

| Repo | PR | Author | Branch pattern | Category | CI | Conflicts | Age (d) | Status |
| --- | ---: | --- | --- | --- | --- | --- | ---: | --- |
| personal-config | [#1169](https://github.com/abhimehro/personal-config/pull/1169) | abhimehro | `jules-*` | PERFORMANCE | green | CLEAN | 0 | OPEN |
| personal-config | [#1166](https://github.com/abhimehro/personal-config/pull/1166) | abhimehro | `jules-*` | SECURITY | green | CLEAN | 1 | OPEN |
| personal-config | [#1165](https://github.com/abhimehro/personal-config/pull/1165) | abhimehro | `jules-*` | UI | green | **DIRTY** | 1 | OPEN |
| personal-config | [#1164](https://github.com/abhimehro/personal-config/pull/1164) | app/cursor | `cursor-agent/automated-pr-salvage-*` | CI/INFRA | green | CLEAN | 1 | draft |
| personal-config | [#1161](https://github.com/abhimehro/personal-config/pull/1161) | app/cursor | `cursor-agent/automated-pr-salvage-*` | CI/INFRA | green | CLEAN | 2 | draft |
| personal-config | [#1160](https://github.com/abhimehro/personal-config/pull/1160) | app/cursor | `cursor-agent/automated-pr-workflow-*` | CI/INFRA | green | CLEAN | 2 | draft |
| personal-config | [#1154](https://github.com/abhimehro/personal-config/pull/1154) | abhimehro | `cursor-agent/salvage-*` | PERFORMANCE | **fail** Shellcheck | UNSTABLE | 3 | draft |
| email-security-pipeline | [#1034](https://github.com/abhimehro/email-security-pipeline/pull/1034) | abhimehro | `cursor-agent/repository-health-check-*` | SECURITY | green | CLEAN | 0 | OPEN |
| email-security-pipeline | [#1030](https://github.com/abhimehro/email-security-pipeline/pull/1030) | abhimehro | `cursor-agent/salvage-*` | REFACTOR | **fail** pytest | UNKNOWN | 2 | OPEN |
| email-security-pipeline | [#1023](https://github.com/abhimehro/email-security-pipeline/pull/1023) | abhimehro | `cursor-agent/salvage-*` | SECURITY | green | UNKNOWN | 3 | draft |
| email-security-pipeline | [#1021](https://github.com/abhimehro/email-security-pipeline/pull/1021) | abhimehro | `cursor-agent/salvage-*` | REFACTOR | green | UNKNOWN | 3 | draft |
| email-security-pipeline | [#1008](https://github.com/abhimehro/email-security-pipeline/pull/1008) | abhimehro | `cursor-agent/salvage-*` | SECURITY | **fail** CodeScene | UNKNOWN | 4 | draft |
| email-security-pipeline | [#1006](https://github.com/abhimehro/email-security-pipeline/pull/1006) | abhimehro | `automation-workflow-*` | CI/INFRA | **fail** bandit | UNKNOWN | 4 | OPEN |
| Seatek_Analysis | [#263](https://github.com/abhimehro/Seatek_Analysis/pull/263) | abhimehro | `security-fix-*` | SECURITY | green | CLEAN | 1 | OPEN |
| Seatek_Analysis | [#261](https://github.com/abhimehro/Seatek_Analysis/pull/261) | abhimehro | `cursor-agent/salvage-*` | PERFORMANCE | **fail** CodeScene | UNKNOWN | 2 | draft |
| Hydrograph_Versus_Seatek_Sensors_Project | [#227](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/227) | abhimehro | `cursor-agent/salvage-*` | PERFORMANCE | **fail** CodeScene | UNSTABLE | 2 | draft |

## Merged this session

| Repo | PR | Category | Title |
| --- | ---: | --- | --- |
| personal-config | [#1166](https://github.com/abhimehro/personal-config/pull/1166) | SECURITY | Fix command injection in `spinner_wait` (subshell traps) |
| email-security-pipeline | [#1034](https://github.com/abhimehro/email-security-pipeline/pull/1034) | SECURITY | Restore `_set_secure_permissions` on config fd |
