# PR Triage — 2026-05-23 salvage workflow

**Session:** Automated PR salvage + cleanup (cron). Preflight **passed**.

## MERGED (squash, branch deleted)

| Repo | PR | Notes |
| --- | ---: | --- |
| personal-config | 1027 | Session artifacts (`tasks/pr-*`, `lessons.md`) — all required checks green |
| Seatek_Analysis | 206 | Chore: untrack runtime `processing_warnings.log` |

## CLOSED-SUPERSEDED / CLOSED-SCOPE-CREEP

| Repo | PR | Reason |
| --- | ---: | --- |
| personal-config | 1019 | Superseded by merged #1027; branch carried ~400 unrelated files |
| personal-config | 1022 | Superseded by merged #1027 (salvage doc artifacts) |
| personal-config | 1020, 1021 | v2 salvage branches with ~402 files — closed; rebuild tests/adguard-only from `main` |
| personal-config | 985 | DIRTY batch2 secrets-path salvage; trust-boundary — rebuild as fresh draft |
| Seatek_Analysis | 190–198 | Batch1 salvages DIRTY after #199/#175; overlapping `repository_automation_tasks.py` |

## SALVAGE-DRAFT (human merge required — Phase 2 never auto-merges)

| Repo | PR | Tier | Notes |
| --- | ---: | --- | --- |
| personal-config | 1028 | T3 | `tests/test_scratch_triage.py` only (salvages #992) |
| Seatek_Analysis | 204 | T3 | Extension-check perf (salvages #188); CI green |
| email-security-pipeline | 894 | T3 | Palette console indicators (salvages #867); CodeScene failing |

## DEFER — CONFLICTING / UNSTABLE

### ctrld-sync

| PR | Disposition | Notes |
| ---: | --- | --- |
| 815 | DEFER-CONFLICT | Salvage `_gh_get` refactor |
| 837 | ESCALATE | `benchmark` check failing |
| 835, 789 | DEFER-UNSTABLE | Jules Sentinel / refactor |

### email-security-pipeline

| PR | Disposition | Notes |
| ---: | --- | --- |
| 807, 823, 841 | DEFER-CONFLICT | Bolt / code-health on hot paths |
| 842, 844 | DEFER-UNSTABLE | Jules perf/refactor |

## Phase 1 disposition summary

| Disposition | Count |
| --- | ---: |
| MERGE | 2 |
| CLOSE-SUPERSEDED / SCOPE-CREEP | 11 |
| SALVAGE-DRAFT (new or retained) | 3 |
| DEFER / ESCALATE | 9 |
