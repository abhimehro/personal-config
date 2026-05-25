# PR Triage — 2026-05-25

**Disposition key:** MERGE · CLOSE-DUPLICATE · CLOSE-SUPERSEDED · CLOSE-DEFERRED · SALVAGE-DRAFT · DEFER-COMMENT

**Preflight:** PASS

## Phase 1 (review-and-merge within salvage cron)

| Repo | PR | Disposition |
| --- | ---: | --- |
| email-security-pipeline | 917, 927, 929 | **MERGE** |
| email-security-pipeline | 907 | **CLOSE-DUPLICATE** (#905) |
| personal-config | 1052 | **MERGE** |
| email-security-pipeline | 906, 908, 913 | **CLOSE-DEFERRED** (conflicted hygiene) |

## Phase 2 (salvage)

| Repo | Old PR | Disposition | New draft |
| --- | ---: | --- | ---: |
| personal-config | 1048 / 1051 | **CLOSE-SUPERSEDED** | [#1065](https://github.com/abhimehro/personal-config/pull/1065) |
| email-security-pipeline | 919 | **CLOSE-SUPERSEDED** | [#932](https://github.com/abhimehro/email-security-pipeline/pull/932) |
| email-security-pipeline | 921 | **CLOSE-SUPERSEDED** | [#933](https://github.com/abhimehro/email-security-pipeline/pull/933) |
| email-security-pipeline | 930, 931 | **CLOSE-SUPERSEDED** | v2 rebuild → #932, #933 |
| ctrld-sync | 846 | **CLOSE-SUPERSEDED** | [#847](https://github.com/abhimehro/ctrld-sync/pull/847) |
| series_correction | 66, 68 | **CLOSE-SUPERSEDED** | [#72](https://github.com/abhimehro/series_correction_project_updated/pull/72), [#73](https://github.com/abhimehro/series_correction_project_updated/pull/73) |
| Seatek_Analysis | 218, 219 | **CLOSE-SUPERSEDED** | [#223](https://github.com/abhimehro/Seatek_Analysis/pull/223), [#224](https://github.com/abhimehro/Seatek_Analysis/pull/224) |
| Seatek_Analysis | 209–214 | **DEFER-COMMENT** | Next cron / manual salvage |

## Human merge queue (draft salvages — do not auto-merge)

| Repo | PR | Tier | Priority |
| --- | ---: | --- | --- |
| email-security-pipeline | 932 | T1 | Security TOCTOU |
| email-security-pipeline | 933 | T3 | IMAP concurrency |
| personal-config | 1065 | T3 | scratch_triage (CodeScene may fail) |
| ctrld-sync | 847 | T3 | Confirm benchmark before merge |
| series_correction | 72, 73 | T3 | Run `scripts/tests/` |
| Seatek_Analysis | 223, 224 | T3 | R `testthat` suite |

## Ready-to-execute human actions

1. After CI green, squash-merge draft salvages in order: **ESP #932** → **#933** → **series #72/#73** → **Seatek #223/#224** → **pc #1065** → **ctrld #847** (benchmark last).
2. Salvage or close **ESP #905** (still CONFLICTING) on next cycle.
3. Batch-salvage **Seatek #209–#214** perf/refactor cluster or close as stale if intent already on `main`.
4. Merge or close **personal-config #1064** session-doc draft after reviewing diff.

## Escalations

None new. Trust-boundary note: do **not** bundle `parse_inventory.py` / `gh_token_env` into #1052 follow-up — separate human PR per 2026-05-24 policy.
