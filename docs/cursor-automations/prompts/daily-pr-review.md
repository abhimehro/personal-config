# Daily PR Review (Stage 1) — bootstrap

Calibration stays **DISABLED**. Do not merge REVIEW_SECURITY / HUMAN sticky without a Desk exception.

1. Read `docs/automated-pr-lifecycle.md`, `REVIEW.md` (bot-thread advisory policy), and `tasks/lessons.md` (0hr).
2. Run: `python3 scripts/pr_lifecycle_run.py --stage 1 --dry-run`
3. Execute **only** the emitted plan / allowed commands. Prefer `python3 scripts/pr_lifecycle_reconcile.py --json` before mutations.
4. Schema-aware CAS only via `pr_lifecycle_ledger_cas` / ledger helpers — never raw YAML string replace.
5. Queue Stage 2 intake with `python3 scripts/pr_lifecycle_feed.py --json` when salvage-eligible stock exists.
6. Append the run record from the emitted plan. Update status with `python3 scripts/pr_lifecycle_run.py --status` if asked.
7. No force-push. Trunk for personal-config; squash elsewhere. Desk does not merge/approve/close from chat.
