# Task: Create .shellcheckrc for Project-Wide Exclusions

- [x] Create `.shellcheckrc` at the repository root.
- [x] Disable `SC1091` globally with a comment explaining it's for dynamic sourcing.
- [x] Add a commented-out exclusion for `SC2034` with an explanation that unused variables should be reviewed per-instance.
- [ ] Examine Trunk CI configuration (`.trunk/trunk.yaml` and `.trunk/configs/.shellcheckrc`) to understand and document how it interacts with the repo-root `.shellcheckrc`.
- [x] Verify configuration works natively.
- [x] Run test suite to verify no regressions.
- [x] Ensure pre-commit checks and reviews are complete.
- [x] Submit pull request.

---

## Archived tasks from Session 3 (PR #424 test plan)

These items were previously tracked in `tasks/todo.md` under **Session 3** and are preserved here for audit/history. See `tasks/pr-review-2026-02-*.md` for full context and current status.

- [ ] Resolve permission escalation for ctrld-sync and email-security-pipeline
- [ ] Execute close queue (10 PRs)
- [ ] Execute merge queue (12 PRs)
- [ ] Handle MERGE-AFTER-FIX PRs (#381, #407, #375)
- [ ] Resolve escalations (#404, #396, #376)
- [ ] Rebase #385
- [ ] Post-merge conflict cascade check
