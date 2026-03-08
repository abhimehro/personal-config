# Bot PR Inventory

Snapshot timestamp: 2026-03-08 (session 4 — live inventory with Jules delegated-author heuristic).

## Summary

| Repo | Open Jules PRs | Merge | Merge After Fix | Request Changes | Escalate | Notes |
|---|---:|---:|---:|---:|---:|---|
| abhimehro/[REDACTED]-config | 8 | 5 | 2 | 1 | 0 | All checks passing; two overlap groups need merge ordering |
| abhimehro/email-security-pipeline | 1 | 1 | 0 | 0 | 0 | Clean performance optimization |
| abhimehro/ctrld-sync | 4 | 2 | 2 | 0 | 0 | Security PR should merge before perf/test cleanup PRs |
| **Totals** | **13** | **8** | **4** | **1** | **0** | |

## Attribution heuristic used this session

These PRs appear under the triggering human account (`abhimehro`) in the GitHub author field, but were treated as **bot-authored by Jules** because they include both of the following indicators:

- PR body/footer text: `PR created automatically by Jules ... started by @abhimehro`
- A bootstrap comment from `google-labs-jules`

This heuristic keeps the session within scope while still honoring the rule to avoid acting on true human-authored PRs.

## Current Open Jules PRs

| Repo | PR # | Displayed Author | Jules Evidence | Category | CI | Conflicts | Age (days) | Status | Disposition |
|---|---:|---|---|---|---|---|---:|---|---|
| abhimehro/[REDACTED]-config | 614 | abhimehro | Body footer + `google-labs-jules` comment | REFACTOR | passing | No | 0 | OPEN | MERGE-AFTER-FIX |
| abhimehro/[REDACTED]-config | 615 | abhimehro | Body footer + `google-labs-jules` comment | SECURITY | passing | No | 0 | OPEN | MERGE-AFTER-FIX |
| abhimehro/[REDACTED]-config | 616 | abhimehro | Body footer + `google-labs-jules` comment | SECURITY | passing | No | 0 | OPEN | MERGE |
| abhimehro/[REDACTED]-config | 617 | abhimehro | Body footer + `google-labs-jules` comment | SECURITY | passing | No | 0 | OPEN | MERGE |
| abhimehro/[REDACTED]-config | 618 | abhimehro | Body footer + `google-labs-jules` comment | PERFORMANCE | passing | No | 0 | OPEN | MERGE |
| abhimehro/[REDACTED]-config | 619 | abhimehro | Body footer + `google-labs-jules` comment | PERFORMANCE | passing | No | 0 | OPEN | REQUEST-CHANGES |
| abhimehro/[REDACTED]-config | 620 | abhimehro | Body footer + `google-labs-jules` comment | REFACTOR | passing | No | 0 | OPEN | MERGE |
| abhimehro/[REDACTED]-config | 621 | abhimehro | Body footer + `google-labs-jules` comment | REFACTOR | passing | No | 0 | OPEN | MERGE |
| abhimehro/email-security-pipeline | 539 | abhimehro | Body footer + `google-labs-jules` comment | PERFORMANCE | passing | No | 0 | OPEN | MERGE |
| abhimehro/ctrld-sync | 620 | abhimehro | Body footer + `google-labs-jules` comment | SECURITY | passing | Unknown (`mergeable=UNKNOWN`) | 0 | OPEN | MERGE |
| abhimehro/ctrld-sync | 621 | abhimehro | Body footer + `google-labs-jules` comment | REFACTOR | passing | Unknown (`mergeable=UNKNOWN`) | 0 | OPEN | MERGE |
| abhimehro/ctrld-sync | 622 | abhimehro | Body footer + `google-labs-jules` comment | REFACTOR | passing | No | 0 | OPEN | MERGE-AFTER-FIX |
| abhimehro/ctrld-sync | 623 | abhimehro | Body footer + `google-labs-jules` comment | PERFORMANCE | passing | No | 0 | OPEN | MERGE-AFTER-FIX |

## Notes

- Preflight passed after fixing `scripts/preflight-gh-pr-automation.sh` to correctly parse `repos:` from `tasks/pr-review-agent.config.yaml`.
- `gh pr checks` showed passing CI for all 13 PRs.
- `abhimehro/ctrld-sync#620` and `#621` returned `mergeable=UNKNOWN` / `mergeStateStatus=UNKNOWN` during metadata reads; re-check mergeability immediately before merge.
- No true human-authored PRs remain in the live queue after applying the Jules delegated-author heuristic.
