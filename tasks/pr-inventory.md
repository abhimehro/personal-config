# PR Inventory — 2026-06-01

**Preflight:** PASS (6/6 repos)  
**Session:** Salvage `0 17 * * *` (cron automation)  
**Branch:** `cursor-agent/automated-pr-salvage-workflow-17fb`  
**Config:** `tasks/pr-review-agent.config.yaml`

## Scope summary (end of salvage)

| Repo | Open in-scope (EOD) | CONFLICTING / DIRTY |
| --- | ---: | ---: |
| personal-config | 4 | 0 (originals closed → draft salvages) |
| ctrld-sync | 0 | 0 |
| email-security-pipeline | 10 | 6 |
| Seatek_Analysis | 1 | 0 |
| Hydrograph_Versus_Seatek_Sensors_Project | 0 | 0 |
| series_correction_project_updated | 0 | 0 |

## Merged this session (CLEAN squash)

| Repo | PR | Category | Title |
| --- | ---: | --- | --- |
| personal-config | [#1139](https://github.com/abhimehro/personal-config/pull/1139) | SECURITY | Fix bash eval injection in smart scheduler |
| personal-config | [#1113](https://github.com/abhimehro/personal-config/pull/1113) | SECURITY | Remove unexecuted eval string from log output |
| personal-config | [#1144](https://github.com/abhimehro/personal-config/pull/1144) | CI/TEST | fix shellcheck SC2016 in test_repo_credential_hygiene |
| series_correction | [#92](https://github.com/abhimehro/series_correction_project_updated/pull/92) | SECURITY | CSV/Formula injection categorical column fix |
| series_correction | [#90](https://github.com/abhimehro/series_correction_project_updated/pull/90) | PERFORMANCE | Vectorize DataFrame creation in correct_gaps |
| Seatek_Analysis | [#238](https://github.com/abhimehro/Seatek_Analysis/pull/238) | PERFORMANCE | Optimize weekly retrospective network requests |

## Closed superseded (conflicted originals)

| Repo | Old PR | Salvage draft | Notes |
| --- | ---: | ---: | --- |
| personal-config | #1132, #1125 | [#1145](https://github.com/abhimehro/personal-config/pull/1145) | run_merges parallelization cluster |
| personal-config | #1117 | [#1147](https://github.com/abhimehro/personal-config/pull/1147) | scratch_triage parallel API |
| personal-config | #1142 | [#1146](https://github.com/abhimehro/personal-config/pull/1146) | scratch_inventory any() → or chains |
| email-security-pipeline | #999 | [#1008](https://github.com/abhimehro/email-security-pipeline/pull/1008) | T1 tarfile Zip Slip |
| Seatek_Analysis | #237 | [#239](https://github.com/abhimehro/Seatek_Analysis/pull/239) | code_health_scanner TODO perf |

## Open tail (human review)

| Repo | PR | State | Disposition |
| --- | ---: | --- | --- |
| personal-config | [#1145](https://github.com/abhimehro/personal-config/pull/1145) | draft, UNSTABLE | MERGE when CI green (T3) |
| personal-config | [#1146](https://github.com/abhimehro/personal-config/pull/1146) | draft, UNSTABLE | MERGE when CI green (T3) |
| personal-config | [#1147](https://github.com/abhimehro/personal-config/pull/1147) | draft, UNSTABLE | MERGE when CI green (T3) |
| personal-config | [#1143](https://github.com/abhimehro/personal-config/pull/1143) | draft, DIRTY | CLOSE after session artifacts land on salvage branch |
| email-security-pipeline | [#1008](https://github.com/abhimehro/email-security-pipeline/pull/1008) | draft, UNSTABLE | MERGE first (T1 security) |
| email-security-pipeline | #972–#996, #1003, #1006 | mixed | DEFER / MERGE-AFTER-FIX (see triage) |
| Seatek_Analysis | [#239](https://github.com/abhimehro/Seatek_Analysis/pull/239) | draft, UNSTABLE | MERGE when CI green (T3) |
