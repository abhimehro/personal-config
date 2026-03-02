# Task: Create .shellcheckrc for Project-Wide Exclusions

- [x] Create `.shellcheckrc` at the repository root.
- [x] Disable `SC1091` globally with a comment explaining it's for dynamic sourcing.
- [x] Add a commented-out exclusion for `SC2034` with an explanation that unused variables should be reviewed per-instance.
- [ ] Examine Trunk CI configuration (`.trunk/trunk.yaml` and `.trunk/configs/.shellcheckrc`) to understand and document how it interacts with the repo-root `.shellcheckrc`.
- [x] Verify configuration works natively.
- [x] Run test suite to verify no regressions.
- [x] Ensure pre-commit checks and reviews are complete.
- [x] Submit pull request.
