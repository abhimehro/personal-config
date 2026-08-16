# PR inventory — 2026-08-16 (Phase 1 cron 13:00 UTC)

Preflight **PASS 7/7**. Inventoried **68** open PRs at session start.
Adversarial: claude-opus-5-thinking-high + gpt-5.6-sol-high (model picker N/A).

Dispositions are end-of-session (after squash-merge / close).

| Repo | PR | Author | Category | CI | Conflicts | Age | Disposition | Title |
| --- | ---: | --- | --- | --- | --- | ---: | --- | --- |
| Hydrograph_Versus_Seatek_Sensors_Project | 524 | abhimehro | SECURITY | CLEAN | OK | 0 | ESCALATE | Sentinel: path traversal in file sink |
| Hydrograph_Versus_Seatek_Sensors_Project | 523 | abhimehro | CI/INFRA | CLEAN | OK | 0 | HOLD | QA black wrap + `pr_body.txt` |
| Hydrograph_Versus_Seatek_Sensors_Project | 521 | cursor | DEPENDENCY | CLEAN | OK | 0 | MERGE | numpy pin 2.5.1→2.5.2 |
| Hydrograph_Versus_Seatek_Sensors_Project | 520 | abhimehro | SECURITY | CLEAN | OK | 0 | ESCALATE | Sentinel: path traversal in validate_data.py |
| Hydrograph_Versus_Seatek_Sensors_Project | 507 | abhimehro | SECURITY | CLEAN | OK | 0 | ESCALATE | salvage newline sanitize_filename |
| Hydrograph_Versus_Seatek_Sensors_Project | 498 | cursor | CI/INFRA | FAIL | OK | 0 | ESCALATE | repo-health (test fail) |
| Seatek_Analysis | 681 | abhimehro | PERFORMANCE | CLEAN | OK | 0 | HOLD | Bolt mean.default() |
| Seatek_Analysis | 680 | abhimehro | SECURITY | CLEAN | OK | 0 | ESCALATE | Sentinel file-read DoS (automation_tasks) |
| Seatek_Analysis | 679 | abhimehro | UI | CLEAN | OK | 0 | ESCALATE | Palette CLI empty-state (toolchain) |
| Seatek_Analysis | 676 | abhimehro | SECURITY | CLEAN | OK | 0 | ESCALATE | Sentinel file-reader DoS |
| Seatek_Analysis | 673 | abhimehro | CI/INFRA | CLEAN | OK | 0 | HOLD | Jules QA line wrap + delete lint_output.txt |
| Seatek_Analysis | 667 | abhimehro | SECURITY | CLEAN | OK | 0 | ESCALATE | Sentinel UnicodeDecodeError DoS |
| Seatek_Analysis | 665 | abhimehro | SECURITY | CLEAN | OK | 2 | ESCALATE | Sentinel file-read DoS hotspot |
| Seatek_Analysis | 662 | abhimehro | SECURITY | CLEAN | OK | 2 | ESCALATE | Sentinel UnicodeDecodeError read/write |
| Seatek_Analysis | 661 | dependabot | DEPENDENCY | FAIL | OK | 0 | ESCALATE | numpy 1.26→2.5.2 Series_27 |
| Seatek_Analysis | 657 | abhimehro | SECURITY | CLEAN | OK | 0 | ESCALATE | Sentinel yaml load exceptions |
| Seatek_Analysis | 643 | cursor | CI/INFRA | FAIL | OK | 0 | ESCALATE | repo-health untrack venv (11538 files) |
| ctrld-sync | 1183 | abhimehro | REFACTOR | FAIL | OK | 0 | ESCALATE | Devin split display.py (draft, CodeScene) |
| ctrld-sync | 1176 | dependabot | DEPENDENCY | CLEAN | OK | 0 | MERGE | ruff 0.16.1→0.16.2 |
| ctrld-sync | 1175 | dependabot | DEPENDENCY | CLEAN | OK | 0 | MERGE | pre-commit 4.6.1→4.6.2 |
| ctrld-sync | 1174 | abhimehro | SECURITY | DIRTY | DIRTY | 0 | ESCALATE | Sentinel input-length bypass |
| ctrld-sync | 1173 | abhimehro | CI/INFRA | CLEAN | OK | 0 | MERGE | Jules QA PlanRuleGroup typing |
| ctrld-sync | 1170 | dependabot | DEPENDENCY | CLEAN | OK | 0 | HOLD | gh-aw floating tag 0.86.2 |
| ctrld-sync | 1165 | abhimehro | CI/INFRA | CLEAN | OK | 2 | OOS-HUMAN | mypy test fixes (subset of #1173) |
| ctrld-sync | 1162 | cursor | CI/INFRA | CLEAN | OK | 0 | HOLD | repo-health ruff pin 0.16.1 (stale vs 0.16.2) |
| ctrld-sync | 1161 | abhimehro | PERFORMANCE | CLEAN | OK | 0 | HOLD | Bolt sum([list]) vs generator (0fo) |
| ctrld-sync | 1156 | abhimehro | SECURITY | CLEAN | OK | 0 | ESCALATE | Sentinel TOCTOU plan JSON |
| ctrld-sync | 1136 | dependabot | DEPENDENCY | CLEAN | OK | 0 | ESCALATE | mypy 1.19→2.3 major |
| email-security-pipeline | 1487 | abhimehro | PERFORMANCE | DIRTY | DIRTY | 0 | DEFER | Bolt headers subset + patch_bumpy2.py |
| email-security-pipeline | 1473 | cursor | CI/INFRA | CLEAN | OK | 0 | ESCALATE | repo-health docs; requirements-ci default |
| email-security-pipeline | 1471 | abhimehro | CI/INFRA | CLEAN | OK | 2 | MERGE | upload-sarif SHA pin v2.26.3 |
| email-security-pipeline | 1444 | dependabot | DEPENDENCY | FAIL | OK | 0 | ESCALATE | opencv 4→5 major |
| personal-config | 2011 | abhimehro | PERFORMANCE | CLEAN | OK | 0 | CLOSE | duplicate of #1984 |
| personal-config | 2008 | abhimehro | CI/INFRA | CLEAN | OK | 0 | MERGE | trufflehog+codeql SHA pins |
| personal-config | 2007 | abhimehro | SECURITY | DIRTY | DIRTY | 0 | ESCALATE | Sentinel CWE-78 eval |
| personal-config | 2000 | abhimehro | SECURITY | DIRTY | DIRTY | 0 | ESCALATE | Sentinel CWE-88 pgrep |
| personal-config | 1998 | abhimehro | SECURITY | CLEAN | OK | 0 | ESCALATE | Sentinel CWE-1236 spreadsheet |
| personal-config | 1997 | abhimehro | PERFORMANCE | DIRTY | DIRTY | 0 | DEFER | Bolt join list-comp twin |
| personal-config | 1996 | abhimehro | PERFORMANCE | CLEAN | OK | 2 | HOLD | Bolt join flip-flop |
| personal-config | 1991 | abhimehro | UI | DIRTY | DIRTY | 0 | HOLD | Palette HTML empty-state (unescaped HTML) |
| personal-config | 1989 | abhimehro | SECURITY | DIRTY | DIRTY | 2 | ESCALATE | Sentinel CWE-88 pgrep twin |
| personal-config | 1988 | cursor | REFACTOR | DIRTY | DIRTY | 2 | DEFER | salvage docs 2026-08-13 |
| personal-config | 1985 | abhimehro | PERFORMANCE | DIRTY | DIRTY | 2 | DEFER | Bolt join + scratch_triage.py |
| personal-config | 1984 | abhimehro | PERFORMANCE | CLEAN | OK | 0 | MERGE | draft_fixes set lookup |
| personal-config | 1982 | abhimehro | CI/INFRA | CLEAN | OK | 0 | HOLD | yaml soft-import in tests |
| personal-config | 1980 | abhimehro | SECURITY | FAIL | OK | 0 | ESCALATE | Sentinel SSRF + scratch + CodeScene |
| personal-config | 1979 | cursor | REFACTOR | DIRTY | DIRTY | 2 | DEFER | salvage docs 2026-08-12 |
| personal-config | 1978 | abhimehro | PERFORMANCE | CLEAN | OK | 2 | HOLD | Bolt join + adguard |
| personal-config | 1969 | abhimehro | FEATURE | FAIL | OK | 2 | OOS-HUMAN | skill-index source sync |
| personal-config | 1907 | abhimehro | SECURITY | FAIL | OK | 0 | ESCALATE | Sentinel CORS allow-all |
| repoprompt-ce | 257 | abhimehro | PERFORMANCE | UNSTABLE | OK | 0 | DEFER | Bolt (CI pending/fail) |
| repoprompt-ce | 256 | abhimehro | UI | CLEAN | OK | 0 | MERGE | Palette a11y DualClick/MCP |
| repoprompt-ce | 254 | abhimehro | SECURITY | FAIL | OK | 0 | ESCALATE | Sentinel TOCTOU (newest) |
| repoprompt-ce | 253 | abhimehro | UI | FAIL | OK | 0 | DEFER | Palette a11y (red CI) |
| repoprompt-ce | 250 | abhimehro | SECURITY | FAIL | OK | 0 | ESCALATE | Sentinel TOCTOU twin |
| repoprompt-ce | 249 | abhimehro | PERFORMANCE | FAIL | OK | 1 | DEFER | Bolt DateFormatter cache |
| repoprompt-ce | 247 | abhimehro | UI | CLEAN | OK | 2 | HOLD | Palette a11y AgentSessionRows + junk |
| repoprompt-ce | 244 | abhimehro | REFACTOR | FAIL | OK | 2 | DEFER | salvage MCPCommandParser tests |
| repoprompt-ce | 243 | abhimehro | SECURITY | FAIL | OK | 2 | ESCALATE | Sentinel TOCTOU twin |
| repoprompt-ce | 242 | cursor | CI/INFRA | CLEAN | OK | 0 | MERGE | repo-health CoC / 1.3.0 docs |
| repoprompt-ce | 241 | abhimehro | PERFORMANCE | FAIL | OK | 2 | DEFER | Bolt DateFormatter twin |
| repoprompt-ce | 239 | abhimehro | SECURITY | FAIL | OK | 2 | ESCALATE | Sentinel TOCTOU twin |
| repoprompt-ce | 237 | abhimehro | REFACTOR | FAIL | OK | 2 | DEFER | salvage REPLInputParser tests |
| repoprompt-ce | 236 | abhimehro | PERFORMANCE | FAIL | OK | 2 | DEFER | Bolt GitService DateFormatter |
| series_correction_project_updated | 398 | abhimehro | CI/INFRA | CLEAN | OK | 0 | CLOSE | QA daily review (zero-diff) |
| series_correction_project_updated | 393 | dependabot | DEPENDENCY | FAIL | OK | 0 | ESCALATE | numpy 2.2.6→2.5.2 |
| series_correction_project_updated | 390 | abhimehro | PERFORMANCE | CLEAN | OK | 0 | HOLD | Bolt shallow copy sanitizer (0fp) |
| series_correction_project_updated | 386 | dependabot | DEPENDENCY | FAIL | OK | 0 | ESCALATE | pandas 2.3.3→3.0.5 |
