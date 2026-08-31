# Cursor Dashboard Application Checklist

The live Cursor Dashboard is canonical for trigger, enablement, model, memory,
and connected-tool state. The checked-in prompt files and exports are reconciled
records, not instructions to overwrite a verified live setting. The authorized
`automation/pr-lifecycle-ledger` branch is active with the recorded Contents API
compare-and-swap primitive. Apply a changed export only after confirming the
Dashboard value it represents, then record the dashboard fingerprint in the next
runtime-ledger event.

| Stage               | Export                                         | Prompt to paste                              | Schedule     | Dashboard authority                                     | MCP/action allowlist                                               | Memory                   |
| ------------------- | ---------------------------------------------- | -------------------------------------------- | ------------ | ------------------------------------------------------- | ------------------------------------------------------------------ | ------------------------ |
| Stage 1             | `exports/daily-pr-review.json`                 | `prompts/daily-pr-review.md`                 | `0 15 * * *` | `prComment.allowApprove: true`; routine only            | Dashboard-referenced MCP set; prompt and routine predicates govern | Enabled namespaced cache |
| Stage 2             | `exports/daily-pr-salvage.json`                | `prompts/daily-pr-salvage.md`                | `0 17 * * *` | No approval, reviewer request, merge, or close          | Dashboard-referenced MCP set; draft-only contract governs          | Enabled namespaced cache |
| Stage 3 calibration | `exports/daily-pr-completion.calibration.json` | `prompts/daily-pr-completion.calibration.md` | `0 19 * * *` | Report-only, no GitHub mutation                         | Dashboard-referenced MCP set; report-only prohibitions govern      | Enabled namespaced cache |
| Stage 3 completion  | `exports/daily-pr-completion.json`             | `prompts/daily-pr-completion.md`             | `0 19 * * *` | `prComment.allowApprove: true`; bounded completion only | Dashboard-referenced MCP set; approval gate and cap govern         | Enabled namespaced cache |

All schedules are **UTC**. In America/Chicago, the displayed local hour changes
with daylight-saving time. The shared environment ID is
`8fa8ebdc-09a7-484a-a3a8-766347b3ac19`, model is `cursor-grok-4.6-high`, and
scope is private.

The Dashboard-referenced MCP set is role-based in each stage prompt (`gh` is
required; GitHub MCP is a same-token fallback). Stage 1 names codescene,
Sonatype-mcp, and Snyk as needed for merge gates. Stage 2 names draft `gh`,
codescene, Context7, and Sonatype pins. Stage 3 names read-only `gh`, Notion
packets, and scanners as hold evidence. The Dashboard may still expose Notion,
Memory, Sequential thinking, GitKraken, cloudrun, Linear, codescene,
julesServer, Snyk, Sonatype-mcp, and a broader catalog. Neither the visible
catalog nor a connected integration changes a stage's explicit authority,
report-only rule, mutation cap, or security boundary. `concurrency: 1` is an
operating requirement documented in source artifacts, not a Cursor Dashboard
enforcement primitive.

Agent-facing session docs share one `pr-lifecycle-docs-YYYYMMDD` PR per UTC day
(lifecycle contract). Stage 3 still uses Notion only for one-question packets;
do not paste run records into Notion as git continuity. Grok Bot is not a
Dashboard automation; human-facing digest setup is
[`docs/grok-bot/README.md`](../grok-bot/README.md).

**HITL after this burndown PR lands (required or cron keeps the old
prompts and the 20-slot cap):**

1. Paste `prompts/daily-pr-review.md` into Stage 1 automation
   `77c168e0-7f6b-42de-bad6-da4e4e640b79` (80 inventory / 40 product mutations).
2. Paste `prompts/daily-pr-salvage.md` into Stage 2 automation
   `3e537981-04a6-456f-89a3-272d9d5fddd7`.
3. **Disable** Stage 3 calibration automation
   `d9d2c058-9c42-11f1-ba66-0e7d0216e441` (do not leave it enabled).
4. Paste `prompts/daily-pr-completion.md` into the Stage 3 **completion**
   automation and **enable** that automation on `0 19 * * *`. Confirm
   calibration cannot fire again. Record the completion automation UUID in the
   next ledger event if it is still missing from docs.
5. Record the new dashboard fingerprints in the next runtime-ledger event.
   Do **not** reset calibration to `REPORT_ONLY` for this volume change.

Monitor: `python3 scripts/pr_lifecycle_pipeline_health.py <fetched-ledger>`
(schema + runtime records; `stage2_work_item_count` is complete unexpired WIs;
owned items without a usable WI do not suppress starvation; exit 2 =
starvation). PR Desk Health must surface that line.

The two Stage 3 exports share `0 19 * * *` and are **mutually exclusive**. Never
leave both variants enabled. Calibration reached 7/7 on 2026-08-26; the
maintainer approved bounded completion. Completion is the live Stage 3 variant
once the ledger `calibration.status` is `APPROVED` and this paste is done.
