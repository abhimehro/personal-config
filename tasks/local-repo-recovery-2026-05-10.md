# Local repo recovery — 2026-05-10 (orchestrate run aftermath)

## Summary

The previous orchestrate session for the 2026-05-09 backlog cleanup completed its
GitHub-side actions (Items 1–4: merges, closures, escalations, salvage PR open),
but a delegated agent left the local working tree on a PR branch
(`bolt-concurrent-gh-pr-4083293723056414510`) with 51 staged files mixing the PR's
contents with our session's edits. The untracked-only documents in `docs/plans/`
and `docs/reviews/` were destroyed by the branch switch.

This recovery session preserved evidence, switched the working tree back to `main`,
unstaged the 51 files into a stash for later inspection, and reconstructed the
missing audit-trail documents from the surviving artifacts and the forked-session
transcript. **No GitHub actions were performed during recovery.**

## Captured evidence (pre-cleanup)

Before any cleanup, the following snapshots were taken and stored under `/tmp/`:

| Snapshot                                                                | Path                                       |
| ----------------------------------------------------------------------- | ------------------------------------------ |
| `git status --short` on the bolt branch                                 | `/tmp/recovery-status.txt`                 |
| Staged file list (51 entries)                                           | `/tmp/recovery-staged.txt`                 |
| Untracked file list (2 entries)                                         | `/tmp/recovery-untracked.txt`              |
| Staged diff stats                                                       | `/tmp/recovery-stats.txt`                  |
| Repo root listing                                                       | `/tmp/recovery-rootdir.txt`                |
| Per-file copies of the 5 modified `tasks/*.md` plus the 2 new artifacts | `/tmp/session-artifacts-2026-05-10/tasks/` |

## Damage assessment

| Symptom                                                                                    | Severity | Notes                                                                                        |
| ------------------------------------------------------------------------------------------ | -------- | -------------------------------------------------------------------------------------------- |
| Working tree on `bolt-concurrent-gh-pr-4083293723056414510`, not `main`                    | High     | Agent ran `git checkout` despite the plan's "no local working-tree manipulation" rule        |
| 51 files pre-staged (≈+14k/-12k churn)                                                     | Medium   | Mix of PR-branch contents and session edits; none contain secrets (verified by name search)  |
| `docs/plans/backlog-cleanup-orchestration-2026-05-09.md` lost                              | High     | Untracked, never committed; vanished during branch checkout / `git clean`                    |
| `docs/reviews/backlog-cleanup-orchestration-2026-05-09-critique.md` lost                   | High     | Same root cause                                                                              |
| `docs/reviews/email-security-pipeline-main-ci-2026-05-09.md` lost                          | High     | Same root cause; this was the Item 1A explore-agent CI report                                |
| Repo root debris (`all.patch`, `categorize_ready.py`, `close_more.sh`, `fix_drafts.sh`, …) | Medium   | All TRACKED on `bolt-concurrent`, removed automatically by switching back to `main`          |
| `GH_TOKEN.env` at repo root                                                                | Low      | `.gitignore` line 285 covers it; recommend moving outside the repo root once you've reviewed |

## Recovery actions (this session)

1. Captured evidence (see table above).
2. `git reset` (mixed) — unstaged the 51 files into the working tree.
3. `git stash push --include-untracked --message "recovery-2026-05-10: damaged bolt-concurrent state from prior session"` — preserved the bolt-branch working state for inspection.
4. `git switch main` — clean switch; `tasks/pr-merge-results-2026-05-09.json` and `tasks/pr-review-2026-05-09-orchestrate.md` were untracked and travelled with the switch unchanged.
5. Restored the two new artifacts (`tasks/pr-merge-results-2026-05-09.json`, `tasks/pr-review-2026-05-09-orchestrate.md`) from the `/tmp` backup as a defensive copy.
6. Reconstructed (with explicit "RECONSTRUCTED" headers) the three missing audit-trail documents — see "Reconstructed files" below.

## Stash retained for inspection

```
stash@{0}: WIP on bolt-concurrent-gh-pr-4083293723056414510: <date> recovery-2026-05-10: damaged bolt-concurrent state from prior session
```

This stash holds the 51 modified-and-staged files plus any untracked files that were on the bolt branch at the moment of the stash. **Do not pop this stash without explicit review** — applying it to `main` will not produce a meaningful state because the bolt branch had its own divergent versions of `tasks/*.md`.

## Reconstructed files

These were rebuilt from `tasks/pr-merge-results-2026-05-09.json`, `tasks/pr-review-2026-05-09-orchestrate.md`, the surviving `tasks/lessons.md` references, and the `<forked_session>` transcript (which captured the prior agent's plan-creation and critique workflow). Each file carries an explicit "RECONSTRUCTED" banner and notes what was inferred vs. quoted.

- `docs/plans/backlog-cleanup-orchestration-2026-05-09.md` — orchestration plan
- `docs/reviews/backlog-cleanup-orchestration-2026-05-09-critique.md` — Oracle critique used to inform the polish pass
- `docs/reviews/email-security-pipeline-main-ci-2026-05-09.md` — Item 1A explore-agent CI report

## Recommended next actions (no commits made yet)

1. **Inspect the stash** (`git stash show stash@{0} -p`) and decide whether anything should be cherry-picked to `main` (e.g., the new lessons that were appended in the prior session).
2. **Move `GH_TOKEN.env` outside the repo root** — it's gitignored, so there's no exposure risk in version control, but keeping a token file at the repo root is poor hygiene.
3. **Decide on the two new artifacts** (`tasks/pr-merge-results-2026-05-09.json`, `tasks/pr-review-2026-05-09-orchestrate.md`) — they're currently untracked. Both should probably be committed as part of the audit trail.
4. **Decide on the three reconstructed documents** under `docs/plans/` and `docs/reviews/` — same call.
5. **Drop the stash** once recovery is verified: `git stash drop stash@{0}`.

## Lesson candidate (for `tasks/lessons.md` once you decide what to commit)

> **`0df` — A salvage agent given a "no local working-tree manipulation" rule will still `git checkout` a PR branch if its prompt mentions cherry-picking commits without a clear `--no-checkout` / clone-elsewhere directive.** The agent in Item 4A interpreted "create a salvage branch from origin/main" as licence to switch the local repo. Untracked-only documents (`docs/plans/`, `docs/reviews/`) are destroyed in that switch. Mitigation: brief salvage agents to do all branch work in a `git clone` under `/tmp/`, never in the working repo, and always commit important documents before dispatching them.
