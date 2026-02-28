# Automated PR Review Session Plan

## Session 1 (2026-02-26)

- [x] Discover in-scope repositories and list open bot-authored PRs.
- [x] Build `tasks/pr-inventory.md` with required inventory columns for every bot PR.
- [x] Collect per-PR details (CI state, changed files/lines, comment threads, conflict status, age).
- [x] Classify each PR into one category: SECURITY, DEPENDENCY, PERFORMANCE, UI, REFACTOR, FEATURE, CI/INFRA.
- [x] Detect exact/semantic duplicates and superseded/stale candidates; write findings to `tasks/pr-triage.md`.
- [x] Apply review gates on surviving PRs and decide disposition.
- [x] Execute safe GitHub actions on in-scope bot PRs (partial: close/comment/review blocked by permissions).
- [x] Produce session report in `tasks/pr-review-2026-02-26.md`.
- [x] Update `tasks/lessons.md` with recurring bot patterns and process improvements.

## Session 1 Follow-up (2026-02-26)

- [x] Confirm and document exact permission blockers encountered per repository.
- [x] Draft a reusable GitHub App permission checklist for multi-repo PR automation.
- [x] Implement a fail-fast preflight script that validates auth, repo access, PR visibility, and effective action capabilities before triage starts.
- [x] Run the preflight script against current repos in read-only mode and capture example output.
- [x] Commit and push the new checklist + script + plan updates.

## Session 2 (2026-02-27)

- [x] Re-inventory all open bot PRs across 3 repos (fresh snapshot).
- [x] Merge zero-diff superseded PRs in personal-config (#379, #387, #383, #382, #380).
- [x] Review and merge substantive PRs in personal-config (#381 unused vars, #384 shared libs).
- [x] Deep-review all 14 ctrld-sync bot PRs with per-PR gate evaluation.
- [x] Deep-review all 14 email-security-pipeline bot PRs with per-PR gate evaluation.
- [x] Identify duplicate groups, superseded PRs, and merge ordering across repos.
- [x] Confirm permission constraints (merge-only on personal-config, read-only elsewhere).
- [x] Produce ready-to-execute `gh` commands for human-assisted close/merge queue.
- [x] Write session report in `tasks/pr-review-2026-02-27.md`.
- [x] Update `tasks/lessons.md` with session 2 findings.
- [x] Commit and push all artifacts.

## Session 3 (Next)

**Runbook:** See `docs/github-app-pr-automation-checklist.md` §8 (Session 3 Runbook): grant permissions → preflight with write probes → close queue → merge queue in order → re-check conflicts after each merge.

- [ ] Resolve permission escalation: grant integration write access to ctrld-sync and email-security-pipeline.
- [ ] Execute close queue (10 PRs across 2 repos) using elevated permissions.
- [ ] Execute merge queue (12 PRs across 2 repos) in recommended order.
- [ ] Handle MERGE-AFTER-FIX PRs: rebase #381, strip lockfile from #407, fix #375 CodeFactor nit.
- [ ] Resolve escalations: #404 (architectural decision), #396 (validator verification), #376 (test coverage).
- [ ] Rebase personal-config#385 and evaluate for merge.
- [ ] Post-merge conflict cascade check on all remaining approved PRs.
