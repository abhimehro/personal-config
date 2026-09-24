# Daily PR Salvage (Stage 2) — bootstrap

Stage 2 **never merges**. Builder ≠ merger. Calibration stays **DISABLED**.

1. Read `docs/automated-pr-lifecycle.md` and the Stage 2 agent doc.
2. Run: `python3 scripts/pr_lifecycle_run.py --stage 2 --dry-run`
3. Execute **only** the emitted plan. Start from `python3 scripts/pr_lifecycle_feed.py --json`.
4. **Skip-if-empty (Option 3):** If the dry-run plan reports reason `EMPTY_INTAKE_SKIP` / action `SKIP_IF_EMPTY` (no usable mechanical WIs remain after never-touch filtering) → **exit success**; do not open/push a docs PR; do not launch further agents. Optional one-line status only.
5. If feed is empty AND eligible stock remains, treat as `EMPTY_FEED_WITH_ELIGIBLE_STOCK` / LOGIC_STOP — heal-forward, do not invent merges.
6. Expired-packet BOT non-REVIEW_SECURITY items are salvage-eligible **or** CLOSE_STALE (Stage 1/3). Prefer focused draft recovery within allowed paths. Hard never-touch (#692 / #1206 CSPRNG / Hydro Sentinel / REVIEW_SECURITY) stays report-only.
7. Minimal WI intake: source key, SHAs, paths, reason. Heavy fields are Stage 2 outputs.
8. Schema-aware CAS only. Append the run record. No force-push.
