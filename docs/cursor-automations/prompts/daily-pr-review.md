# Daily PR Review (Stage 1) — bootstrap

Calibration stays **DISABLED**. Do not merge REVIEW_SECURITY / HUMAN sticky without a Desk exception.

The ledger, run records, and lessons are the continuity plane. Memory is enabled
as a namespaced cache and cannot override the ledger, SHA anchors, or stage
authority. The Dashboard-referenced MCP set for this stage is `gh` plus
codescene, Sonatype, and Snyk as needed; connected-tool visibility grants no
extra authority.

1. Read `docs/automated-pr-lifecycle.md`, `docs/pr-lifecycle-runtime-ledger.md`, `REVIEW.md` (bot-thread advisory policy), and `tasks/lessons.md` (0hr).
2. Run: `python3 scripts/pr_lifecycle_run.py --stage 1 --dry-run` (plan includes live signals; `SIGNALS_DEGRADED` adds no signal-specific stop; other planner stops, including `FEED_CHECK_FAIL` from `FEED_CHECK`, still apply; executor live-verifies unique paths at CAS time).
3. Execute **only** the emitted plan / allowed commands. Prefer `python3 scripts/pr_lifecycle_reconcile.py --json` before mutations.
4. Schema-aware CAS only via `pr_lifecycle_ledger_cas` / ledger helpers — never raw YAML string replace.
5. **Stage 2 intake (Option 3):** When the plan emits `ENQUEUE_STAGE2_WI`, CAS-write up to **5** complete `stage2_work_items` for live CONFLICTING/DIRTY ledger-BOT (or title-BOT) with unique remaining. Reason `CONFLICTING_UNIQUE_RESELECT`. Soft sticky `shell_execution` only for Palette wrap on the path allowlist. Never invent whole-PR rebase. Never-touch unchanged: Seatek#692, ctrld#1206 CSPRNG, Hydro Sentinel twins, REVIEW_SECURITY/HUMAN sticky, real HOLD_PLATFORM. `python3 scripts/pr_lifecycle_feed.py --json` is **read-only verification**, not enqueue. `FEED_CHECK` grade **FAIL** when reselect candidates > 0 and enqueued == 0.
6. CLOSED_NOOP Observed-CLOSED ledger catch-up may run here as reconcile bookkeeping (or weekly) — do not leave it as Stage 3 daily theater.
7. Append the run record from the emitted plan. Update status with `python3 scripts/pr_lifecycle_run.py --status` if asked.
8. No force-push. Trunk for personal-config; squash elsewhere. Desk does not merge/approve/close from chat.
