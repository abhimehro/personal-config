# Bot PR Inventory

Snapshot timestamp: 2026-03-09 (current session, post-preflight).

## Summary

| Repo | Open Bot PRs | Merge-Ready | Escalated | Remaining Open |
|---|---:|---:|---:|---:|
| abhimehro/[REDACTED]-config | 2 | 0 | 2 | 2 |
| abhimehro/email-security-pipeline | 0 | 0 | 0 | 0 |
| abhimehro/ctrld-sync | 1 | 1 | 0 | 1 |
| **Totals** | **3** | **1** | **2** | **3** |

## Open Bot PRs

| Repo | PR # | Author | Category | CI | Conflicts | Age (days) | Status | Disposition |
|---|---:|---|---|---|---|---:|---|---|
| abhimehro/[REDACTED]-config | 626 | Jules (delegated via @abhimehro) | CI/INFRA | failing | No | 0 | OPEN | ESCALATE |
| abhimehro/[REDACTED]-config | 627 | Jules (delegated via @abhimehro) | CI/INFRA | failing | No | 0 | OPEN | ESCALATE |
| abhimehro/ctrld-sync | 628 | Jules (delegated via @abhimehro) | REFACTOR | passing | No | 0 | OPEN | MERGE |

## Notes

- Jules-authored PRs are attributed to `author.login=abhimehro` in current metadata, so inventory uses the delegated-author heuristic: the Jules footer in the PR body plus the `google-labs-jules` bootstrap comment on the thread.
- `CI = failing` includes `mergeStateStatus=UNSTABLE` with at least one failed check in `statusCheckRollup`.
- `Conflicts = No` means `mergeable=MERGEABLE`; none of the current PRs are in a `DIRTY` or `CONFLICTING` merge state.
- `MERGE` for `ctrld-sync#628` reflects the review disposition, not an executed action. This environment can gather evidence and update local session artifacts, but it does not expose a GitHub write tool for cross-repo PR mutations.
