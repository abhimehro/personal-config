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

The two Stage 3 exports share `0 19 * * *` and are **mutually exclusive**.
Before enabling completion, disable or delete the calibration automation, verify
it cannot run again, and record its dashboard fingerprint, disable/delete time,
and the new completion fingerprint in the runtime ledger. Only then may the
human-approved completion export be enabled. The inverse rollback is equally
strict: disable completion first, set calibration to `REVOKED` through the
runtime ledger, record the reason and fingerprint, then create or re-enable the
report-only calibration variant. Never leave both variants enabled. Both Stage 3
variants are currently disabled for the maintainer's controlled manual test.
