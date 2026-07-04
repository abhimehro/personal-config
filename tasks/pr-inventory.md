# PR Inventory — 2026-07-04

**Session:** Automated PR salvage & cleanup (cron 17:00 UTC)  
**Branch:** `cursor-agent/pr-salvage-and-cleanup-5069`  
**Preflight:** PASS 6/6 configured repos + repoprompt-ce read access  
**Mode:** Phase 1 review-and-merge + Phase 2 salvage  
**Stale threshold:** 30 days

## Summary

| Repo | Open at start | Merged | Closed | Salvage drafts | Remainder |
|------|---------------|--------|--------|----------------|-----------|
| personal-config | 16 | 12 | 3 | 1 | 5 |
| ctrld-sync | 0 | 0 | 0 | 0 | **0** |
| email-security-pipeline | 11 | 7 | 0 | 0 | 4 |
| Seatek_Analysis | 12 | 11 | 0 | 0 | 1 |
| Hydrograph_Versus_Seatek_Sensors_Project | 0 | 0 | 0 | 0 | **0** |
| series_correction_project_updated | 21 | 12 | 1 | 1 | 9 |
| repoprompt-ce | 0 | 0 | 0 | 0 | **0** |
| **Total** | **60** | **42** | **4** | **2** | **19** |

## Starting inventory (60 in-scope open)

All open PRs were Jules / Code Health / Bolt / Palette / Sentinel automation branches (human author `abhimehro`, bot branch signals). Zero `DIRTY` at session start; merge cascade produced 10 `DIRTY` tails mid-session.

## Merged this session (42 squash)

### personal-config (12)

