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

## Live Dashboard IDs (verified 2026-09-16)

Paste targets are **UUID automations**. Agent run URLs (`bc-*`, e.g.
`https://cursor.com/agents/bc-…`) are session evidence only — never paste
prompts into a `bc-*` URL and never treat a cloud-agent session id as an
automation id.

| Stage               | Automation ID                          | Enablement (2026-09-16) | Schedule                     |
| ------------------- | -------------------------------------- | ----------------------- | ---------------------------- |
| Stage 1             | `77c168e0-7f6b-42de-bad6-da4e4e640b79` | **disabled**            | `0 15 * * *` UTC             |
| Stage 2             | `3e537981-04a6-456f-89a3-272d9d5fddd7` | **disabled**            | `0 17 * * *` UTC             |
| Stage 3 calibration | `d9d2c058-9c42-11f1-ba66-0e7d0216e441` | **disabled**            | do not enable                |
| Stage 3 completion  | `66a8e7a8-9c42-11f1-ba66-0e7d0216e441` | **disabled**            | `0 19 * * *` UTC / 12:00 PDT |

These four UUIDs are the only paste targets. Disable any orphan duplicate
automation that is not in this table. Leave calibration permanently disabled
while completion exists.

### Fail-closed enablement rule

After a Stage 1 **FAIL** feed (`stage2_queued_count: 0` while
`salvage_eligible_count > 0`, or health-monitor `starvation=true`):

1. Keep Stage 2 and Stage 3 completion **disabled**.
2. Re-enable Stage 1 only to paste the updated prompt and run a sample that
   CAS-writes ≥1 complete `stage2_work_item`.
3. Re-enable Stage 2 only after that sample WI exists and health reports
   `starvation=false` (or eligible drained).
4. Re-enable Stage 3 completion only after Stage 2 has claimed a WI without
   `FEED_FAIL` theater on the same UTC day.

Do not re-enable Stage 2/3 while Stage 1 still queues 0 WIs and dumps remainder
to Stage 3.

**HITL paste after this cascade PR lands:**

1. Paste `prompts/daily-pr-review.md` into Stage 1
   `77c168e0-7f6b-42de-bad6-da4e4e640b79` (feed fingerprint + salvage feed).
2. Paste `prompts/daily-pr-salvage.md` into Stage 2
   `3e537981-04a6-456f-89a3-272d9d5fddd7` (FEED_FAIL short-circuit).
3. Leave calibration `d9d2c058-9c42-11f1-ba66-0e7d0216e441` **disabled**.
4. Paste `prompts/daily-pr-completion.md` into Stage 3 completion
   `66a8e7a8-9c42-11f1-ba66-0e7d0216e441` (upstream-feed pause). Keep it
   **disabled** until the sample handoff proves green.
5. Record the new dashboard fingerprints in the next runtime-ledger event. Do
   **not** reset calibration to `REPORT_ONLY` for this change.

## Health monitor (requires a fetched ledger)

Homebrew / PEP 668 Python: use a venv. Do **not** `--break-system-packages`.
The monitor reads a **file path**; `/tmp/pr-lifecycle-ledger.yaml` does not exist
until you fetch it.

```bash
cd ~/dev/personal-config
python3 -m venv .venv
source .venv/bin/activate          # fish: source .venv/bin/activate.fish
python -m pip install -r requirements.txt
gh api "repos/abhimehro/personal-config/contents/pr-lifecycle-ledger.yaml?ref=automation/pr-lifecycle-ledger" \
  -H "Accept: application/vnd.github.raw+json" > /tmp/pr-lifecycle-ledger.yaml
python scripts/pr_lifecycle_pipeline_health.py /tmp/pr-lifecycle-ledger.yaml
```

(`stage2_work_item_count` is complete unexpired WIs; empty required strings and
owned items without a usable WI do not suppress starvation; exit 2 =
starvation). PR Desk Health must surface that line. Local verify without cron:
`python scripts/pr_lifecycle_feed_cascade_verify.py --ledger /tmp/pr-lifecycle-ledger.yaml`.

The two Stage 3 exports share `0 19 * * *` and are **mutually exclusive**. Never
leave both variants enabled. Calibration reached 7/7 on 2026-08-26; the
maintainer approved bounded completion. Completion is the live Stage 3 variant
once the ledger `calibration.status` is `APPROVED` and this paste is done —
subject to the fail-closed enablement rule above.
