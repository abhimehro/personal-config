# Automated PR inventory — 2026-05-22

**Trigger:** Cursor automation cron (`0 13 * * *`).  
**Preflight:** `bash scripts/preflight-gh-pr-automation.sh --config tasks/pr-review-agent.config.yaml` — **passed** (all 6 repos).  
**Config:** `tasks/pr-review-agent.config.yaml` — `mode: review-and-merge`, `merge_strategy: squash`, `stale_threshold_days: 30`, `auto_fix_enabled: true`.

**Open in-scope PRs (session start):** 35  
**Open in-scope PRs (session end):** 25

| Repo | PR | Author | Branch (head) | Files | Mergeable | Age (d) | CI | Title |
| --- | ---: | --- | --- | ---: | --- | ---: | --- | --- |
| personal-config | 1018 | abhimehro | jules-…-b4d04f70 | 0 | MERGEABLE | 0 | passing | Jules Daily QA (merged) |
| personal-config | 1017 | abhimehro | jules-…-9c20147c | 4 | MERGEABLE | 0 | passing | Bolt: parallelize gh pr list (ESCALATE) |
| personal-config | 1015 | abhimehro | jules-…-04cb665a | 7 | MERGEABLE | 0 | passing | Sentinel: AppleScript injection (merged) |
| personal-config | 1014 | abhimehro | jules-…-d9d20b63 | 6 | MERGEABLE | 0 | passing | Palette: confirmation prompts (merged) |
| personal-config | 1013 | app/cursor | cursor-agent/pr-salvage-workflow-ebe6 | 5 | MERGEABLE | 0 | passing | Salvage session artifacts (closed superseded) |
| personal-config | 1012 | abhimehro | devin/…-remove-unused-var | 1 | MERGEABLE | 0 | passing | fix(lint): SC2034 (merged) |
| personal-config | 1011 | app/cursor | cursor-agent/automated-pr-workflow-4420 | 5 | MERGEABLE | 0 | passing | PR review session artifacts (merged) |
| personal-config | 995 | abhimehro | cursor-agent/salvage-…-939-bolt | 3 | CONFLICTING | 3 | passing | Bolt: Tracker parallel I/O (DEFER) |
| personal-config | 992 | abhimehro | cursor-agent/salvage-…-945-test | 2 | CONFLICTING | 3 | passing | Testing: scratch_triage run_cmd (DEFER) |
| personal-config | 985 | abhimehro | cursor-agent/salvage-…-938-secu | 9 | CONFLICTING | 3 | failing | Security: secrets path (ESCALATE) |
| ctrld-sync | 821 | abhimehro | cursor-agent/salvage-…-794 | 1 | MERGEABLE | 3 | failing | Simplify rate-limit headers (DEFER) |
| ctrld-sync | 818 | abhimehro | cursor-agent/salvage-…-803 | 1 | MERGEABLE | 3 | failing | _retry_request refactor (DEFER) |
| ctrld-sync | 815 | abhimehro | cursor-agent/salvage-…-806 | 2 | MERGEABLE | 3 | failing | _gh_get refactor (DEFER) |
| ctrld-sync | 789 | abhimehro | jules-…-4942ccca | 1 | MERGEABLE | 7 | failing | print_plan_details refactor (DEFER) |
| email-security-pipeline | 889 | abhimehro | devin/…-precommit | 1 | MERGEABLE | 0 | passing | pre-commit-hooks bump (merged) |
| email-security-pipeline | 887 | abhimehro | automation-workflow-updates-… | 1 | MERGEABLE | 0 | passing | greetings.yml tag bump (ESCALATE) |
| email-security-pipeline | 867 | abhimehro | cursor-agent/salvage-…-861 | 2 | CONFLICTING | 3 | passing | Palette console indicators (DEFER) |
| email-security-pipeline | 844 | abhimehro | jules-…-ca12f13d | 1 | MERGEABLE | 7 | failing | deepfake refactor (DEFER) |
| email-security-pipeline | 842 | abhimehro | jules-…-bacb924b | 5 | MERGEABLE | 7 | failing | spam URL cache (DEFER) |
| email-security-pipeline | 841 | abhimehro | optimize-dict-get-… | 2 | CONFLICTING | 7 | passing | media_analyzer dict get (DEFER) |
| email-security-pipeline | 823 | abhimehro | fix-unused-imports | 2 | CONFLICTING | 7 | passing | unused security constants (DEFER) |
| email-security-pipeline | 807 | abhimehro | jules-…-437014dc | 2 | CONFLICTING | 10 | passing | IMAP batch tuning (DEFER) |
| Seatek_Analysis | 198–188,172 | abhimehro | cursor-agent/salvage-* / bolt-* | 1–3 | mostly CONFLICTING | 3–8 | mixed | Bolt perf + salvage batch (DEFER) |
| Hydrograph_Versus_Seatek_Sensors_Project | 195 | abhimehro | devin/…-fix-unused-imports | 1 | MERGEABLE | 0 | passing | F401 lint (merged) |
| series_correction_project_updated | 56 | abhimehro | bolt-optimize-correct-jumps-… | 1 | MERGEABLE | 0 | passing | NumPy correct_jumps (merged) |
| series_correction_project_updated | 55 | abhimehro | sentinel/fix-exception-leakage-… | 9 | MERGEABLE | 0 | failing | exception leakage fix (DEFER) |
