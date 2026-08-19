# Cursor Dashboard Application Checklist

The checked-in prompt files and exports are the reviewed source of truth. Cursor Dashboard is a separately applied runtime copy and can drift. Apply one export at a time, paste the named prompt verbatim, and record the applied dashboard fingerprint in the next Stage 1, 2, or 3 ledger event.

| Stage | Export | Prompt to paste | Schedule | Dashboard authority | MCP/action allowlist | Memory |
|---|---|---|---|---|---|---|
| Stage 1 | `exports/daily-pr-review.json` | `prompts/daily-pr-review.md` | `0 13 * * *` | `prComment.allowApprove: true`; routine only | GitKraken repository connector and approval action only | Disabled |
| Stage 2 | `exports/daily-pr-salvage.json` | `prompts/daily-pr-salvage.md` | `0 17 * * *` | No approval, reviewer request, merge, or close | GitKraken repository connector only, new draft branches/PRs only | Disabled |
| Stage 3 calibration | `exports/daily-pr-completion.calibration.json` | `prompts/daily-pr-completion.calibration.md` | `15 21 * * *` | Report-only, no GitHub mutation | GitKraken repository connector only, ledger/run-record writes only | Disabled |
| Stage 3 completion | `exports/daily-pr-completion.json` | `prompts/daily-pr-completion.md` | `15 21 * * *` | `prComment.allowApprove: true`; bounded completion only | GitKraken repository connector and approval action only | Disabled |

All schedules are **UTC**. In America/Chicago, the displayed local hour changes with daylight-saving time. The shared environment ID is `8fa8ebdc-09a7-484a-a3a8-766347b3ac19`, model is `cursor-grok-4.6-high`, and scope is private.

Do not attach Browser, Browser-use, Playwright, desktop commander, AppleScript, email, drive, calendar, Rube, Firebase, Cloudflare, Clerk, `requestReviewers`, or a general shell tool to any stage. Do not attach a generic commenting action to Stage 3 calibration. Enable the completion export only after a human records `calibration.status: APPROVED` with the current policy revision and evidence. Roll back by disabling the completion automation, setting calibration to `REVOKED`, recording the reason, and returning to the calibration export.
