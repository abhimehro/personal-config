# PR Inventory — 2026-08-12

Phase 1 cron (13:00 UTC). Preflight **PASS 7/7**. Auth: `abhimehro` PAT.
Mode: review-and-merge. Stale threshold: 30 days. Merge: squash.

Scope: automation-driven open PRs (bot authors + human-authored
Bolt/Jules/Sentinel/Palette/salvage/cursor-agent/Dependabot).

## Start-of-session counts (auto targets)

| Repo | Auto open |
| ---- | --------: |
| personal-config | 4 |
| ctrld-sync | 3 |
| email-security-pipeline | 2 |
| Seatek_Analysis | 6 |
| Hydrograph… | 2 |
| series_correction… | 5 |
| repoprompt-ce | 8 |
| **Total** | **30** |

## Full inventory

| Repo | PR | Author | Category | CI | Conflicts | Age | Status |
| ---- | -- | ------ | -------- | -- | --------- | --: | ------ |
| personal-config | 1974 | cursor | CI/INFRA | green | CLEAN | 0 | MERGE→merge |
| personal-config | 1967 | abhimehro | UI | green | CLEAN | 0 | MERGE→merge |
| personal-config | 1966 | cursor | CI/INFRA | green | CLEAN | 0 | docs cascade — recover then close |
| personal-config | 1907 | abhimehro | SECURITY | green | CLEAN | 8 | ESCALATE CORS title/scope |
| ctrld-sync | 1156 | abhimehro | SECURITY | green | ? | 1 | ESCALATE TOCTOU |
| ctrld-sync | 1150 | abhimehro | UI | green | DIRTY | 2 | DEFER conflict + 0fm hold |
| ctrld-sync | 1136 | dependabot | DEPENDENCY | green | CLEAN | 4 | ESCALATE mypy major 1→2 |
| email-security-pipeline | 1467 | abhimehro | PERFORMANCE | green | CLEAN | 0 | MERGE→merge |
| email-security-pipeline | 1444 | dependabot | DEPENDENCY | fail | CLEAN | 4 | ESCALATE opencv major + CI |
| Seatek_Analysis | 658 | abhimehro | PERFORMANCE | green | CLEAN | 0 | MERGE (prefer over #652) |
| Seatek_Analysis | 657 | abhimehro | SECURITY | green | CLEAN | 0 | REQUEST_CHANGES fail-open |
| Seatek_Analysis | 655 | abhimehro | UI | green | CLEAN | 0 | MERGE after #658 |
| Seatek_Analysis | 653 | abhimehro | SECURITY | green | CLEAN | 0 | CLOSE incomplete/journal |
| Seatek_Analysis | 652 | abhimehro | PERFORMANCE | green | CLEAN | 0 | CLOSE twin of #658 |
| Seatek_Analysis | 643 | cursor | CI/INFRA | fail CS | CLEAN | 1 | DEFER CodeScene + venv untrack |
| Hydrograph… | 504 | abhimehro | SECURITY | green | DIRTY | 0 | ESCALATE sanitize + conflict |
| Hydrograph… | 498 | cursor | CI/INFRA | fail test | CLEAN | 1 | DEFER failing tests + junk |
| series… | 388 | abhimehro | CI/INFRA | green | CLEAN | 0 | MERGE zero-diff |
| series… | 386 | dependabot | DEPENDENCY | fail | CLEAN | 0 | ESCALATE pandas 2→3 |
| series… | 385 | dependabot | DEPENDENCY | fail | CLEAN | 0 | ESCALATE numpy bump + CI |
| series… | 378 | abhimehro | SECURITY | — | DIRTY | 2 | ESCALATE auth timing |
| series… | 375 | abhimehro | FEATURE | fail CS | CLEAN | 3 | DEFER CodeScene salvage |
| repoprompt-ce | 235 | abhimehro | UI | fail | CLEAN | 0 | DEFER failing shard |
| repoprompt-ce | 234 | abhimehro | CI/INFRA | fail | CLEAN | 0 | DEFER zero-diff + fail CI |
| repoprompt-ce | 232 | abhimehro | SECURITY | fail? | CLEAN | 0 | ESCALATE TOCTOU+scope creep |
| repoprompt-ce | 231 | abhimehro | PERFORMANCE | — | DIRTY | 1 | HOLD 0fm DateFormatter |
| repoprompt-ce | 228 | abhimehro | SECURITY | fail | CLEAN | 1 | ESCALATE TOCTOU twin |
| repoprompt-ce | 227 | abhimehro | FEATURE | fail | CLEAN | 1 | DEFER contaminated salvage |
| repoprompt-ce | 226 | abhimehro | UI | fail | CLEAN | 2 | REQUEST_CHANGES scope creep |
| repoprompt-ce | 224 | abhimehro | FEATURE | fail | DIRTY | 2 | DEFER conflict salvage |

## End-of-session (auto)

| Repo | Open (approx) | Notes |
| ---- | ------------: | ----- |
| personal-config | 1 | #1907 ESCALATE |
| ctrld-sync | 3 | TOCTOU / 0fm / mypy2 |
| email-security-pipeline | 1 | opencv5 |
| Seatek_Analysis | 2 | #657 RC / #643 CS |
| Hydrograph… | 2 | #504 / #498 |
| series_correction… | 4 | auth + majors + CS |
| repoprompt-ce | 8 | TOCTOU / a11y / salvage |
| **Total** | **~21** | |
