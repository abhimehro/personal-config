# Cursor Dashboard Application Checklist

The checked-in prompt files and exports are the reviewed source of truth. Cursor
Dashboard is a separately applied runtime copy and can drift. Do not apply a
ledger-read-required export until the separately authorized
`automation/pr-lifecycle-ledger` data branch is bootstrapped and a selected
runtime write primitive has completed a validated read/write round trip. Apply
one export at a time, paste the named prompt verbatim, and record the applied
dashboard fingerprint in the next runtime-ledger event.

| Stage               | Export                                         | Prompt to paste                              | Schedule      | Dashboard authority                                     | MCP/action allowlist                                               | Memory   |
| ------------------- | ---------------------------------------------- | -------------------------------------------- | ------------- | ------------------------------------------------------- | ------------------------------------------------------------------ | -------- |
| Stage 1             | `exports/daily-pr-review.json`                 | `prompts/daily-pr-review.md`                 | `0 13 * * *`  | `prComment.allowApprove: true`; routine only            | GitKraken repository connector and approval action only            | Disabled |
| Stage 2             | `exports/daily-pr-salvage.json`                | `prompts/daily-pr-salvage.md`                | `0 17 * * *`  | No approval, reviewer request, merge, or close          | GitKraken repository connector only, new draft branches/PRs only   | Disabled |
| Stage 3 calibration | `exports/daily-pr-completion.calibration.json` | `prompts/daily-pr-completion.calibration.md` | `15 21 * * *` | Report-only, no GitHub mutation                         | GitKraken repository connector only, ledger/run-record writes only | Disabled |
| Stage 3 completion  | `exports/daily-pr-completion.json`             | `prompts/daily-pr-completion.md`             | `15 21 * * *` | `prComment.allowApprove: true`; bounded completion only | GitKraken repository connector and approval action only            | Disabled |

All schedules are **UTC**. In America/Chicago, the displayed local hour changes
with daylight-saving time. The shared environment ID is
`8fa8ebdc-09a7-484a-a3a8-766347b3ac19`, model is `cursor-grok-4.6-high`, and
scope is private.

Do not attach Browser, Browser-use, Playwright, desktop commander, AppleScript,
email, drive, calendar, Rube, Firebase, Cloudflare, Clerk, `requestReviewers`,
or a general shell tool to any stage. Do not attach a generic commenting action
to Stage 3 calibration. `concurrency: 1` is an operating requirement documented
in source artifacts, not a Cursor Dashboard enforcement primitive.

The two Stage 3 exports share `15 21 * * *` and are **mutually exclusive**.
Before enabling completion, disable or delete the calibration automation, verify
it cannot run again, and record its dashboard fingerprint, disable/delete time,
and the new completion fingerprint in the runtime ledger. Only then may the
human-approved completion export be enabled. The inverse rollback is equally
strict: disable completion first, set calibration to `REVOKED` through the
runtime ledger, record the reason and fingerprint, then create or re-enable the
report-only calibration variant. Never leave both variants enabled.
