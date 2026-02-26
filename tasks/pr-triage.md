# PR Triage Findings

Triage basis: pre-action open PR snapshot from `tasks/pr-inventory.md`.

## Exact Duplicates / High File Overlap

| Repo | PRs | Overlap | Keep | Close | Rationale |
|---|---|---:|---|---|---|
| abhimehro/ctrld-sync | #406, #399 | 1.00 | #406 | #399 | Same file set and same objective (parallel pytest); retain newer branch and close redundant variant after/with fix. |

## Semantic Duplicates

| Repo | PRs | Keep | Close | Rationale |
|---|---|---|---|---|
| abhimehro/email-security-pipeline | #381, #372 | #381 | #372 | Both target nested archive duplication logic in media analyzer; #381 is broader and includes tests. |
| abhimehro/ctrld-sync | #405, #402, #395 | - | - | All modify test workflow setup; consolidate into one branch/PR to avoid drift between overlapping CI changes. |

## Superseded PRs (No Effective Diff vs base)

| Repo | PR # | Proposed Disposition | Rationale |
|---|---:|---|---|
| abhimehro/ctrld-sync | 397 | CLOSE-DUPLICATE | PR currently has zero changed files and is effectively superseded by base branch state. |
| abhimehro/email-security-pipeline | 370 | CLOSE-DUPLICATE | PR currently has zero changed files and is effectively superseded by base branch state. |
| abhimehro/email-security-pipeline | 371 | CLOSE-DUPLICATE | PR currently has zero changed files and is effectively superseded by base branch state. |
| abhimehro/email-security-pipeline | 373 | CLOSE-DUPLICATE | PR currently has zero changed files and is effectively superseded by base branch state. |
| abhimehro/personal-config | 379 | CLOSE-DUPLICATE | PR currently has zero changed files and is effectively superseded by base branch state. |
| abhimehro/personal-config | 380 | CLOSE-DUPLICATE | PR currently has zero changed files and is effectively superseded by base branch state. |
| abhimehro/personal-config | 382 | CLOSE-DUPLICATE | PR currently has zero changed files and is effectively superseded by base branch state. |
| abhimehro/personal-config | 383 | CLOSE-DUPLICATE | PR currently has zero changed files and is effectively superseded by base branch state. |
| abhimehro/personal-config | 387 | CLOSE-DUPLICATE | PR currently has zero changed files and is effectively superseded by base branch state. |
| abhimehro/personal-config | 390 | CLOSE-DUPLICATE | PR currently has zero changed files and is effectively superseded by base branch state. |

## Conflicting PRs (Manual Review)

| Repo | PR # | Issue | Action |
|---|---:|---|---|
| abhimehro/ctrld-sync | 394 | Merge conflict (`CONFLICTING/DIRTY`) | ESCALATE or rebase before merge decision. |
| abhimehro/ctrld-sync | 407 | Overlaps file targets with #394 (`main.py`, `uv.lock`) but different intent. | ESCALATE for manual selection/rebase order; do not auto-close as duplicate. |
| abhimehro/email-security-pipeline | 372 | Merge conflict (`CONFLICTING/DIRTY`) | ESCALATE or rebase before merge decision. |
| abhimehro/email-security-pipeline | 381 | Merge conflict (`CONFLICTING/DIRTY`) | ESCALATE or rebase before merge decision. |

## Stale Candidates (>30 days inactive and failing CI)

No stale candidates detected under the configured threshold.

## Execution Constraints Encountered

- Attempted `CLOSE-DUPLICATE` actions via `gh pr close` failed due GitHub App permission limits: `Resource not accessible by integration (closePullRequest/addComment)`.
- For non-`personal-config` repositories, merge attempts were blocked by branch policy and unavailable elevated permissions (`--auto` and `--admin` not permitted).
