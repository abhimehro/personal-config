# PR Inventory — 2026-06-30

**Session:** automated PR review (cron)  
**Mode:** review-and-merge  
**Preflight:** PASS 6/6  
**Repos scanned:** 7 (+ repoprompt-ce ad hoc)

## Summary

| Repo | Open (EOD) | Bot/automation PRs processed | Notes |
|------|------------|------------------------------|-------|
| personal-config | 40 | 10+ merged, 1 escalated | Large Jules burst; GraphQL timeout on first list |
| ctrld-sync | 0 | 2 merged | Palette pair #958+#960 |
| email-security-pipeline | 12 | 8 merged, 2 closed dupes, 2 escalated/deferred | Path-traversal cluster deduped |
| Seatek_Analysis | 0 | 1 merged | Daily QA #385 |
| Hydrograph_Versus_Seatek_Sensors_Project | 0 | 1 merged | Bolt #307 |
| series_correction_project_updated | 0 | 1 merged | Bolt #163 |
| repoprompt-ce | 0 | 2 merged | Palette #76 + Bolt #77 |

## Open automation PRs (EOD snapshot)

### personal-config (40 open)

| # | Author | Category | CI | Merge | Disposition |
|---|--------|----------|----|-------|-------------|
| 1430 | abhimehro | CI/INFRA | GREEN | CLEAN | **ESCALATE** SHA→tag workflow regression |
| 1428 | abhimehro | UI | GREEN | CLEAN | DEFER (Palette; review after #958/#960 pattern) |
| 1427 | abhimehro | REFACTOR | varies | varies | DEFER (permission/chmod logic) |
| 1426–1400 | abhimehro | mixed | mostly GREEN | varies | DEFER tail (Bolt/tests/refactor burst) |
| 1418 | abhimehro | SECURITY | GREEN | CLEAN | DEFER (symlink preservation — trust boundary) |
| 1416 | abhimehro | SECURITY | GREEN | CLEAN | DEFER (Sentinel symlink/FIX comment) |

_Merged this session:_ #1429 (dependabot), #1420, #1417, #1408, #1403, #1401, #1400, #1410, #1405, #1404 (trivial code-health / unused-import cluster).

### email-security-pipeline (12 open)

| # | Author | Category | CI | Merge | Disposition |
|---|--------|----------|----|-------|-------------|
| 1189 | abhimehro | SECURITY | GREEN | CLEAN | **ESCALATE** webhook token / netloc bypass |
| 1179 | abhimehro | TEST | FAIL (CodeScene) | UNSTABLE | **DEFER** `/cs-agent` posted |
| 1180 | abhimehro | TEST | varies | varies | DEFER |
| 1173–1168 | abhimehro | mixed | varies | varies | DEFER tail |

_Merged:_ #1181 (dependabot), #1185 (path traversal + tests), #1186 (ignored exceptions), #1184, #1183, #1171, #1170.  
_Closed dupes:_ #1187, #1188 (superseded #1185).

### ctrld-sync, Seatek, Hydrograph, series_correction, repoprompt-ce

**0 open** at EOD.

## Detection notes

- `get_prs.sh` hit HTTP 504 on personal-config GraphQL once; `gh pr list` REST fallback succeeded.
- Automation inferred via `body:automation_marker`, `branch:jules|bolt|palette|dependabot`, titles.
