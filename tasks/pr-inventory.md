# PR Inventory — 2026-05-24 (cron `0 13 * * *`)

**Preflight:** PASS (`scripts/preflight-gh-pr-automation.sh --config tasks/pr-review-agent.config.yaml`, 6/6 repos)

**Mode:** `review-and-merge` | **Stale threshold:** 30 days | **Merge strategy:** squash

## Summary

| Repo | In-scope open | Notes |
| --- | ---: | --- |
| abhimehro/personal-config | 13 → 4 (end of session) | Security remediation burst (CWE-94 / ABHI-9xx) |
| abhimehro/email-security-pipeline | 1 → 0 | Jules Daily QA import removal |
| abhimehro/ctrld-sync | 0 | — |
| abhimehro/Seatek_Analysis | 0 | — |
| abhimehro/Hydrograph_Versus_Seatek_Sensors_Project | 0 | — |
| abhimehro/series_correction_project_updated | 0 | — |

## Full inventory (session start)

| Repo | PR | Author | Branch | Category | CI | Conflicts | Age | Session end |
| --- | ---: | --- | --- | --- | --- | --- | --- | --- |
| personal-config | [#1048](https://github.com/abhimehro/personal-config/pull/1048) | abhimehro (Jules) | `jules-*` | CI/INFRA | CodeScene **fail** | — | 0d | **OPEN** |
| personal-config | [#1047](https://github.com/abhimehro/personal-config/pull/1047) | abhimehro (cursor) | `cursor-agent/abh-918-*` | SECURITY | CLEAN | — | 0d | **ESCALATE** |
| personal-config | [#1046](https://github.com/abhimehro/personal-config/pull/1046) | abhimehro (cursor) | `cursor-agent/verify-no-hardcoded-*` | SECURITY | CLEAN | resolved | 0d | **MERGED** |
| personal-config | [#1045](https://github.com/abhimehro/personal-config/pull/1045) | abhimehro (cursor) | `cursor-agent/abhi-943-*` | SECURITY | CLEAN | — | 0d | **MERGED** |
| personal-config | [#1044](https://github.com/abhimehro/personal-config/pull/1044) | abhimehro (cursor) | `cursor-agent/abhi-929-*` | SECURITY | CodeScene fail | — | 0d | **CLOSED** dup #1045 |
| personal-config | [#1043](https://github.com/abhimehro/personal-config/pull/1043) | abhimehro (cursor) | `cursor-agent/fix-copilot-*` | SECURITY | CLEAN | — | 0d | **CLOSED** superseded |
| personal-config | [#1042](https://github.com/abhimehro/personal-config/pull/1042) | abhimehro (cursor) | `cursor-agent/verify-summary-*` | SECURITY | CodeScene fail | — | 0d | **CLOSED** dup #1037 |
| personal-config | [#1041](https://github.com/abhimehro/personal-config/pull/1041) | abhimehro (cursor) | `cursor-agent/rotate-webdav-*` | SECURITY | CLEAN | resolved | 0d | **MERGED** |
| personal-config | [#1040](https://github.com/abhimehro/personal-config/pull/1040) | abhimehro (cursor) | `cursor-agent/abhi-967-*` | SECURITY | CLEAN | resolved | 0d | **MERGED** |
| personal-config | [#1039](https://github.com/abhimehro/personal-config/pull/1039) | abhimehro (cursor) | `cursor-agent/github-pat-*` | SECURITY | tests+CodeScene fail | — | 0d | **ESCALATE** |
| personal-config | [#1038](https://github.com/abhimehro/personal-config/pull/1038) | abhimehro (cursor) | `cursor-agent/test-cwe94-*` | SECURITY | fixed+merged | resolved | 0d | **MERGED** |
| personal-config | [#1037](https://github.com/abhimehro/personal-config/pull/1037) | abhimehro (cursor) | `cursor-agent/fix-copilot-setup-*` | SECURITY | CLEAN | — | 0d | **MERGED** |
| personal-config | [#1036](https://github.com/abhimehro/personal-config/pull/1036) | abhimehro (cursor) | `cursor-agent/security-remediation-tracker-*` | SECURITY | CLEAN | DIRTY post-wave | 0d | **DEFER** |
| email-security-pipeline | [#901](https://github.com/abhimehro/email-security-pipeline/pull/901) | abhimehro (Jules) | `fix/remove-unused-import-*` | REFACTOR | all green | — | 0d | **MERGED** |

## Automation signals

All `abhimehro`-authored rows are in scope via `cursor-agent/*`, `jules-*`, or Jules task links in the PR body.
