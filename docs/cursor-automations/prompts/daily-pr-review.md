# Daily PR Review (Stage 1) — bootstrap

Calibration stays **DISABLED**. Do not merge REVIEW_SECURITY / HUMAN sticky without a Desk exception.

1. Read `docs/automated-pr-lifecycle.md`, `REVIEW.md` (bot-thread advisory policy), and `tasks/lessons.md` (0hr).
2. Run: `python3 scripts/pr_lifecycle_run.py --stage 1 --dry-run` (plan includes live signals; `SIGNALS_DEGRADED` adds no signal-specific stop; other planner stops, including `FEED_CHECK_FAIL` from `FEED_CHECK`, still apply; executor live-verifies unique paths at CAS time).
3. Execute **only** the emitted plan / allowed commands. Run `python3 scripts/pr_lifecycle_reconcile.py --apply --json` for closed-PR bookkeeping and open-PR ingestion, then `python3 scripts/pr_lifecycle_unblock.py --apply --json` for blocker routing and escalation refresh.
4. Schema-aware CAS only via `pr_lifecycle_ledger_cas` / ledger helpers — never raw YAML string replace.
5. **Stage 2 intake (Option 3):** When the plan emits `ENQUEUE_STAGE2_WI`, CAS-write up to **5** complete `stage2_work_items` for live CONFLICTING/DIRTY ledger-BOT (or title-BOT) with unique remaining. Reason `CONFLICTING_UNIQUE_RESELECT`. Soft sticky `shell_execution` only for Palette wrap on the path allowlist. Never invent whole-PR rebase. Never-touch unchanged: Seatek#692, ctrld#1206 CSPRNG, Hydro Sentinel twins, REVIEW_SECURITY/HUMAN sticky, real HOLD_PLATFORM. `python3 scripts/pr_lifecycle_feed.py --json` is **read-only verification**, not enqueue. `FEED_CHECK` grade **FAIL** when reselect candidates > 0 and enqueued == 0.
6. Reconcile records observed-closed PRs directly as CLOSED_NOOP; do not defer them to Stage 3.
7. Append the run record from the emitted plan. Update status with `python3 scripts/pr_lifecycle_run.py --status` if asked.
8. No force-push. Trunk for personal-config; squash elsewhere. Desk does not merge/approve/close from chat.
