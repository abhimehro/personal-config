# PR Inventory — 2026-08-15

Phase 1 cron (13:00 UTC). Preflight PASS 7/7. Auth: `abhimehro` PAT (squash-merge works).
Mode: review-and-merge. Stale threshold: 30 days. Merge: squash.

Scope: automation-driven open PRs (Dependabot/Renovate/Jules/Devin/Copilot/Bolt/Palette/Sentinel/cursor-agent). Human OOS: personal-config #1969, ctrld-sync #1165 — not merged or closed.

Adversarial (parallel): opus-5, gpt-5.6-sol, gemini-3.7-flash.

## Start-of-session counts (auto targets)

| Repo | Auto open (approx) |
| ---- | -----------------: |
| personal-config | 18 |
| ctrld-sync | 7 |
| email-security-pipeline | 6 |
| Seatek_Analysis | 8 |
| Hydrograph… | 6 |
| series_correction… | 5 |
| repoprompt-ce | 13 |
| **Total auto + 2 human OOS** | **~80** |
| Repo                    | Auto open |
| ----------------------- | --------: |
| personal-config         |         8 |
| ctrld-sync              |         6 |
| email-security-pipeline |         4 |
| Seatek_Analysis         |        14 |
| Hydrograph…             |        10 |
| series_correction…      |         4 |
| repoprompt-ce           |        12 |
| **Total**               |    **58** |

## End-of-session open remainder

| Repo | Open | Notes |
| ---- | ---: | ----- |
| personal-config | 16 | #1969 human OOS; Sentinel/CORS/docs salvage/#2002 |
| ctrld-sync | 6 | #1165 human OOS; #1170 tag HOLD; #1156 TOCTOU |
| email-security-pipeline | 4 | #1487 scratch; #1471/#1444 escalate |
| Seatek_Analysis | 7 | Sentinel cluster; #661 numpy major; #643 |
| Hydrograph… | 2 | #507 sanitizer salvage; #498 repo-health |
| series_correction… | 3 | #390 shallow copy; majors #393/#386 |
| repoprompt-ce | 11 | TOCTOU/a11y/CI-fail/salvage tests |
| **Open total** | **49** | ~47 auto + 2 human OOS |
| Repo                    |    Open | Notes                                                      |
| ----------------------- | ------: | ---------------------------------------------------------- |
| personal-config         |       1 | #1907 CORS ESCALATE                                        |
| ctrld-sync              |      ~4 | Dependabot lock siblings after #1132; mypy major #1136     |
| email-security-pipeline |      ~3 | #1421 CONFLICTING; #1444 opencv major; #1437 salvage draft |
| Seatek_Analysis         |      10 | Sentinel path/subprocess cluster                           |
| Hydrograph…             |       8 | Sentinel sanitize_filename cluster                         |
| series_correction…      |       4 | #364/#365 auth; #371 CodeScene; #369 salvage               |
| repoprompt-ce           |       9 | TOCTOU + failing tests/a11y                                |
| **Approx open auto**    | **~44** |                                                            |

## Merged this session (19)