| PR | Title |
|----|-------|
| [#1494](https://github.com/abhimehro/personal-config/pull/1494) | Remove unused `missing_gh_token_message` |
| [#1493](https://github.com/abhimehro/personal-config/pull/1493) | Remove unused calendar focus logic |
| [#1492](https://github.com/abhimehro/personal-config/pull/1492) | Optimize AdGuard import test file reading |
| [#1491](https://github.com/abhimehro/personal-config/pull/1491) | Tests for pr-review-agent config loader |
| [#1489](https://github.com/abhimehro/personal-config/pull/1489) | Optimize alldebrid selection script memory |
| [#1487](https://github.com/abhimehro/personal-config/pull/1487) | Tests for `_write_triage_report` |
| [#1486](https://github.com/abhimehro/personal-config/pull/1486) | Test for `rewrite_triage_file` |
| [#1484](https://github.com/abhimehro/personal-config/pull/1484) | Export `escape_spreadsheet_formula` |
| [#1482](https://github.com/abhimehro/personal-config/pull/1482) | Remove unused `clear_gh_token_cache` |

### email-security-pipeline (7)

| PR | Title |
|----|-------|
| [#1225](https://github.com/abhimehro/email-security-pipeline/pull/1225) | Palette CLI UX improvements |
| [#1224](https://github.com/abhimehro/email-security-pipeline/pull/1224) | Refactor `generate_threat_report` complexity |
| [#1221](https://github.com/abhimehro/email-security-pipeline/pull/1221) | Extract mock email creation in tests |
| [#1220](https://github.com/abhimehro/email-security-pipeline/pull/1220) | Refactor NLP `analyze` complexity |
| [#1218](https://github.com/abhimehro/email-security-pipeline/pull/1218) | Refactor `test_diagnostics_script` |
| [#1217](https://github.com/abhimehro/email-security-pipeline/pull/1217) | Refactor `_inspect_tar_contents` |
| [#1216](https://github.com/abhimehro/email-security-pipeline/pull/1216) | Refactor `_console_clean_report` |

### Seatek_Analysis (11)

| PR | Title |
|----|-------|
| [#415](https://github.com/abhimehro/Seatek_Analysis/pull/415) | Equivalence tests sapply vs lapply |
| [#414](https://github.com/abhimehro/Seatek_Analysis/pull/414) | Tests for `export_main_summary` |
| [#413](https://github.com/abhimehro/Seatek_Analysis/pull/413) | Bolt parallelize I/O shell commands |
| [#412](https://github.com/abhimehro/Seatek_Analysis/pull/412) | Security: credential exfiltration allowlist |
| [#411](https://github.com/abhimehro/Seatek_Analysis/pull/411) | Optimize `get_language` |
| [#410](https://github.com/abhimehro/Seatek_Analysis/pull/410) | Bolt Data.Table value extraction |
| [#409](https://github.com/abhimehro/Seatek_Analysis/pull/409) | Extract validation from `read_sensor_data` |
| [#408](https://github.com/abhimehro/Seatek_Analysis/pull/408) | Tests for `configured_commands` |
| [#406](https://github.com/abhimehro/Seatek_Analysis/pull/406) | Tests for `configured_commands` |
| [#404](https://github.com/abhimehro/Seatek_Analysis/pull/404) | Tests for `repository_automation.py` main |

### series_correction_project_updated (12)

| PR | Title |
|----|-------|
| [#191](https://github.com/abhimehro/series_correction_project_updated/pull/191) | Sentinel MEDIUM raw exception exposure |
| [#194](https://github.com/abhimehro/series_correction_project_updated/pull/194) | Bolt cache `listdir` |
| [#193](https://github.com/abhimehro/series_correction_project_updated/pull/193) | Multi-root workspace payload roots |
| [#192](https://github.com/abhimehro/series_correction_project_updated/pull/192) | Test batch_correction config FileNotFoundError |
| [#190](https://github.com/abhimehro/series_correction_project_updated/pull/190) | Tests for `correct_jumps` |
| [#188](https://github.com/abhimehro/series_correction_project_updated/pull/188) | Refactor `export_comparisons` loop |
| [#185](https://github.com/abhimehro/series_correction_project_updated/pull/185) | Tests `load_identified_outliers` errors |
| [#182](https://github.com/abhimehro/series_correction_project_updated/pull/182) | Test `export_comparison_sheets` |
| [#181](https://github.com/abhimehro/series_correction_project_updated/pull/181) | Specific exceptions in `generate_overview_table` |
| [#179](https://github.com/abhimehro/series_correction_project_updated/pull/179) | Refactor `batch_process` setup |
| [#176](https://github.com/abhimehro/series_correction_project_updated/pull/176) | Test `generate_overview_table` |
| [#174](https://github.com/abhimehro/series_correction_project_updated/pull/174) | Remove globals in `export_comparison_sheets` |

## Closed this session (4)

| Repo | PR | Reason |
|------|-----|--------|
| personal-config | [#1485](https://github.com/abhimehro/personal-config/pull/1485) | Duplicate alldebrid perf — superseded by #1489 |
| personal-config | [#1488](https://github.com/abhimehro/personal-config/pull/1488) | DIRTY → salvage draft [#1496](https://github.com/abhimehro/personal-config/pull/1496) |
| personal-config | [#1480](https://github.com/abhimehro/personal-config/pull/1480) | Session-doc draft superseded by this run |
| series_correction_project_updated | [#184](https://github.com/abhimehro/series_correction_project_updated/pull/184) | DIRTY → salvage draft [#195](https://github.com/abhimehro/series_correction_project_updated/pull/195) |

## Salvage drafts opened (2)

| Repo | Old PR | New draft PR | Tier |
|------|--------|--------------|------|
| personal-config | #1488 | [#1496](https://github.com/abhimehro/personal-config/pull/1496) | T3 |
| series_correction_project_updated | #184 | [#195](https://github.com/abhimehro/series_correction_project_updated/pull/195) | T1 |

## Post-session remainder (19 open)

| Repo | PR | State | CI | Disposition |
|------|-----|-------|-----|-------------|
| personal-config | [#1496](https://github.com/abhimehro/personal-config/pull/1496) | draft salvage | UNSTABLE | Human review |
| personal-config | [#1495](https://github.com/abhimehro/personal-config/pull/1495) | CLEAN | CLEAN | T2 trust-boundary defer |
| personal-config | [#1490](https://github.com/abhimehro/personal-config/pull/1490) | CLEAN | CLEAN | T2 trust-boundary defer |
| personal-config | [#1483](https://github.com/abhimehro/personal-config/pull/1483) | CLEAN | CLEAN | T2 trust-boundary defer |
| personal-config | [#1481](https://github.com/abhimehro/personal-config/pull/1481) | CLEAN | CLEAN | T2 trust-boundary defer |
| email-security-pipeline | [#1223](https://github.com/abhimehro/email-security-pipeline/pull/1223) | UNSTABLE | pytest fail | DEFER |
| email-security-pipeline | [#1222](https://github.com/abhimehro/email-security-pipeline/pull/1222) | DIRTY | CLEAN | Phase 2 salvage queue |
| email-security-pipeline | [#1219](https://github.com/abhimehro/email-security-pipeline/pull/1219) | DIRTY | CLEAN | Phase 2 salvage queue |
| email-security-pipeline | [#1215](https://github.com/abhimehro/email-security-pipeline/pull/1215) | UNSTABLE | CodeScene | `/cs-agent` posted |
| Seatek_Analysis | [#405](https://github.com/abhimehro/Seatek_Analysis/pull/405) | DIRTY | CLEAN | Phase 2 salvage queue |
| series_correction_project_updated | [#195](https://github.com/abhimehro/series_correction_project_updated/pull/195) | draft salvage | UNSTABLE | Human review (T1) |
| series_correction_project_updated | [#189](https://github.com/abhimehro/series_correction_project_updated/pull/189) | DIRTY | CLEAN | Phase 2 salvage queue |
| series_correction_project_updated | [#187](https://github.com/abhimehro/series_correction_project_updated/pull/187) | DIRTY | CLEAN | Phase 2 salvage queue |
| series_correction_project_updated | [#186](https://github.com/abhimehro/series_correction_project_updated/pull/186) | DIRTY | CLEAN | Phase 2 salvage queue |
| series_correction_project_updated | [#183](https://github.com/abhimehro/series_correction_project_updated/pull/183) | DIRTY | CLEAN | Phase 2 salvage queue |
| series_correction_project_updated | [#180](https://github.com/abhimehro/series_correction_project_updated/pull/180) | DIRTY | CLEAN | Phase 2 salvage queue |
| series_correction_project_updated | [#178](https://github.com/abhimehro/series_correction_project_updated/pull/178) | UNSTABLE | CodeScene | `/cs-agent` posted |
| series_correction_project_updated | [#177](https://github.com/abhimehro/series_correction_project_updated/pull/177) | DIRTY | CLEAN | Phase 2 salvage queue |
| series_correction_project_updated | [#175](https://github.com/abhimehro/series_correction_project_updated/pull/175) | DIRTY | CLEAN | Phase 2 salvage queue |

## Repos at zero (excluding remainder tail)

- `ctrld-sync`
- `Hydrograph_Versus_Seatek_Sensors_Project`
- `repoprompt-ce`
