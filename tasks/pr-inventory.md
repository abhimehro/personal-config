# PR Inventory — 2026-07-28 (Phase 2 Salvage)

**Source:** Live `gh pr list` after Phase 1 `tasks/pr-review-2026-07-28.md`\
**Preflight:** PASS 7/7 · `unset GH_TOKEN` (0eo) · `make cursor-cloud-hooks`\
**Branch:** `cursor-agent/automated-pr-salvage-workflow-de9a`\
**Trigger:** cron `0 17 * * *`

## Scope filter

Bot / automation-authored open PRs (dependabot, renovate,
Jules/Sentinel/Bolt/Palette, cursor-agent, Devin, Copilot). Phase 2 focuses on
**CONFLICTING** + Phase 1 **ESCALATE** / close-recommended remainder.

## Live open counts (post-salvage drafts)

| Repo                    |   Open | CONFLICTING | Notes                                                |
| ----------------------- | -----: | ----------: | ---------------------------------------------------- |
| personal-config         |      8 |           3 | +draft salvages #1803/#1804; #1800/#1791 still DIRTY |
| ctrld-sync              |      5 |           2 | +draft salvage #1072; #1069/#1064 DIRTY              |
| email-security-pipeline |      4 |           1 | #1362 DIRTY; #1370/#1375 preferred twins             |
| Seatek_Analysis         |      4 |           0 | #525/#518/#507 cluster; #535 UNSTABLE                |
| Hydrograph…             |      5 |           3 | #427/#420/#413 DIRTY; #418 preferred                 |
| series_correction…      |      5 |           0 | #293 close-dup of #299; +new #301 Sentinel           |
| repoprompt-ce           |      0 |           0 | Quiet                                                |
| **Total**               | **31** |       **9** |                                                      |

## CONFLICTING (Phase 2 primary)

| Repo                    |                                                                                    PR | Title                   | Disposition                                                                          |
| ----------------------- | ------------------------------------------------------------------------------------: | ----------------------- | ------------------------------------------------------------------------------------ |
| personal-config         |                        [1800](https://github.com/abhimehro/personal-config/pull/1800) | Bolt chained `.get()`   | **SALVAGED** → draft [#1804](https://github.com/abhimehro/personal-config/pull/1804) |
| personal-config         |                        [1791](https://github.com/abhimehro/personal-config/pull/1791) | Bolt regex pre-compile  | **SALVAGED** → draft [#1803](https://github.com/abhimehro/personal-config/pull/1803) |
| ctrld-sync              |                             [1064](https://github.com/abhimehro/ctrld-sync/pull/1064) | Palette prompt UX       | **SALVAGED** → draft [#1072](https://github.com/abhimehro/ctrld-sync/pull/1072)      |
| ctrld-sync              |                             [1069](https://github.com/abhimehro/ctrld-sync/pull/1069) | Palette partial success | **CLOSE-SUPERSEDED** by #1067                                                        |
| email-security-pipeline |                [1362](https://github.com/abhimehro/email-security-pipeline/pull/1362) | Sentinel TOCTOU         | **CLOSE-SUPERSEDED** prefer #1370 (0es)                                              |
| Hydrograph…             | [413](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/413) | Sentinel DoS            | **CLOSE-SUPERSEDED** prefer #418 (0es)                                               |
| Hydrograph…             | [427](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/427) | Bolt scalar             | **CLOSE-SUPERSEDED** by #428                                                         |
| Hydrograph…             | [420](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/420) | Bolt scalar subset      | **CLOSE-SUPERSEDED** by #428                                                         |

## New draft salvage PRs (human merge only)

| Repo            |                                                          New PR | Salvages | Verify                     |
| --------------- | --------------------------------------------------------------: | -------- | -------------------------- |
| personal-config | [#1804](https://github.com/abhimehro/personal-config/pull/1804) | #1800    | `py_compile` tasks.py      |
| personal-config | [#1803](https://github.com/abhimehro/personal-config/pull/1803) | #1791    | `py_compile` common.py     |
| ctrld-sync      |      [#1072](https://github.com/abhimehro/ctrld-sync/pull/1072) | #1064    | `uv run pytest` 364 passed |

## Phase 1 remainder — live status

| PR                     | Phase 1 reason          | Live state               | Phase 2 action                                |
| ---------------------- | ----------------------- | ------------------------ | --------------------------------------------- |
| pc #1800/#1791         | CONFLICTING bolt.md     | OPEN DIRTY               | Salvaged (drafts above)                       |
| pc #1796/#1784         | CWE-88 siblings         | OPEN CLEAN               | ESCALATE (#1784 has code; #1796 journal-only) |
| pc #1794               | Sentinel timeout/auth   | OPEN                     | ESCALATE (security)                           |
| pc #1792               | a11y markup             | OPEN                     | REQUEST_CHANGES                               |
| cs #1064               | CONFLICTING             | OPEN DIRTY               | Salvaged → #1072                              |
| cs #1069/#1066         | CLOSE-DUP of #1067      | OPEN                     | CLOSE-SUPERSEDED (MCP)                        |
| cs #1060               | Sentinel exception      | OPEN UNSTABLE (Trunk MQ) | ESCALATE                                      |
| esp #1362              | TOCTOU CONFLICTING      | OPEN DIRTY               | CLOSE-SUPERSEDED (0es)                        |
| esp #1370/#1375        | TOCTOU cluster          | OPEN CLEAN               | ESCALATE prefer #1370                         |
| esp #1366              | artifact skew           | OPEN CLEAN               | REQUEST_CHANGES (0er)                         |
| Seatek #525/#518/#507  | env-filter 0ej          | OPEN CLEAN               | ESCALATE cluster                              |
| Seatek #535            | repo-health             | OPEN UNSTABLE            | DEFER (Analyze FAIL)                          |
| hg #413/#427/#420      | CONFLICTING             | OPEN DIRTY               | CLOSE-SUPERSEDED                              |
| hg #418/#425           | Sentinel                | OPEN                     | ESCALATE (#418 preferred)                     |
| sc #293                | CLOSE-DUP of #299       | OPEN CLEAN               | CLOSE-SUPERSEDED                              |
| sc #295/#296/#297/#301 | security/perf/draft/new | OPEN                     | ESCALATE / DEFER / inventory                  |
| pc #1789/#1787/#1786   | Phase 1 escalate        | **MERGED** since Phase 1 | DROP                                          |
