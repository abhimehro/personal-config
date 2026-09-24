# Daily PR Completion (Stage 3) — bootstrap

Completion is **live Stage 3** (not calibration). Calibration stays **DISABLED**. Re-read predicates before every merge/close.

1. Read `docs/automated-pr-lifecycle.md`, `REVIEW.md` bot-thread policy (2026-09-21), and lessons 0hr.
2. Run: `python3 scripts/pr_lifecycle_run.py --stage 3 --dry-run`
3. Execute **only** the emitted plan / allowed commands.
4. **Bot-thread advisory (Abhi 2026-09-21):** Codacy / qodo / CodeRabbit threads with no human reply are advisory; Stage 3 may resolve them with a standard comment before `/trunk`.
5. Never merge REVIEW_SECURITY / HUMAN sticky without Desk exception. Builder ≠ merger.
6. Schema-aware CAS only via ledger helpers. Prefer reconcile dry-run before applying terminals.
7. Append the run record. No force-push. Trunk for personal-config; squash elsewhere.
