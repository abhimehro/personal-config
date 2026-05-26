# PR Triage — 2026-05-26

**Disposition key:** MERGE · CLOSE-DUPLICATE · CLOSE-SUPERSEDED · CLOSE-DEFERRED · SALVAGE-DRAFT · DEFER-COMMENT

**Preflight:** PASS

## Phase 1 (review-and-merge)

| Repo | PR | Disposition |
| --- | ---: | --- |
| personal-config | 1068, 1070, 1072 | **MERGE** |
| series_correction | 72 | **MERGE** (CodeScene non-blocking; other checks green) |

## Phase 2 (salvage v3 rebuilds)

| Repo | Old PR | Disposition | New draft |
| --- | ---: | --- | ---: |
| email-security-pipeline | 932 | **CLOSE-SUPERSEDED** | [#939](https://github.com/abhimehro/email-security-pipeline/pull/939) |
| email-security-pipeline | 933 | **CLOSE-SUPERSEDED** | [#940](https://github.com/abhimehro/email-security-pipeline/pull/940) |
| email-security-pipeline | 937 | **CLOSE-DEFERRED** | Re-apply Black on `main` in focused chore PR |
| Seatek_Analysis | 223, 224 | **CLOSE-SUPERSEDED** | [#227](https://github.com/abhimehro/Seatek_Analysis/pull/227) |
| series_correction | 73 | **CLOSE-SUPERSEDED** | [#76](https://github.com/abhimehro/series_correction_project_updated/pull/76) |

## Human merge queue (draft salvages)

| Repo | PR | Tier | Priority |
| --- | ---: | --- | --- |
| email-security-pipeline | 939 | T1 | TOCTOU — merge first after CI green |
| email-security-pipeline | 940 | T3 | IMAP per-folder concurrency |
| Seatek_Analysis | 227 | T3 | R `testthat` for write_year_sheet + read_sensor_data |
| series_correction | 76 | T3 | Dead `load_series_data` removal |
| personal-config | 1065 | T3 | scratch_triage modularization; CodeScene may fail |

## Ready-to-execute human actions

1. After CI green, squash-merge drafts in order: **ESP #939** → **#940** → **Seatek #227** → **series #76**.
2. Review **personal-config #1065** — merge if CodeScene waiver acceptable (refactor-only).
3. No action on **ctrld-sync** until new bot PRs appear; #847 superseded by #849.

## Escalations

None new. **Lesson 0cc** applied: all v3 salvages built from `origin/main` after Phase 1 merges (#1068, #1072, series #72).
