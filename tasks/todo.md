# Automated PR Review Session Plan (2026-02-26)

- [x] Discover in-scope repositories and list open bot-authored PRs.
- [x] Build `tasks/pr-inventory.md` with required inventory columns for every bot PR.
- [x] Collect per-PR details (CI state, changed files/lines, comment threads, conflict status, age).
- [x] Classify each PR into one category: SECURITY, DEPENDENCY, PERFORMANCE, UI, REFACTOR, FEATURE, CI/INFRA.
- [x] Detect exact/semantic duplicates and superseded/stale candidates; write findings to `tasks/pr-triage.md`.
- [x] Apply review gates on surviving PRs and decide disposition: MERGE / MERGE-AFTER-FIX / REQUEST-CHANGES / ESCALATE / CLOSE-DUPLICATE / CLOSE-STALE / CONSOLIDATE.
- [x] Execute safe GitHub actions on in-scope bot PRs (comments, closes, merges where gates pass). *(partial: close/comment/review blocked by integration permissions)*
- [x] Produce session report in `tasks/pr-review-2026-02-26.md`.
- [x] Update `tasks/lessons.md` with recurring bot patterns and process improvements.

## Follow-up Plan (2026-02-26)

- [x] Confirm and document exact permission blockers encountered per repository.
- [x] Draft a reusable GitHub App permission checklist for multi-repo PR automation.
- [x] Implement a fail-fast preflight script that validates auth, repo access, PR visibility, and effective action capabilities before triage starts.
- [x] Run the preflight script against current repos in read-only mode and capture example output.
- [x] Commit and push the new checklist + script + plan updates.
