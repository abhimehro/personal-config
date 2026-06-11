# PR Triage — 2026-06-11

## Disposition summary

| Disposition | Count | Notes |
| --- | ---: | --- |
| MERGE (squash) | 31 | CI green, security-first ordering |
| CLOSE | 1 | Zero-value Palette halt (#105) |
| ESCALATE | 6 | Trust-boundary / workflow / parse_inventory / automation_tasks |
| DEFER (CI fail) | 4 | benchmark (ctrld-sync), CodeScene (ESP) |
| DEFER (conflict) | 10 | `update-branch` returned 422 after sibling merges |
| DEFER (draft) | 1 | #1205 salvage session doc draft |

## Escalated (human review required)

| Repo | PR | Reason |
| --- | ---: | --- |
| personal-config | [#1201](https://github.com/abhimehro/personal-config/pull/1201) | Workflow consolidation — `refactoring-agent.yml` trust boundary |
| personal-config | [#1210](https://github.com/abhimehro/personal-config/pull/1210) | `parse_inventory` test surface — agent toolchain boundary |
| Seatek_Analysis | [#273](https://github.com/abhimehro/Seatek_Analysis/pull/273) | 9 workflow files — consolidation trust boundary |
| Seatek_Analysis | [#277](https://github.com/abhimehro/Seatek_Analysis/pull/277) | Touches `repository_automation_tasks.py` |
| Seatek_Analysis | [#278](https://github.com/abhimehro/Seatek_Analysis/pull/278) | Touches `repository_automation_tasks.py` |
| email-security-pipeline | [#1066](https://github.com/abhimehro/email-security-pipeline/pull/1066) | Workflow consolidation |

## Deferred — failing CI (do not merge)

| Repo | PR | Failing check |
| --- | ---: | --- |
| ctrld-sync | [#881](https://github.com/abhimehro/ctrld-sync/pull/881) | `benchmark` |
| ctrld-sync | [#882](https://github.com/abhimehro/ctrld-sync/pull/882) | `benchmark` |
| email-security-pipeline | [#1071](https://github.com/abhimehro/email-security-pipeline/pull/1071) | CodeScene Code Health Review |
| email-security-pipeline | [#1075](https://github.com/abhimehro/email-security-pipeline/pull/1075) | CodeScene Code Health Review |

## Deferred — merge conflicts (Phase 2 Salvage)

| Repo | PR | Notes |
| --- | ---: | --- |
| Seatek_Analysis | [#283](https://github.com/abhimehro/Seatek_Analysis/pull/283) | SECURITY shell=False — conflict after #293 merge |
| Seatek_Analysis | [#276](https://github.com/abhimehro/Seatek_Analysis/pull/276) | Test file overlap |
| Seatek_Analysis | [#282](https://github.com/abhimehro/Seatek_Analysis/pull/282) | R analysis overlap |
| Seatek_Analysis | [#284](https://github.com/abhimehro/Seatek_Analysis/pull/284) | Test overlap |
| Seatek_Analysis | [#286](https://github.com/abhimehro/Seatek_Analysis/pull/286) | Test overlap |
| Seatek_Analysis | [#291](https://github.com/abhimehro/Seatek_Analysis/pull/291) | Test overlap |
| Seatek_Analysis | [#261](https://github.com/abhimehro/Seatek_Analysis/pull/261) | Salvage draft — workflow YAML + CONFLICTING |
| personal-config | [#1211](https://github.com/abhimehro/personal-config/pull/1211) | detect_duplicates cluster |
| personal-config | [#1215](https://github.com/abhimehro/personal-config/pull/1215) | categorize_ready refactor |
| series_correction_project_updated | [#109](https://github.com/abhimehro/series_correction_project_updated/pull/109) | test_processor overlap |
| Hydrograph_Versus_Seatek_Sensors_Project | [#245](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/245) | test_app overlap |

## Closed

| Repo | PR | Reason |
| --- | ---: | --- |
| series_correction_project_updated | [#105](https://github.com/abhimehro/series_correction_project_updated/pull/105) | Zero-diff Palette halt — no actionable changes |

## Duplicate / overlap notes

- **ESP file cluster:** Merged lint/tests (#1078–#1074) before Palette (#1068) and Bolt perf (#1076); daily QA zero-diff (#1079) merged first.
- **Seatek security wave:** #293 and #290 merged before #283; #283 now conflicts — salvage must rebase security fix onto updated `code_health_scanner.py`.
- **personal-config script cluster:** #1212 lint merged before detect_duplicates tests (#1207, #1208, #1213); #1211/#1215 now conflict on shared modules.
- **Workflow consolidation triplet:** #1201, #273, #1066 are parallel automation-workflow-updates branches — consolidate manually, do not auto-merge.

## Stale threshold (30 days)

No PRs exceeded the 30-day stale threshold this session. Oldest open: Seatek #261 at 7 days.
