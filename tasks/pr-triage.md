# PR Triage — 2026-07-28 (Phase 2)

Decision tree applied per `docs/automated-pr-salvage-agent.md` Step 4. **No autonomous merges (S1).**

## SALVAGE (draft PRs opened)

| Old PR | New draft | Residual kept | Journals |
|--------|----------:|---------------|----------|
| pc [#1800](https://github.com/abhimehro/personal-config/pull/1800) | [#1804](https://github.com/abhimehro/personal-config/pull/1804) | `repository_automation_tasks.py` chained-get cache | skipped bolt.md (S2/0cs) |
| pc [#1791](https://github.com/abhimehro/personal-config/pull/1791) | [#1803](https://github.com/abhimehro/personal-config/pull/1803) | `TAG_PATTERN`/`SHA_PATTERN` | skipped bolt.md |
| cs [#1064](https://github.com/abhimehro/ctrld-sync/pull/1064) | [#1072](https://github.com/abhimehro/ctrld-sync/pull/1072) | `_prompt_for_missing_config` + bold headers | skipped palette.md; kept #1067 partial-success |

## CLOSE-SUPERSEDED (MCP review; API close blocked 0eq)

| PR | Canonical |
|----|-----------|
| cs #1069, #1066 | [#1067](https://github.com/abhimehro/ctrld-sync/pull/1067) on main |
| esp #1362 | Prefer [#1370](https://github.com/abhimehro/email-security-pipeline/pull/1370) (+ main #1353 app_runner) |
| hg #413 | Prefer [#418](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/418) |
| hg #427, #420 | [#428](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/428) on main |
| sc #293 | [#299](https://github.com/abhimehro/series_correction_project_updated/pull/299) on main |

## REQUEST_CHANGES

| PR | Reason |
|----|--------|
| esp [#1366](https://github.com/abhimehro/email-security-pipeline/pull/1366) | download-artifact v8 vs upload v7 (Lesson **0er**) |
| pc [#1792](https://github.com/abhimehro/personal-config/pull/1792) | Recent Activity `<dl>` still uses div wrappers vs #1795 |

## ESCALATE (human security / trust-boundary)

| PR | Tier | Why |
|----|------|-----|
| pc #1784 | T1 | CWE-88 pkill **code** fix (prefer over journal-only #1796) |
| pc #1796 | T2 | journal-only sibling of #1784 |
| pc #1794 | T1 | Sentinel timeout + auth token handling |
| cs #1060 | T1 | Sentinel exception sanitization |
| esp #1370 / #1375 | T1 | TOCTOU cluster — pick one |
| Seatek #525/#518/#507 | T1 | env-filter orderings (0ej) |
| hg #418 / #425 | T1 | DoS / file-size validation |
| sc #295 | T1 | formula-injection ABHI-1518 |
| sc #296 | T2 | Bolt NaN + patch_export cruft |

## DEFER / DROP

| PR | Disposition |
|----|-------------|
| pc #1789/#1787/#1786 | DROP — merged since Phase 1 |
| Seatek #535 | DEFER — Analyze FAIL + large repo-health |
| sc #297 | DEFER — draft repo-health |
| sc #301 | Inventory — new Sentinel CWE-209 (next Phase 1) |

## CodeScene

| PR | Action |
|----|--------|
| cs #1066 | Cleared to PASS since yesterday; still CLOSE-DUP |
| cs #1072 | Posted `/cs-agent` trigger (codescene MCP unavailable this run) |
