# PR Inventory — 2026-05-31

**Session:** Automated PR salvage (cron `0 17 * * *`, automation `3e537981-04a6-456f-89a3-272d9d5fddd7`)  
**Preflight:** PASS (6/6 repos)  
**Branch:** `cursor-agent/automated-pr-salvage-workflow-4f93`

## Scope summary

| Repo | Open PRs (all) | In-scope bot/automation | CONFLICTING / DIRTY |
| --- | ---: | ---: | ---: |
| personal-config | 4 | 3 | 0 |
| ctrld-sync | 1 | 1 | 0 |
| email-security-pipeline | 3 | 3 | 0 |
| Seatek_Analysis | 0 | 0 | 0 |
| Hydrograph_Versus_Seatek_Sensors_Project | 0 | 0 | 0 |
| series_correction_project_updated | 0 | 0 | 0 |
| **Total** | **8** | **7** | **0** |

**Conflict tail:** None. Prior deferred `email-security-pipeline#957` and `#956` are **MERGED** (resolved since 2026-05-29).

## In-scope PR table

| Repo | PR | Author | Branch signal | Merge state | CI rollup | Age (days) | Title |
| --- | ---: | --- | --- | --- | --- | ---: | --- |
| personal-config | [#1093](https://github.com/abhimehro/personal-config/pull/1093) | abhimehro | `jules-*` | CLEAN | Green (CodeQL/advisory) | 0 | Bolt: avoid intermediate list allocations |
| personal-config | [#1102](https://github.com/abhimehro/personal-config/pull/1102) | app/cursor | `cursor-agent/*` | CLEAN | Green | 0 | docs(pr-review): 2026-05-31 review artifacts |
| personal-config | [#1096](https://github.com/abhimehro/personal-config/pull/1096) | app/cursor | `cursor-agent/*` | CLEAN | Green | 1 | docs(pr-salvage): 2026-05-30 salvage artifacts |
| personal-config | [#1103](https://github.com/abhimehro/personal-config/pull/1103) | abhimehro | human | CLEAN | Green (full suite) | 0 | secops: harden AI engine + fix launchd PATH |
| ctrld-sync | [#861](https://github.com/abhimehro/ctrld-sync/pull/861) | abhimehro | `jules-*` | UNSTABLE | benchmark fail; app checks green | 0 | Palette: unspecified profile log presentation |
| email-security-pipeline | [#968](https://github.com/abhimehro/email-security-pipeline/pull/968) | abhimehro | `qa-fix-*` | CLEAN | Green | 0 | chore: minor formatting fixes |
| email-security-pipeline | [#970](https://github.com/abhimehro/email-security-pipeline/pull/970) | abhimehro | `jules-*` | UNSTABLE | pending Cursor Bugbot; else green | 0 | Palette: connection retry menu scannability |
| email-security-pipeline | [#966](https://github.com/abhimehro/email-security-pipeline/pull/966) | abhimehro | `automation-workflow-*` | UNSTABLE | bandit fail (SHA policy) | 0 | chore(actions): consolidate workflow automation |

## Out of scope (not bot/automation tail)

| Repo | PR | Reason excluded |
| --- | ---: | --- |
| personal-config | #1103 | Human-authored secops feature; trust-boundary escalation per review heuristics |

## Post–Phase 1 remainder (from 2026-05-29) — status

| PR | Prior disposition | Current state |
| --- | --- | --- |
| esp #957 | DEFER (bandit pins) | **MERGED** |
| esp #956 | DEFER (after #957) | **MERGED** |
