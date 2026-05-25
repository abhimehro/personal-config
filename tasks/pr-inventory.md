# PR Inventory — 2026-05-25

**Trigger:** Cron `0 17 * * *` (automation `3e537981-04a6-456f-89a3-272d9d5fddd7`)  
**Branch:** `cursor-agent/pr-salvage-workflow-bec5`  
**Mode:** Phase 2 salvage + selective Phase 1 merges  
**Preflight:** PASS (6/6 repos)  
**Config:** `tasks/pr-review-agent.config.yaml`

## Summary

| Metric | Count |
| --- | ---: |
| Repos processed | 6 |
| In-scope open at start | 28 |
| Squash-merged (Phase 1) | 4 |
| Closed (duplicate / superseded / deferred comment) | 14 |
| New salvage drafts opened | 9 |
| Open tail (human merge queue) | 15 |

## Phase 1 merges (CLEAN + green required checks)

| Repo | PR | Title (short) |
| --- | ---: | --- |
| email-security-pipeline | [#917](https://github.com/abhimehro/email-security-pipeline/pull/917) | Refactor `replace_secret` → lambda |
| email-security-pipeline | [#927](https://github.com/abhimehro/email-security-pipeline/pull/927) | Jules daily QA notes |
| email-security-pipeline | [#929](https://github.com/abhimehro/email-security-pipeline/pull/929) | Palette setup wizard colors |
| personal-config | [#1052](https://github.com/abhimehro/personal-config/pull/1052) | PAT rotation runbook (salvages #1039) |

**Note:** [#1050](https://github.com/abhimehro/personal-config/pull/1050) was already merged before this run.

## Closures (no merge)

| Repo | PR | Reason |
| --- | ---: | --- |
| email-security-pipeline | 907 | Duplicate of #905 |
| email-security-pipeline | 906, 908, 913 | Conflicted; deferred to next salvage cycle |
| email-security-pipeline | 919, 921 | Superseded by salvage drafts (v2: #932, #933) |
| personal-config | 1051 | Superseded by [#1065](https://github.com/abhimehro/personal-config/pull/1065) |
| ctrld-sync | 846 | Superseded by [#847](https://github.com/abhimehro/ctrld-sync/pull/847) |
| series_correction | 66, 68 | Superseded by [#72](https://github.com/abhimehro/series_correction_project_updated/pull/72), [#73](https://github.com/abhimehro/series_correction_project_updated/pull/73) |
| Seatek_Analysis | 218, 219 | Superseded by [#223](https://github.com/abhimehro/Seatek_Analysis/pull/223), [#224](https://github.com/abhimehro/Seatek_Analysis/pull/224) |
| email-security-pipeline | 930, 931 | Closed after immediate DIRTY; replaced by #932, #933 |

## New salvage drafts (Phase 2)

| Repo | Draft PR | Salvages | Tier |
| --- | ---: | ---: | --- |
| personal-config | [#1065](https://github.com/abhimehro/personal-config/pull/1065) | #1048 | T3 |
| email-security-pipeline | [#932](https://github.com/abhimehro/email-security-pipeline/pull/932) | #919 | T1 |
| email-security-pipeline | [#933](https://github.com/abhimehro/email-security-pipeline/pull/933) | #921 | T3 |
| ctrld-sync | [#847](https://github.com/abhimehro/ctrld-sync/pull/847) | #846 | T3 |
| series_correction | [#72](https://github.com/abhimehro/series_correction_project_updated/pull/72) | #66 | T3 |
| series_correction | [#73](https://github.com/abhimehro/series_correction_project_updated/pull/73) | #68 | T3 |
| Seatek_Analysis | [#223](https://github.com/abhimehro/Seatek_Analysis/pull/223) | #218 | T3 |
| Seatek_Analysis | [#224](https://github.com/abhimehro/Seatek_Analysis/pull/224) | #219 | T3 |

## Open at end of run

| Repo | PR | Merge | Draft | Notes |
| --- | ---: | --- | --- | --- |
| personal-config | 1064 | CLEAN | yes | Cursor session docs (prior review cron) |
| personal-config | 1065 | UNSTABLE | yes | scratch_triage v2 |
| email-security-pipeline | 905 | CONFLICTING | no | Metrics reset — next cycle |
| email-security-pipeline | 932, 933 | pending CI | yes | Security + IMAP perf v2 |
| ctrld-sync | 847 | UNSTABLE | yes | Watch benchmark check |
| Seatek_Analysis | 209–214 | CONFLICTING | no | Commented defer; perf queue |
| Seatek_Analysis | 223, 224 | UNSTABLE | yes | Test salvages |
| series_correction | 72, 73 | UNSTABLE | yes | Perf + dead-code |
| Hydrograph | — | — | — | Zero open bot PRs |

**Legend:** Merge = `mergeStateStatus`; CI = poll `gh pr checks` before human merge.

## Repos with no in-scope automation PRs at start

- `abhimehro/Hydrograph_Versus_Seatek_Sensors_Project` — empty queue (unchanged).
