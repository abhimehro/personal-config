# PR Inventory — 2026-08-18 (Phase 2 salvage)

Phase 2 cron (17:00 UTC). Preflight PASS. Auth: `abhimehro` PAT. Mode: salvage
(draft PRs only; **S1 never merge**).

Live re-fetch: **77** open, **13 CONFLICTING**. Input: Phase 1 remainder from
`pr-review-2026-08-16.md` + PR #2016 (`pr-review-2026-08-17.md`).

## Start-of-session CONFLICTING

| Repo                    | PR     | Head                                    | Salvage result          |
| ----------------------- | ------ | --------------------------------------- | ----------------------- |
| ctrld-sync              | #1188  | `jules/uv-docker-bandit-hardening-y4f4` | CLOSE → draft #1194     |
| ctrld-sync              | #1174  | `copilot/add-is-valid-rule-fn`          | CLOSE → draft #1195     |
| ctrld-sync              | #1161  | `jules/fix-network-timeout-retry-3k3t`  | HOLD 0fo                |
| ctrld-sync              | #1136  | `copilot/update-mypy-2-x`               | ESCALATE                |
| personal-config         | #2007  | `copilot/replace-eval-with-shopt-u`     | ESCALATE 0fu (no salvage) |
| personal-config         | #2000  | `jules/pgrep-cwe88-hardening-3j5k`      | CLOSE → draft #2022     |
| personal-config         | #1997  | `jules/bolt-join-hardening-x9k2`        | CLOSE (superseded #1996) |
| personal-config         | #1991  | `copilot/palette-morning-brief-ux`      | CLOSE (superseded #1980) |
| personal-config         | #1989  | `copilot/fix-pgrep-cwe-88-injection`    | CLOSE (superseded #2022) |
| personal-config         | #1985  | `copilot/harden-bolt-join-lookup`       | CLOSE (superseded #1996) |
| personal-config         | #1907  | `copilot/add-cors-whitelist-to-scripts` | ESCALATE                |
| email-security-pipeline | #1495  | `copilot/add-daily-qa-workflow`         | CLOSE 0fr               |
| email-security-pipeline | #1487  | `jules/security-headers-hardening-k9m2` | CLOSE (already on main) |
| email-security-pipeline | #1473  | `jules/requirements-ci-default-5n8p`    | ESCALATE                |
| Seatek_Analysis         | #690   | `copilot/fix-posixct-comparison-type`   | CLOSE → draft #693      |

## Drafts opened this run

| Repo            | PR     | Branch                                              |
| --------------- | ------ | --------------------------------------------------- |
| personal-config | #2022  | `cursor-agent/salvage-pc-2000-pgrep-cwe88-517a`     |
| ctrld-sync      | #1194  | `cursor-agent/salvage-ctrld-1188-uv-docker-517a`    |
| ctrld-sync      | #1195  | `cursor-agent/salvage-ctrld-1174-is-valid-rule-517a` |
| Seatek_Analysis | #693   | `cursor-agent/salvage-seatek-690-posixct-517a`      |

## Merge-ready leftovers (human squash; not Phase 2)

| Repo                    | PR     | Note                              |
| ----------------------- | ------ | --------------------------------- |
| ctrld-sync              | #1194  | first (Docker/bandit + CI repair) |
| ctrld-sync              | #1195  | second (is_valid_rule)            |
| personal-config         | #2022  | pgrep CWE-88                      |
| Seatek_Analysis         | #693   | .POSIXct one-liner                |
| personal-config         | #1980  | Palette UX (keep; #1991 closed)   |
| personal-config         | #1996  | Bolt join CLEAN                   |
| personal-config         | #2016  | Phase 1 13:00 08-17 docs          |
| Hydrograph…             | #511   | hydro salvage leftover            |
| series_correction…      | #393   | pytest skip                       |

---

# PR Inventory — 2026-08-13 (Phase 2 salvage)

Phase 2 cron (17:00 UTC). Preflight PASS 7/7. Auth: `abhimehro` PAT. Mode:
salvage (draft PRs only; **S1 never merge**). Stale: 30 days.

Live re-fetch (not the 13:00 Phase 1 snapshot): **47** open PRs, **43** auto,
**0 CONFLICTING**.

## Start-of-session auto-open

| Repo                    | Auto open |
| ----------------------- | --------: |
| personal-config         |         8 |
| ctrld-sync              |         5 |
| email-security-pipeline |         3 |
| Seatek_Analysis         |         6 |
| Hydrograph…             |         4 |
| series_correction…      |         4 |
| repoprompt-ce           |        13 |
| **Total**               |    **43** |

