# Daily PR Salvage (Stage 2) — bootstrap

Stage 2 **never merges**. Builder ≠ merger. Calibration stays **DISABLED**.

1. Read `docs/automated-pr-lifecycle.md` and the Stage 2 agent doc.
2. Run: `python3 scripts/pr_lifecycle_run.py --stage 2 --dry-run`
3. Execute **only** the emitted plan. Start from `python3 scripts/pr_lifecycle_feed.py --json`.
4. If feed is empty AND eligible stock remains, treat as `EMPTY_FEED_WITH_ELIGIBLE_STOCK` / LOGIC_STOP — heal-forward, do not invent merges.
5. Expired-packet BOT non-REVIEW_SECURITY items are salvage-eligible **or** CLOSE_STALE (Stage 1/3). Prefer focused draft recovery within allowed paths.
6. Minimal WI intake: source key, SHAs, paths, reason. Heavy fields are Stage 2 outputs.
7. Schema-aware CAS only. Append the run record. No force-push.
