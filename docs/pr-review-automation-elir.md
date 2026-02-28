# PR Review Automation — ELIR Handoff

**Explain Like I'm Reviewing** — maintenance summary for the automated PR review system.

## Purpose

Reduce bot PR backlog across configured repositories by triaging, reviewing, merging the good, fixing the fixable, and closing duplicates/stale. Security and accuracy are top priorities. Only bot-authored PRs are in scope.

## Security

- **No merge** on security gate failure (secrets, eval/exec, permission escalation, CVE deps, weakened .gitignore).
- **No merge** on failing CI unless proven unrelated (e.g. flaky test).
- **No autonomous merge** of auth, payment, or database migration logic—human approval required.
- Token and permissions follow [GitHub App Permission Checklist](github-app-pr-automation-checklist.md). Preflight validates capabilities before any triage or write actions.

## Failure modes

| Condition | Consequence | Mitigation |
|-----------|-------------|------------|
| Preflight fails | Do not run triage or write actions | Fix auth/repo access/permissions; re-run preflight |
| Permissions missing on a repo | Merge/close/comment blocked on that repo | Grant write scope per checklist; run close/merge queues when ready |
| Conflicting PRs | Do not merge either | Flag for manual review; rebase or close as appropriate |
| Stale threshold exceeded + failing CI | Candidate for CLOSE-STALE | Close with comment; offer reopen after rebase |

## Review checklist (before accepting a session)

- [ ] Preflight completed successfully (read-only or write-probes as intended).
- [ ] Inventory written to `tasks/pr-inventory.md`; triage to `tasks/pr-triage.md`.
- [ ] Disposition per decision matrix (MERGE, CLOSE-*, ESCALATE, etc.).
- [ ] Escalations and ready-to-execute commands documented in session report and/or triage.

## Maintenance

- **After each session:** Update `tasks/lessons.md`; reflect material lessons in [Automated PR Review Agent](automated-pr-review-agent.md) heuristics subsection.
- **Permissions:** Keep checklist and preflight in sync with GitHub App permissions. If scope changes, run preflight with `--require-write-probes` and probe PRs to confirm.
- **After permission escalation:** Run close queue then merge queue in the order given in `tasks/pr-triage.md` ("Ready-to-Execute Human Actions"). Re-check mergeable state after each merge.

## Key files

| File | Role |
|------|------|
| `docs/automated-pr-review-agent.md` | Canonical agent spec (phases, gates, matrix) |
| `docs/github-app-pr-automation-checklist.md` | App permissions, preflight usage, runbook |
| `scripts/preflight-gh-pr-automation.sh` | Fail-fast auth/repo/PR/checks validation |
| `scripts/run-pr-review-session.sh` | Runs preflight; prints next steps |
| `tasks/pr-review-agent.config.yaml` | Repos, bot authors, thresholds |
| `tasks/pr-inventory.md` | Current session inventory (table) |
| `tasks/pr-triage.md` | Duplicates, conflicts, ready-to-execute commands |
| `tasks/pr-review-YYYY-MM-DD.md` | Session report |
| `tasks/lessons.md` | Recurring patterns and process improvements |
