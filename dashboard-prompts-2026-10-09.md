# Cursor Dashboard — automation prompts (post-#2460 / #2478)

Copy each prompt block verbatim into the matching automation's prompt field.
Files of record: `docs/cursor-automations/prompts/*.md` on `main` (Stage 1 file
gains the Octopus line when #2478 merges — it is included below).

| Automation | UUID | Cron (UTC) | State |
|---|---|---|---|
| Stage 1 — Daily PR Review | `77c168e0-7f6b-42de-bad6-da4e4e640b79` | `0 15 * * *` | enable first |
| Stage 2 — Daily PR Salvage | `3e537981-04a6-456f-89a3-272d9d5fddd7` | `0 17 * * *` | enable after ~1 day of Stage 1 |
| Stage 3 — Daily PR Completion | `66a8e7a8-9c42-11f1-ba66-0e7d0216e441` | `0 19 * * *` | enable last |
| Calibration | `d9d2c058-9c42-11f1-ba66-0e7d0216e441` | — | keep DISABLED |

---

## Stage 1 — Daily PR Review

```markdown
# Daily PR Review (Stage 1) — bootstrap

Calibration stays **DISABLED**. Do not merge REVIEW_SECURITY / HUMAN sticky without a Desk exception.

1. Read `docs/automated-pr-lifecycle.md`, `REVIEW.md` (bot-thread advisory policy), and `tasks/lessons.md` (0hr).
2. Run: `python3 scripts/pr_lifecycle_run.py --stage 1 --dry-run` (plan includes live signals; `SIGNALS_DEGRADED` adds no signal-specific stop; other planner stops, including `FEED_CHECK_FAIL` from `FEED_CHECK`, still apply; executor live-verifies unique paths at CAS time).
3. Execute **only** the emitted plan / allowed commands. Run `python3 scripts/pr_lifecycle_reconcile.py --apply --json` for closed-PR bookkeeping and open-PR ingestion, then `python3 scripts/pr_lifecycle_unblock.py --apply --json` for blocker routing and escalation refresh. `pr_lifecycle_unblock.py --apply` posts trigger comments through `gh` authenticated with `GH_TOKEN` (the owner's token); do not run it under a bot/app identity — Jules, CodeRabbit and CodeScene ignore bot-authored triggers.
4. Schema-aware CAS only via `pr_lifecycle_ledger_cas` / ledger helpers — never raw YAML string replace.
5. **Stage 2 intake (Option 3):** When the plan emits `ENQUEUE_STAGE2_WI`, CAS-write up to **5** complete `stage2_work_items` for live CONFLICTING/DIRTY ledger-BOT (or title-BOT) with unique remaining. Reason `CONFLICTING_UNIQUE_RESELECT`. Soft sticky `shell_execution` only for Palette wrap on the path allowlist. Never invent whole-PR rebase. Never-touch unchanged: Seatek#692, ctrld#1206 CSPRNG, Hydro Sentinel twins, REVIEW_SECURITY/HUMAN sticky, real HOLD_PLATFORM. `python3 scripts/pr_lifecycle_feed.py --json` is **read-only verification**, not enqueue. `FEED_CHECK` grade **FAIL** when reselect candidates > 0 and enqueued == 0.
6. Reconcile records observed-closed PRs directly as CLOSED_NOOP; do not defer them to Stage 3.
7. Open Octopus review findings (unresolved `octopus-review` threads) escalate to the repo decision issue via `pr_lifecycle_unblock.py --apply`; a PR with open findings is never routine-merge eligible — resolve the threads on the PR to clear the row.
8. Append the run record from the emitted plan. Update status with `python3 scripts/pr_lifecycle_run.py --status` if asked.
9. No force-push. Trunk for personal-config; squash elsewhere. Desk does not merge/approve/close from chat.
```

## Stage 2 — Daily PR Salvage

```markdown
# Daily PR Salvage (Stage 2) — bootstrap

Stage 2 **never merges**. Builder ≠ merger. Calibration stays **DISABLED**.

1. Read `docs/automated-pr-lifecycle.md` and the Stage 2 agent doc.
2. Run: `python3 scripts/pr_lifecycle_run.py --stage 2 --dry-run`
3. Execute **only** the emitted plan. Start from `python3 scripts/pr_lifecycle_feed.py --json`.
4. **Skip-if-empty (Option 3):** If the dry-run plan reports reason `EMPTY_INTAKE_SKIP` / action `SKIP_IF_EMPTY` (no usable mechanical WIs remain after never-touch filtering) → **exit success**; append the run record to the local log (`/tmp/pr-lifecycle/<run_id>.jsonl`); do not open/push a docs PR; do not launch further agents. Optional one-line status only.
5. If feed is empty AND eligible stock remains, treat as `EMPTY_FEED_WITH_ELIGIBLE_STOCK` / LOGIC_STOP — heal-forward, do not invent merges.
6. Expired-packet BOT non-REVIEW_SECURITY items are salvage-eligible **or** CLOSE_STALE (Stage 1/3). Prefer focused draft recovery within allowed paths. Hard never-touch (#692 / #1206 CSPRNG / Hydro Sentinel / REVIEW_SECURITY) stays report-only.
7. Minimal WI intake: source key, SHAs, paths, reason. Heavy fields are Stage 2 outputs.
8. Schema-aware CAS only. Append the run record. No force-push.
```

## Stage 3 — Daily PR Completion

```markdown
# Daily PR Completion (Stage 3) — bootstrap

Completion is **live Stage 3** (not calibration). Calibration stays **DISABLED**. Re-read predicates before every merge/close.

1. Read `docs/automated-pr-lifecycle.md`, `REVIEW.md` bot-thread policy (2026-09-21), and lessons 0hr.
2. Run: `python3 scripts/pr_lifecycle_run.py --stage 3 --dry-run` (plan includes live signals; `SIGNALS_DEGRADED` adds no signal-specific stop; other planner stops still apply; executor live-verifies unique paths at CAS time).
3. Execute **only** the emitted plan / allowed commands.
4. **Bot-thread advisory (Abhi 2026-09-21):** Codacy / qodo / CodeRabbit threads with no human reply are advisory; Stage 3 may resolve them with a standard comment before `/trunk`.
5. Never merge REVIEW_SECURITY / HUMAN sticky without Desk exception. Builder ≠ merger.
6. **Option 3 handoff:** Stage-3-owned `STAGE3_RECONCILIATION` items that pass the reselect selector (live `CONFLICTING`/`DIRTY`, BOT-or-allowlisted title, salvage outcome `HOLD_CONTRACT`/`HOLD_EVIDENCE`/`NOT_RUN`, unique remaining paths) and can form a **complete** Stage 2 WI (repository/pr/base_sha/head_sha/allowed_paths) → `HANDOFF_MECHANICAL_TO_STAGE2` (owner stage2). Items missing fields stay stage3-owned for evidence gathering — do not emit a handoff for them. Do **not** spend the reconciliation cap on CLOSED_NOOP Observed-CLOSED when Stage 1 bookkeeping / weekly can take them (`CLOSED_NOOP_DEFERRED`).
7. Schema-aware CAS only via ledger helpers. Prefer reconcile dry-run before applying terminals.
8. Append the run record. No force-push. Trunk for personal-config; squash elsewhere.
```
