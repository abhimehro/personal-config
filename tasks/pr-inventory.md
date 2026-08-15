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
