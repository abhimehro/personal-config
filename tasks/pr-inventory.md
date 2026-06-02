# PR Inventory — 2026-06-02

**Preflight:** PASS (6/6 repos)  
**Session:** Salvage cron `0 17 * * *`  
**Branch:** `cursor-agent/automated-pr-salvage-workflow-608e`  
**Config:** `tasks/pr-review-agent.config.yaml`

## Scope summary (end of salvage)

| Repo | Open in-scope (EOD) | CONFLICTING / DIRTY |
| --- | ---: | ---: |
| personal-config | 3 | 1 (#1151 session docs) |
| ctrld-sync | 0 | 0 |
| email-security-pipeline | 11 | 0 (originals closed → draft salvages) |
| Seatek_Analysis | 0 | 0 |
| Hydrograph_Versus_Seatek_Sensors_Project | 0 | 0 |
| series_correction_project_updated | 0 | 0 |

## Merged this session (CLEAN squash)

| Repo | PR | Category | Title |
| --- | ---: | --- | --- |
| personal-config | [#1152](https://github.com/abhimehro/personal-config/pull/1152) | SECURITY | Fix eval injection in windscribe-connect trap restore |
| personal-config | [#1150](https://github.com/abhimehro/personal-config/pull/1150) | PERFORMANCE | Tuple-based category lookup in scratch_inventory |
| email-security-pipeline | [#1013](https://github.com/abhimehro/email-security-pipeline/pull/1013) | CI/TEST | Resolve CodeScene and CodeQL CI failures (daily QA) |

## Closed superseded / duplicate

| Repo | Old PR | Replacement / reason | Notes |
| --- | ---: | --- | --- |
| personal-config | #1145 | [#1154](https://github.com/abhimehro/personal-config/pull/1154) v3 | DIRTY after main moved; run_merges rebuild |
| personal-config | #1146 | **#1150 on main** | get_category perf superseded (Lesson 0dp) |
| email-security-pipeline | #1014 | **#1013 merged** | Identical daily QA diff |
| email-security-pipeline | #1016 | **#1017** | Duplicate Palette Spinner UX |
| email-security-pipeline | #984 | [#1018](https://github.com/abhimehro/email-security-pipeline/pull/1018) | IMAP fetch tests v2 |
| email-security-pipeline | #982 | [#1019](https://github.com/abhimehro/email-security-pipeline/pull/1019) | monitoring loop test v2 |
| email-security-pipeline | #989 | [#1020](https://github.com/abhimehro/email-security-pipeline/pull/1020) | email_parser test v2 |
| email-security-pipeline | #996 | [#1021](https://github.com/abhimehro/email-security-pipeline/pull/1021) | app_runner import v2 |
| email-security-pipeline | #972 | [#1022](https://github.com/abhimehro/email-security-pipeline/pull/1022) | threat metrics refactor v2 |
| email-security-pipeline | #973 | [#1023](https://github.com/abhimehro/email-security-pipeline/pull/1023) | NLP eval false-positive v2 |

## Open tail (human review)

| Repo | PR | State | Disposition |
| --- | ---: | --- | --- |
| personal-config | [#1154](https://github.com/abhimehro/personal-config/pull/1154) | draft, UNSTABLE | MERGE when CI green (T3 run_merges) |
| personal-config | [#1153](https://github.com/abhimehro/personal-config/pull/1153) | UNSTABLE | MERGE when CI green (Palette UX) |
| personal-config | [#1151](https://github.com/abhimehro/personal-config/pull/1151) | draft, DIRTY | CLOSE after session artifacts land |
| email-security-pipeline | [#1008](https://github.com/abhimehro/email-security-pipeline/pull/1008) | UNSTABLE | MERGE first (T1 Zip Slip salvage) |
| email-security-pipeline | [#1006](https://github.com/abhimehro/email-security-pipeline/pull/1006) | UNSTABLE | MERGE-AFTER-FIX (bandit SHA pins) |
| email-security-pipeline | [#1009](https://github.com/abhimehro/email-security-pipeline/pull/1009) | UNSTABLE | MERGE-AFTER-FIX (pytest) |
| email-security-pipeline | [#992](https://github.com/abhimehro/email-security-pipeline/pull/992) | UNSTABLE | MERGE when CodeScene green |
| email-security-pipeline | [#1017](https://github.com/abhimehro/email-security-pipeline/pull/1017) | UNSTABLE | MERGE when CI green (Palette) |
| email-security-pipeline | [#1018–#1023](https://github.com/abhimehro/email-security-pipeline/pulls) | draft salvages | Human merge when CI green |

## Auto-resolved since 2026-06-01 report

| PR | State | Notes |
| --- | --- | --- |
| pc #1147 | MERGED | scratch_triage salvage landed 2026-06-02 |
| sa #239 | CLOSED | Seatek scanner salvage closed without merge |
| esp #1003 | CLOSED | Secure permissions duplicate |
