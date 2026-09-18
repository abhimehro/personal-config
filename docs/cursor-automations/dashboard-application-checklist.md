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
| Stage 1             | `exports/daily-pr-review.json`                 | expanded JSON `prompts[0].prompt`            | `0 15 * * *` | `prComment.allowApprove: true`; routine only            | Dashboard-referenced MCP set; prompt and routine predicates govern | Enabled namespaced cache |
| Stage 2             | `exports/daily-pr-salvage.json`                | expanded JSON `prompts[0].prompt`            | `0 17 * * *` | No approval, reviewer request, merge, or close          | Dashboard-referenced MCP set; draft-only contract governs          | Enabled namespaced cache |
| Stage 3 calibration | `exports/daily-pr-completion.calibration.json` | `prompts/daily-pr-completion.calibration.md` | `0 19 * * *` | Report-only, no GitHub mutation                         | Dashboard-referenced MCP set; report-only prohibitions govern      | Enabled namespaced cache |
| Stage 3 completion  | `exports/daily-pr-completion.json`             | expanded JSON `prompts[0].prompt`            | `0 19 * * *` | `prComment.allowApprove: true`; bounded completion only | Dashboard-referenced MCP set; approval gate and cap govern         | Enabled namespaced cache |

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

## Live Dashboard IDs (verified 2026-09-18)

Paste targets are **UUID automations**. Agent run URLs (`bc-*`, e.g.
`https://cursor.com/agents/bc-…`) are session evidence only — never paste
prompts into a `bc-*` URL and never treat a cloud-agent session id as an
automation id.

| Stage               | Automation ID                          | Enablement (live GetAutomation) | Schedule                     |
| ------------------- | -------------------------------------- | ------------------------------- | ---------------------------- |
| Stage 1             | `77c168e0-7f6b-42de-bad6-da4e4e640b79` | **enabled**                     | `0 15 * * *` UTC             |
| Stage 2             | `3e537981-04a6-456f-89a3-272d9d5fddd7` | **enabled**                     | `0 17 * * *` UTC             |
| Stage 3 calibration | `d9d2c058-9c42-11f1-ba66-0e7d0216e441` | **disabled**                    | do not enable                |
| Stage 3 completion  | `66a8e7a8-9c42-11f1-ba66-0e7d0216e441` | **enabled**                     | `0 19 * * *` UTC / 12:00 PDT |

These four UUIDs are the only paste targets. Disable any orphan duplicate
automation that is not in this table. Leave calibration permanently disabled
while completion exists. Do **not** disable Stage 1 so Stage 2 can take over:
Stage 2 is an independent `0 17 * * *` UTC cron (lesson **0hk**).

A 2026-09-16 snapshot of this table listed all four as **disabled**. That
column is historical and must not be applied. Live GetAutomation on
2026-09-18 is Stage 1/2/3 completion **enabled**, calibration **disabled**.
Follow this table and the heal-forward section, not the dated disabled
column.

### Heal-forward enablement rule

After a Stage 1 **FAIL** feed (`stage2_queued_count: 0` while
`salvage_eligible_count > 0`, or health-monitor `starvation=true`):

1. Keep Stage 1, Stage 2, and Stage 3 completion **enabled**.
2. The next stage **heals leftover work** (`HEAL_THEN_PROCEED`): queue complete
   `stage2_work_item`s, repair wrap-only export drift, then continue its own
   job. Do not wait for a human to disable/enable crons.
3. Empty intake with zero salvage-eligible remainder is the only short stop.
4. A queued sample WI alone does not clear a FAIL grade or active starvation;
   healing must produce a real feed or leftover Stage 1 drain.
5. Shared ownership: each stage is a **security-first / security-focused
   development partner** (Copilot Development Partner profile, `AGENTS.md`,
   `REVIEW.md`, `.cursorrules`). Apply those files; citing them is not
   enough. A growing backlog is a failed run, not a reason to stop. Doing
   no work is a failed run. Do not claim problems resolved and then leave.

Do not disable Stage 1 so Stage 2 can “take over”; Stage 2 is an independent
`0 17 * * *` UTC cron. Do not disable Stage 2/3 while Stage 1 still queues
0 WIs; that is the condition that requires heal-forward, not a pause.

**HITL paste after this cascade PR lands:**

Paste the **expanded** JSON `prompts[0].prompt` field from each export —
never paste markdown that still contains `{{include:...}}`. Sibling
includes (`_shared-cas-bootstrap.md`, `_shared-partner-frame.md`) are
already expanded in the JSON. The four UUIDs below are unchanged; do
not create a fifth automation.

1. Paste `exports/daily-pr-review.json` `prompts[0].prompt` into Stage 1
   `77c168e0-7f6b-42de-bad6-da4e4e640b79` (shared ownership + fingerprint).
2. Paste `exports/daily-pr-salvage.json` `prompts[0].prompt` into Stage 2
   `3e537981-04a6-456f-89a3-272d9d5fddd7`
   (shared ownership + HEAL_THEN_PROCEED).
3. Leave calibration `d9d2c058-9c42-11f1-ba66-0e7d0216e441` **disabled**.
4. Paste `exports/daily-pr-completion.json` `prompts[0].prompt` into Stage 3
   completion `66a8e7a8-9c42-11f1-ba66-0e7d0216e441` (shared ownership +
   leftover drain). Keep it **enabled**.
5. Record the new dashboard fingerprints in the next runtime-ledger event. Do
   **not** reset calibration to `REPORT_ONLY` for this change.

## Health monitor (requires a fetched ledger)

Homebrew / PEP 668 Python: use a venv. Do **not** `--break-system-packages`. The
monitor reads a **file path**; `/tmp/pr-lifecycle-ledger.yaml` does not exist
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