| Repo | PR | Category | Note |
| ---- | -- | -------- | ---- |
| series_correction… | [394](https://github.com/abhimehro/series_correction_project_updated/pull/394) | DEPENDENCY | pylint 4.0.6→4.0.7 |
| personal-config | [2004](https://github.com/abhimehro/personal-config/pull/2004) | PERFORMANCE | Bolt list-comps; CI all pass |
| personal-config | [2001](https://github.com/abhimehro/personal-config/pull/2001) | UI | Palette CTA |
| personal-config | [1993](https://github.com/abhimehro/personal-config/pull/1993) | CI/INFRA | setup-cli SHA pin |
| personal-config | [1992](https://github.com/abhimehro/personal-config/pull/1992) | CI/INFRA | setup SHA pin |
| personal-config | [1987](https://github.com/abhimehro/personal-config/pull/1987) | DOCS | agent-shell |
| ctrld-sync | [1171](https://github.com/abhimehro/ctrld-sync/pull/1171) | CI/INFRA | setup SHA pin |
| ctrld-sync | [1168](https://github.com/abhimehro/ctrld-sync/pull/1168) | UI | pluralize |
| email-security-pipeline | [1485](https://github.com/abhimehro/email-security-pipeline/pull/1485) | CI/INFRA | setup-cli SHA |
| email-security-pipeline | [1484](https://github.com/abhimehro/email-security-pipeline/pull/1484) | CI/INFRA | setup SHA |
| email-security-pipeline | [1483](https://github.com/abhimehro/email-security-pipeline/pull/1483) | DEPENDENCY | pre-commit |
| email-security-pipeline | [1482](https://github.com/abhimehro/email-security-pipeline/pull/1482) | DEPENDENCY | numpy 2.5.2 patch |
| email-security-pipeline | [1478](https://github.com/abhimehro/email-security-pipeline/pull/1478) | PERFORMANCE | header `in` checks |
| email-security-pipeline | [1469](https://github.com/abhimehro/email-security-pipeline/pull/1469) | UI | Palette timer; `.jules` |
| Seatek_Analysis | [674](https://github.com/abhimehro/Seatek_Analysis/pull/674) | UI | CLI empty-state |
| Hydrograph… | [518](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/518) | PERFORMANCE | `to_numpy()` |
| Hydrograph… | [515](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/515) | DEPENDENCY | pre-commit 4.6.2 |
| Hydrograph… | [509](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/509) | DEPENDENCY | numpy 2.5.1→2.5.2 (Dependabot rebase, 0fr) |
| repoprompt-ce | [235](https://github.com/abhimehro/repoprompt-ce/pull/235) | UI | a11y labels |
| Repo                    | PR   | Category    | Note                                          |
| ----------------------- | ---- | ----------- | --------------------------------------------- |
| ctrld-sync              | 1130 | DEPENDENCY  | pnpm/action-setup                             |
| ctrld-sync              | 1131 | DEPENDENCY  | gh-aw actions/setup pin                       |
| ctrld-sync              | 1129 | DEPENDENCY  | gh-aw setup-cli                               |
| ctrld-sync              | 1127 | UI          | Palette error grammar                         |
| ctrld-sync              | 1126 | SECURITY    | pygments 2.20.0 CVE (verified on main)        |
| ctrld-sync              | 1123 | CI/INFRA    | repo-health                                   |
| ctrld-sync              | 1132 | DEPENDENCY  | pytest-cov (one lock / 0fb)                   |
| Seatek_Analysis         | 619  | DEPENDENCY  | pnpm/action-setup                             |
| Seatek_Analysis         | 618  | CI/INFRA    | zero-diff daily QA                            |
| Seatek_Analysis         | 621  | PERFORMANCE | Bolt POSIXct guard (verified on main)         |
| Hydrograph…             | 481  | DEPENDENCY  | pnpm/action-setup                             |
| Hydrograph…             | 482  | DEPENDENCY  | pandas requirements align to 3.0.5 (verified) |
| email-security-pipeline | 1439 | UI          | Palette email hint                            |
| email-security-pipeline | 1435 | CI/INFRA    | repo-health                                   |
| email-security-pipeline | 1446 | DEPENDENCY  | certifi                                       |
| email-security-pipeline | 1445 | DEPENDENCY  | pytest                                        |
| email-security-pipeline | 1443 | DEPENDENCY  | pre-commit                                    |
| email-security-pipeline | 1442 | CI/INFRA    | zero-diff daily QA                            |
| personal-config         | 1924 | PERFORMANCE | Bolt yaml import fallback                     |
| personal-config         | 1931 | CI/INFRA    | repo-health TruffleHog                        |
| personal-config         | 1912 | CI/INFRA    | docs Phase1 2026-08-04                        |
| repoprompt-ce           | 209  | CI/INFRA    | zero-diff Jules QA                            |
| repoprompt-ce           | 203  | UI          | Palette a11y Chat buttons                     |
| repoprompt-ce           | 205  | CI/INFRA    | repo-health community templates               |

## Closed this session (12)

| Repo | PR | Reason |
| ---- | -- | ------ |
| series_correction… | 396, 392 | zero-diff daily QA |
| repoprompt-ce | 252, 246 | zero-diff Jules QA |
| email-security-pipeline | 1480, 1476 | `.Jules/` case collision (0fe); superseded by #1469 |
| Hydrograph… | 517 | stray `patch.diff` / `.orig` (0fg); superseded by #518 |
| Hydrograph… | 513, 511 | duplicate Bolt `np.where` twins of #518 |
| ctrld-sync | 1159 | CONFLICTING salvage; superseded by #1168 |
| Seatek_Analysis | 670 | only `test_results.txt` (0fg) |
| personal-config | 1986 | docs cascade; 08-08…13 recovered onto 864b (0fk) |

## Representative remaining (disposition)

| Repo | PR | Disposition |
| ---- | -- | ----------- |
| personal-config | 1907, 2000, 1998, 1989, 1980 | ESCALATE Sentinel/CORS |
| personal-config | 2002 | ESCALATE workflow rewrite |
| personal-config | 1991 | HOLD unescaped `html_empty_state` |
| personal-config | 1997/1996/1985/1984/1978 | HOLD join cluster |
| personal-config | 1982 | HOLD yaml skipIf |
| personal-config | 1988, 1979 | DEFER Phase 2 salvage docs |
| personal-config | 1969 | HUMAN OOS (skill-index) |
| ctrld-sync | 1170 | HOLD floating gh-aw tag |
| ctrld-sync | 1161 | HOLD sum/join (0fo) |
| ctrld-sync | 1156 | ESCALATE TOCTOU |
| ctrld-sync | 1136 | ESCALATE mypy 2.x |
| ctrld-sync | 1165 | HUMAN OOS |
| email-security-pipeline | 1487 | HOLD `patch_bumpy2.py` (0fg) |
| email-security-pipeline | 1471, 1444 | ESCALATE workflow / opencv 5 |
| Seatek_Analysis | 667/665/662/657 | ESCALATE Sentinel |
| Seatek_Analysis | 661 | ESCALATE numpy 1.26→2.5.2 |
| Seatek_Analysis | 643, 673 | HOLD repo-health / lint scratch |
| Hydrograph… | 507 | ESCALATE sanitizer salvage |
| Hydrograph… | 498 | HOLD failing CI |
| series_correction… | 390, 393, 386 | HOLD/ESCALATE 0fp + majors |
| repoprompt-ce | 250/243/239 | ESCALATE TOCTOU |
| repoprompt-ce | 253 | HOLD failing CI + duplicate #235 |
| Repo            | PR   | Reason                                                       |
| --------------- | ---- | ------------------------------------------------------------ |
| personal-config | 1925 | CONFLICTING docs cascade after #1912; recovered Aug 5 report |
| personal-config | 1930 | CONFLICTING docs cascade; recovered Aug 6 report             |
| personal-config | 1933 | CONFLICTING salvage docs cascade                             |
| personal-config | 1914 | Trunk MQ fail + docs cascade                                 |
| Seatek_Analysis | 615  | Superseded by focused #621; workflow scope creep             |

## Representative remaining (disposition)

| Repo            | PR                                      | Disposition                               |
| --------------- | --------------------------------------- | ----------------------------------------- |
| personal-config | 1907                                    | ESCALATE CORS                             |
| Seatek_Analysis | 620/617/612/610/607/605/590/585/580/573 | ESCALATE Sentinel cluster                 |
| Hydrograph…     | 484…459                                 | ESCALATE sanitize cluster                 |
| series…         | 365/364                                 | ESCALATE auth                             |
| series…         | 371                                     | REQUEST_CHANGES + CodeScene trigger       |
| series…         | 369                                     | DEFER salvage draft (CodeScene)           |
| esp             | 1421                                    | REQUEST_CHANGES / DEFER CONFLICTING       |
| esp             | 1444                                    | ESCALATE opencv major                     |
| esp             | 1437                                    | DEFER salvage draft                       |
| rpce            | 211                                     | REQUEST_CHANGES XCTSkip (now CONFLICTING) |
| rpce            | 210/201/196                             | ESCALATE TOCTOU                           |
| rpce            | 212/194/186                             | REQUEST_CHANGES failing CI                |
| ctrld-sync      | 1136                                    | ESCALATE mypy major                       |
| ctrld-sync      | 1133–1135                               | DEFER lock cascade                        |