## CONFLICTING / DIRTY

None. GitHub `mergeable=MERGEABLE` for every auto PR. Phase 2 still acted:
zero-diff CLOSE, contaminated-mega CLOSE (0fr), one unique-test salvage.

## Prior salvage drafts still open (do not re-roll)

| Repo            | PR                                                                                     | Note                                            |
| --------------- | -------------------------------------------------------------------------------------- | ----------------------------------------------- |
| Hydrograph…     | [#507](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/507) | newline sanitize (Aug 12)                       |
| ctrld-sync      | [#1159](https://github.com/abhimehro/ctrld-sync/pull/1159)                             | dry-run pluralize (Aug 12)                      |
| repoprompt-ce   | [#237](https://github.com/abhimehro/repoprompt-ce/pull/237)                            | REPLInputParserTests (Aug 12)                   |
| personal-config | [#1979](https://github.com/abhimehro/personal-config/pull/1979)                        | Aug 12 docs                                     |
| personal-config | [#1986](https://github.com/abhimehro/personal-config/pull/1986)                        | Phase 1 13:00 docs                              |
| personal-config | [#1988](https://github.com/abhimehro/personal-config/pull/1988)                        | this Phase 2 17:00 docs (prefer for 0fk squash) |

## Merge-ready leftovers (human squash; not Phase 2)

| Repo                    | PR                                                                                     | Note              |
| ----------------------- | -------------------------------------------------------------------------------------- | ----------------- |
| personal-config         | [#1984](https://github.com/abhimehro/personal-config/pull/1984)                        | `set()` lookup    |
| email-security-pipeline | [#1469](https://github.com/abhimehro/email-security-pipeline/pull/1469)                | Palette timer     |
| Hydrograph…             | [#509](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/509) | numpy 2.5.2       |
| repoprompt-ce           | [#235](https://github.com/abhimehro/repoprompt-ce/pull/235)                            | a11y copy buttons |

esp [#1471](https://github.com/abhimehro/email-security-pipeline/pull/1471) was
Phase 1 APPROVE (CodeQL pin) — still OPEN; not an auto-inventory hit this
salvage pass.

## Closed this Phase 2 pass

See `tasks/salvage-session-reports.md` Run — 2026-08-13.

# PR Inventory — Phase 2 Salvage 2026-08-12

Phase 2 cron (17:00 UTC). Preflight PASS (+ `make cursor-cloud-hooks`). Auth:
`abhimehro` PAT (Lesson 0ew). Mode: **salvage only — 0 autonomous merges (S1)**.

Input: Phase 1 draft
[#1977](https://github.com/abhimehro/personal-config/pull/1977)
(`pr-review-2026-08-12.md` remainder) + live CONFLICTING re-fetch.

## Live CONFLICTING automation queue (start)

| Repo            | PR   | Author / pattern     | Title                                   |
| --------------- | ---- | -------------------- | --------------------------------------- |
| personal-config | 1977 | app/cursor docs      | Phase 1 session report 2026-08-12       |
| ctrld-sync      | 1150 | Palette / abhimehro  | Grammatical Polish for Dry Run Errors   |
| Hydrograph…     | 504  | Sentinel / abhimehro | Log injection via filename sanitization |
| series…         | 378  | Sentinel / abhimehro | User enumeration timing attack          |
| repoprompt-ce   | 231  | Bolt / abhimehro     | Cache DateFormatter allocations         |
| repoprompt-ce   | 224  | salvage / abhimehro  | REPLInputParser edge-case coverage      |

## Open PR counts (end of Phase 2, approx)

| Repo                    |   Open |
| ----------------------- | -----: |
| personal-config         |      4 |
| ctrld-sync              |      3 |
| email-security-pipeline |      1 |
| Seatek_Analysis         |      2 |
| Hydrograph…             |      2 |
| series_correction…      |      4 |
| repoprompt-ce           |      9 |
| **Total**               | **25** |

## Salvage drafts opened this run

| Repo          | New PR                                                                                 | Salvages  |
| ------------- | -------------------------------------------------------------------------------------- | --------- |
| Hydrograph…   | [#507](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/507) | #504      |
| ctrld-sync    | [#1159](https://github.com/abhimehro/ctrld-sync/pull/1159)                             | #1150     |
| repoprompt-ce | [#237](https://github.com/abhimehro/repoprompt-ce/pull/237)                            | #224/#186 |

## Closed this run

| Repo            | PR   | Reason                                            |
| --------------- | ---- | ------------------------------------------------- |
| Hydrograph…     | 504  | Superseded by #507                                |
| ctrld-sync      | 1150 | Superseded by #1159 (contamination stripped)      |
| series…         | 378  | No-op — `dummy_todos.py` absent on main           |
| repoprompt-ce   | 224  | Superseded by clean #237                          |
| personal-config | 1977 | Superseded by this Phase 2 docs PR (0fk recovery) |

## Still escalated / deferred (human)

See `tasks/pr-triage.md` — CORS/TOCTOU/majors/CodeScene holds unchanged.

# PR inventory — 2026-08-16 (Phase 1 cron 13:00 UTC)

Preflight **PASS 7/7**. Inventoried **68** open PRs at session start.
Adversarial: claude-opus-5-thinking-high + gpt-5.6-sol-high (model picker N/A).

Dispositions are end-of-session (after squash-merge / close).

| Repo                                     |   PR | Author     | Category    | CI       | Conflicts | Age | Disposition | Title                                         |
| ---------------------------------------- | ---: | ---------- | ----------- | -------- | --------- | --: | ----------- | --------------------------------------------- |
| Hydrograph_Versus_Seatek_Sensors_Project |  524 | abhimehro  | SECURITY    | CLEAN    | OK        |   0 | ESCALATE    | Sentinel: path traversal in file sink         |
| Hydrograph_Versus_Seatek_Sensors_Project |  523 | abhimehro  | CI/INFRA    | CLEAN    | OK        |   0 | HOLD        | QA black wrap + `pr_body.txt`                 |
| Hydrograph_Versus_Seatek_Sensors_Project |  521 | cursor     | DEPENDENCY  | CLEAN    | OK        |   0 | MERGE       | numpy pin 2.5.1→2.5.2                         |
| Hydrograph_Versus_Seatek_Sensors_Project |  520 | abhimehro  | SECURITY    | CLEAN    | OK        |   0 | ESCALATE    | Sentinel: path traversal in validate_data.py  |
| Hydrograph_Versus_Seatek_Sensors_Project |  507 | abhimehro  | SECURITY    | CLEAN    | OK        |   0 | ESCALATE    | salvage newline sanitize_filename             |
| Hydrograph_Versus_Seatek_Sensors_Project |  498 | cursor     | CI/INFRA    | FAIL     | OK        |   0 | ESCALATE    | repo-health (test fail)                       |
| Seatek_Analysis                          |  681 | abhimehro  | PERFORMANCE | CLEAN    | OK        |   0 | HOLD        | Bolt mean.default()                           |
| Seatek_Analysis                          |  680 | abhimehro  | SECURITY    | CLEAN    | OK        |   0 | ESCALATE    | Sentinel file-read DoS (automation_tasks)     |
| Seatek_Analysis                          |  679 | abhimehro  | UI          | CLEAN    | OK        |   0 | ESCALATE    | Palette CLI empty-state (toolchain)           |
| Seatek_Analysis                          |  676 | abhimehro  | SECURITY    | CLEAN    | OK        |   0 | ESCALATE    | Sentinel file-reader DoS                      |
| Seatek_Analysis                          |  673 | abhimehro  | CI/INFRA    | CLEAN    | OK        |   0 | HOLD        | Jules QA line wrap + delete lint_output.txt   |
| Seatek_Analysis                          |  667 | abhimehro  | SECURITY    | CLEAN    | OK        |   0 | ESCALATE    | Sentinel UnicodeDecodeError DoS               |
| Seatek_Analysis                          |  665 | abhimehro  | SECURITY    | CLEAN    | OK        |   2 | ESCALATE    | Sentinel file-read DoS hotspot                |
| Seatek_Analysis                          |  662 | abhimehro  | SECURITY    | CLEAN    | OK        |   2 | ESCALATE    | Sentinel UnicodeDecodeError read/write        |
| Seatek_Analysis                          |  661 | dependabot | DEPENDENCY  | FAIL     | OK        |   0 | ESCALATE    | numpy 1.26→2.5.2 Series_27                    |
| Seatek_Analysis                          |  657 | abhimehro  | SECURITY    | CLEAN    | OK        |   0 | ESCALATE    | Sentinel yaml load exceptions                 |
| Seatek_Analysis                          |  643 | cursor     | CI/INFRA    | FAIL     | OK        |   0 | ESCALATE    | repo-health untrack venv (11538 files)        |
| ctrld-sync                               | 1183 | abhimehro  | REFACTOR    | FAIL     | OK        |   0 | ESCALATE    | Devin split display.py (draft, CodeScene)     |
| ctrld-sync                               | 1176 | dependabot | DEPENDENCY  | CLEAN    | OK        |   0 | MERGE       | ruff 0.16.1→0.16.2                            |
| ctrld-sync                               | 1175 | dependabot | DEPENDENCY  | CLEAN    | OK        |   0 | MERGE       | pre-commit 4.6.1→4.6.2                        |
| ctrld-sync                               | 1174 | abhimehro  | SECURITY    | DIRTY    | DIRTY     |   0 | ESCALATE    | Sentinel input-length bypass                  |
| ctrld-sync                               | 1173 | abhimehro  | CI/INFRA    | CLEAN    | OK        |   0 | MERGE       | Jules QA PlanRuleGroup typing                 |
| ctrld-sync                               | 1170 | dependabot | DEPENDENCY  | CLEAN    | OK        |   0 | HOLD        | gh-aw floating tag 0.86.2                     |
| ctrld-sync                               | 1165 | abhimehro  | CI/INFRA    | CLEAN    | OK        |   2 | OOS-HUMAN   | mypy test fixes (subset of #1173)             |
| ctrld-sync                               | 1162 | cursor     | CI/INFRA    | CLEAN    | OK        |   0 | HOLD        | repo-health ruff pin 0.16.1 (stale vs 0.16.2) |
| ctrld-sync                               | 1161 | abhimehro  | PERFORMANCE | CLEAN    | OK        |   0 | HOLD        | Bolt sum([list]) vs generator (0fo)           |
| ctrld-sync                               | 1156 | abhimehro  | SECURITY    | CLEAN    | OK        |   0 | ESCALATE    | Sentinel TOCTOU plan JSON                     |
| ctrld-sync                               | 1136 | dependabot | DEPENDENCY  | CLEAN    | OK        |   0 | ESCALATE    | mypy 1.19→2.3 major                           |
| email-security-pipeline                  | 1487 | abhimehro  | PERFORMANCE | DIRTY    | DIRTY     |   0 | DEFER       | Bolt headers subset + patch_bumpy2.py         |
| email-security-pipeline                  | 1473 | cursor     | CI/INFRA    | CLEAN    | OK        |   0 | ESCALATE    | repo-health docs; requirements-ci default     |
| email-security-pipeline                  | 1471 | abhimehro  | CI/INFRA    | CLEAN    | OK        |   2 | MERGE       | upload-sarif SHA pin v2.26.3                  |
| email-security-pipeline                  | 1444 | dependabot | DEPENDENCY  | FAIL     | OK        |   0 | ESCALATE    | opencv 4→5 major                              |
| personal-config                          | 2011 | abhimehro  | PERFORMANCE | CLEAN    | OK        |   0 | CLOSE       | duplicate of #1984                            |
| personal-config                          | 2008 | abhimehro  | CI/INFRA    | CLEAN    | OK        |   0 | MERGE       | trufflehog+codeql SHA pins                    |
| personal-config                          | 2007 | abhimehro  | SECURITY    | DIRTY    | DIRTY     |   0 | ESCALATE    | Sentinel CWE-78 eval                          |
| personal-config                          | 2000 | abhimehro  | SECURITY    | DIRTY    | DIRTY     |   0 | ESCALATE    | Sentinel CWE-88 pgrep                         |
| personal-config                          | 1998 | abhimehro  | SECURITY    | CLEAN    | OK        |   0 | ESCALATE    | Sentinel CWE-1236 spreadsheet                 |
| personal-config                          | 1997 | abhimehro  | PERFORMANCE | DIRTY    | DIRTY     |   0 | DEFER       | Bolt join list-comp twin                      |
| personal-config                          | 1996 | abhimehro  | PERFORMANCE | CLEAN    | OK        |   2 | HOLD        | Bolt join flip-flop                           |
| personal-config                          | 1991 | abhimehro  | UI          | DIRTY    | DIRTY     |   0 | HOLD        | Palette HTML empty-state (unescaped HTML)     |
| personal-config                          | 1989 | abhimehro  | SECURITY    | DIRTY    | DIRTY     |   2 | ESCALATE    | Sentinel CWE-88 pgrep twin                    |
| personal-config                          | 1988 | cursor     | REFACTOR    | DIRTY    | DIRTY     |   2 | DEFER       | salvage docs 2026-08-13                       |
| personal-config                          | 1985 | abhimehro  | PERFORMANCE | DIRTY    | DIRTY     |   2 | DEFER       | Bolt join + scratch_triage.py                 |
| personal-config                          | 1984 | abhimehro  | PERFORMANCE | CLEAN    | OK        |   0 | MERGE       | draft_fixes set lookup                        |
| personal-config                          | 1982 | abhimehro  | CI/INFRA    | CLEAN    | OK        |   0 | HOLD        | yaml soft-import in tests                     |
| personal-config                          | 1980 | abhimehro  | SECURITY    | FAIL     | OK        |   0 | ESCALATE    | Sentinel SSRF + scratch + CodeScene           |
| personal-config                          | 1979 | cursor     | REFACTOR    | DIRTY    | DIRTY     |   2 | DEFER       | salvage docs 2026-08-12                       |
| personal-config                          | 1978 | abhimehro  | PERFORMANCE | CLEAN    | OK        |   2 | HOLD        | Bolt join + adguard                           |
| personal-config                          | 1969 | abhimehro  | FEATURE     | FAIL     | OK        |   2 | OOS-HUMAN   | skill-index source sync                       |
| personal-config                          | 1907 | abhimehro  | SECURITY    | FAIL     | OK        |   0 | ESCALATE    | Sentinel CORS allow-all                       |
| repoprompt-ce                            |  257 | abhimehro  | PERFORMANCE | UNSTABLE | OK        |   0 | DEFER       | Bolt (CI pending/fail)                        |
| repoprompt-ce                            |  256 | abhimehro  | UI          | CLEAN    | OK        |   0 | MERGE       | Palette a11y DualClick/MCP                    |
| repoprompt-ce                            |  254 | abhimehro  | SECURITY    | FAIL     | OK        |   0 | ESCALATE    | Sentinel TOCTOU (newest)                      |
| repoprompt-ce                            |  253 | abhimehro  | UI          | FAIL     | OK        |   0 | DEFER       | Palette a11y (red CI)                         |
| repoprompt-ce                            |  250 | abhimehro  | SECURITY    | FAIL     | OK        |   0 | ESCALATE    | Sentinel TOCTOU twin                          |
| repoprompt-ce                            |  249 | abhimehro  | PERFORMANCE | FAIL     | OK        |   1 | DEFER       | Bolt DateFormatter cache                      |
| repoprompt-ce                            |  247 | abhimehro  | UI          | CLEAN    | OK        |   2 | HOLD        | Palette a11y AgentSessionRows + junk          |
| repoprompt-ce                            |  244 | abhimehro  | REFACTOR    | FAIL     | OK        |   2 | DEFER       | salvage MCPCommandParser tests                |
| repoprompt-ce                            |  243 | abhimehro  | SECURITY    | FAIL     | OK        |   2 | ESCALATE    | Sentinel TOCTOU twin                          |
| repoprompt-ce                            |  242 | cursor     | CI/INFRA    | CLEAN    | OK        |   0 | MERGE       | repo-health CoC / 1.3.0 docs                  |
| repoprompt-ce                            |  241 | abhimehro  | PERFORMANCE | FAIL     | OK        |   2 | DEFER       | Bolt DateFormatter twin                       |
| repoprompt-ce                            |  239 | abhimehro  | SECURITY    | FAIL     | OK        |   2 | ESCALATE    | Sentinel TOCTOU twin                          |
| repoprompt-ce                            |  237 | abhimehro  | REFACTOR    | FAIL     | OK        |   2 | DEFER       | salvage REPLInputParser tests                 |
| repoprompt-ce                            |  236 | abhimehro  | PERFORMANCE | FAIL     | OK        |   2 | DEFER       | Bolt GitService DateFormatter                 |
| series_correction_project_updated        |  398 | abhimehro  | CI/INFRA    | CLEAN    | OK        |   0 | CLOSE       | QA daily review (zero-diff)                   |
| series_correction_project_updated        |  393 | dependabot | DEPENDENCY  | FAIL     | OK        |   0 | ESCALATE    | numpy 2.2.6→2.5.2                             |
| series_correction_project_updated        |  390 | abhimehro  | PERFORMANCE | CLEAN    | OK        |   0 | HOLD        | Bolt shallow copy sanitizer (0fp)             |
| series_correction_project_updated        |  386 | dependabot | DEPENDENCY  | FAIL     | OK        |   0 | ESCALATE    | pandas 2.3.3→3.0.5                            |
