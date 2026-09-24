# Daily PR Completion (Stage 3) — bootstrap

Completion is **live Stage 3** (not calibration). Calibration stays **DISABLED**. Re-read predicates before every merge/close.

1. Read `docs/automated-pr-lifecycle.md`, `REVIEW.md` bot-thread policy (2026-09-21), and lessons 0hr.
2. Run: `python3 scripts/pr_lifecycle_run.py --stage 3 --dry-run`
3. Execute **only** the emitted plan / allowed commands.
4. **Bot-thread advisory (Abhi 2026-09-21):** Codacy / qodo / CodeRabbit threads with no human reply are advisory; Stage 3 may resolve them with a standard comment before `/trunk`.
5. Never merge REVIEW_SECURITY / HUMAN sticky without Desk exception. Builder ≠ merger.
6. **Option 3 handoff:** Stage-3-owned `STAGE3_RECONCILIATION` items that pass the reselect selector (live `CONFLICTING`/`DIRTY`, BOT-or-allowlisted title, salvage outcome `HOLD_CONTRACT`/`HOLD_EVIDENCE`/`NOT_RUN`, unique remaining paths) and can form a **complete** Stage 2 WI (repository/pr/base_sha/head_sha/allowed_paths) → `HANDOFF_MECHANICAL_TO_STAGE2` (owner stage2). Items missing fields stay stage3-owned for evidence gathering — do not emit a handoff for them. Do **not** spend the reconciliation cap on CLOSED_NOOP Observed-CLOSED when Stage 1 bookkeeping / weekly can take them (`CLOSED_NOOP_DEFERRED`).
7. Schema-aware CAS only via ledger helpers. Prefer reconcile dry-run before applying terminals.
8. Append the run record. No force-push. Trunk for personal-config; squash elsewhere.
