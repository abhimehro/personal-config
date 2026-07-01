# PR Inventory — 2026-06-30

**Session:** Automated PR salvage & cleanup (cron 17:00 UTC)  
**Preflight:** PASS 6/6 configured repos + repoprompt-ce read access  
**Mode:** review-and-merge + Phase 2 salvage  
**Stale threshold:** 30 days

## Summary

| Repo | Open (in-scope) | Merged | Closed | Salvage drafts | Remainder |
|------|-----------------|--------|--------|----------------|-----------|
| personal-config | 9 | 22 | 12 | 6 | 9 |
| ctrld-sync | 0 | 0 | 0 | 0 | **0** |
| email-security-pipeline | 6 | 5 | 3 | 3 | 6 |
| Seatek_Analysis | 0 | 0 | 0 | 0 | **0** |
| Hydrograph_Versus_Seatek_Sensors_Project | 0 | 0 | 0 | 0 | **0** |
| series_correction_project_updated | 0 | 0 | 0 | 0 | **0** |
| repoprompt-ce | 0 | 0 | 0 | 0 | **0** |

## Merged this session (27 squash)

### personal-config (22)

- [#1416](https://github.com/abhimehro/personal-config/pull/1416) Sentinel symlink false-positive fix
- [#1409](https://github.com/abhimehro/personal-config/pull/1409) Bolt triage title_lower cache
- [#1425](https://github.com/abhimehro/personal-config/pull/1425) Bolt bulk GraphQL PR metadata
- [#1426](https://github.com/abhimehro/personal-config/pull/1426) Bolt os.walk directory pruning
- [#1427](https://github.com/abhimehro/personal-config/pull/1427) Bolt permission-fix fail-fast
- [#1428](https://github.com/abhimehro/personal-config/pull/1428) Palette TTY spinner cleanup
- [#1421](https://github.com/abhimehro/personal-config/pull/1421) test fix-allowlist-format main
- [#1419](https://github.com/abhimehro/personal-config/pull/1419) Code health main refactor
- [#1414](https://github.com/abhimehro/personal-config/pull/1414) test _read_env_file coverage
- [#1413](https://github.com/abhimehro/personal-config/pull/1413) benchmark timing helper
- [#1412](https://github.com/abhimehro/personal-config/pull/1412) split test_generate_directory_listing
- [#1411](https://github.com/abhimehro/personal-config/pull/1411) test extract_domains_from_file errors
- [#1406](https://github.com/abhimehro/personal-config/pull/1406) test group_prs integration
- [#1399](https://github.com/abhimehro/personal-config/pull/1399) test _contains_all_keywords
- [#1396](https://github.com/abhimehro/personal-config/pull/1396) test _process_pr_group
- [#1395](https://github.com/abhimehro/personal-config/pull/1395) remove unused annotations (alldebrid)
- [#1394](https://github.com/abhimehro/personal-config/pull/1394) test test-adguard-import
- [#1392](https://github.com/abhimehro/personal-config/pull/1392) remove unused annotations
- [#1390](https://github.com/abhimehro/personal-config/pull/1390) remove unused json import
- [#1389](https://github.com/abhimehro/personal-config/pull/1389) env parsing edge-case tests
- [#1388](https://github.com/abhimehro/personal-config/pull/1388) consolidate_adblock_lists refactor
- [#1387](https://github.com/abhimehro/personal-config/pull/1387) fetch_weather error tests

### email-security-pipeline (5)

- [#1177](https://github.com/abhimehro/email-security-pipeline/pull/1177) remove silent KeyboardInterrupt catch
- [#1176](https://github.com/abhimehro/email-security-pipeline/pull/1176) sanitize_for_logging truncation tests
- [#1174](https://github.com/abhimehro/email-security-pipeline/pull/1174) ui.py missing tests
- [#1173](https://github.com/abhimehro/email-security-pipeline/pull/1173) email ingestion logging
- [#1172](https://github.com/abhimehro/email-security-pipeline/pull/1172) inverted threshold tests

## Closed this session (15)

| Repo | PR | Reason |
|------|-----|--------|
| personal-config | #1369–#1383 | Session-doc drafts superseded by 2026-06-30 run |
| personal-config | #1402, #1424, #1397, #1393, #1391, #1407 | DIRTY → salvage drafts #1433–#1438 |
| email-security-pipeline | #1168, #1175, #1191 | DIRTY → salvage drafts #1192–#1194 |

## Salvage drafts opened (9)

| Repo | Old PR | New draft PR |
|------|--------|--------------|
| personal-config | #1402 | [#1433](https://github.com/abhimehro/personal-config/pull/1433) |
| personal-config | #1424 | [#1434](https://github.com/abhimehro/personal-config/pull/1434) |
| personal-config | #1397 | [#1435](https://github.com/abhimehro/personal-config/pull/1435) |
| personal-config | #1393 | [#1436](https://github.com/abhimehro/personal-config/pull/1436) |
| personal-config | #1391 | [#1437](https://github.com/abhimehro/personal-config/pull/1437) |
| personal-config | #1407 | [#1438](https://github.com/abhimehro/personal-config/pull/1438) |
| email-security-pipeline | #1168 | [#1192](https://github.com/abhimehro/email-security-pipeline/pull/1192) |
| email-security-pipeline | #1175 | [#1193](https://github.com/abhimehro/email-security-pipeline/pull/1193) |
| email-security-pipeline | #1191 | [#1194](https://github.com/abhimehro/email-security-pipeline/pull/1194) |

## Post-session remainder

| Repo | PR | CI | Conflicts | Status |
|------|-----|-----|-----------|--------|
| personal-config | [#1398](https://github.com/abhimehro/personal-config/pull/1398) | FAIL GitGuardian | MERGEABLE | DEFER |
| personal-config | [#1422](https://github.com/abhimehro/personal-config/pull/1422) | FAIL CodeScene | MERGEABLE | DEFER (cs-agent posted) |
| personal-config | [#1432](https://github.com/abhimehro/personal-config/pull/1432) | FAIL Trunk MQ | MERGEABLE | session doc (this run) |
| personal-config | [#1433–1438](https://github.com/abhimehro/personal-config/pull/1433) | pending | MERGEABLE | DRAFT salvage — human review |
| email-security-pipeline | [#1179](https://github.com/abhimehro/email-security-pipeline/pull/1179) | FAIL CodeScene | DIRTY | DEFER (cs-agent posted) |
| email-security-pipeline | [#1180](https://github.com/abhimehro/email-security-pipeline/pull/1180) | FAIL Trunk MQ | MERGEABLE | DEFER |
| email-security-pipeline | [#1190](https://github.com/abhimehro/email-security-pipeline/pull/1190) | FAIL Trunk MQ | MERGEABLE | DEFER (Daily QA — not zero-diff) |
| email-security-pipeline | [#1192–1194](https://github.com/abhimehro/email-security-pipeline/pull/1192) | pending | MERGEABLE | DRAFT salvage — human review |

## Repos at zero open in-scope PRs

- `ctrld-sync`
- `Seatek_Analysis`
- `Hydrograph_Versus_Seatek_Sensors_Project`
- `series_correction_project_updated`
- `repoprompt-ce`
