# Cursor Automations: Weekly Repository Health & Housekeeping

**Type:** Recurring scheduled Cursor Automations (Option A)\
**Dashboard:** https://cursor.com/automations\
**Docs:** https://cursor.com/docs/cloud-agent/automations\
**Environment:**
[Abhi’s 🐝 Dev Cloud Workspace](https://cursor.com/dashboard/cloud-agents/environments/e/8fa8ebdc-09a7-484a-a3a8-766347b3ac19)
(all seven active repos)

These two automations fill the gap left by daily security + PR review/salvage.
They intentionally **do not** duplicate:

- automated-pr-review
- automate-pr-salvage
- daily security / repo-health-triage

## Create two automations (do this once)

Create **two separate** automations. Do not convert an existing daily automation
to weekly (known Cursor bug: schedule edits from daily→weekly can keep firing
daily). Start each as a fresh weekly schedule.

### Shared settings

| Setting                 | Value                                                          |
| ----------------------- | -------------------------------------------------------------- |
| Trigger                 | Scheduled (cron)                                               |
| Repositories            | **Multi-repo environment** → Abhi’s Dev Cloud Workspace        |
| Model                   | Your preferred capable model (automations always run Max Mode) |
| Memories                | **On** (cross-run prioritization)                              |
| Pull request creation   | **On** (draft PRs for mechanical fixes)                        |
| Comment on pull request | Off (not a PR-review bot)                                      |
| MCP                     | Enable Linear + Notion (and GitHub if not already ambient)     |
| Permissions             | Private (personal billing) unless you intentionally promote    |

### Automation 1 — Research repos

| Field                         | Value                                                                                                                     |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| Name                          | `Weekly Repo Health — Research`                                                                                           |
| Schedule                      | Weekly **Monday 10:00** local (`America/Chicago` recommended)                                                             |
| Cron (if UI is UTC-only, CDT) | `0 15 * * 1`                                                                                                              |
| Cron (if UI accepts local TZ) | `0 10 * * 1` with timezone `America/Chicago`                                                                              |
| Instructions                  | Paste from [`prompts/weekly-repo-health-research.md`](prompts/weekly-repo-health-research.md) (body below the `---` rule) |
| In-prompt repos               | `series_correction_project_updated`, `Hydrograph_Versus_Seatek_Sensors_Project`, `Seatek_Analysis`                        |

### Automation 2 — General repos

| Field                         | Value                                                                                                                   |
| ----------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| Name                          | `Weekly Repo Health — General`                                                                                          |
| Schedule                      | Weekly **Thursday 10:00** local (`America/Chicago` recommended)                                                         |
| Cron (if UI is UTC-only, CDT) | `0 15 * * 4`                                                                                                            |
| Cron (if UI accepts local TZ) | `0 10 * * 4` with timezone `America/Chicago`                                                                            |
| Instructions                  | Paste from [`prompts/weekly-repo-health-general.md`](prompts/weekly-repo-health-general.md) (body below the `---` rule) |
| In-prompt repos               | `personal-config`, `email-security-pipeline`, `ctrld-sync`, `repoprompt-ce`                                             |

### After create

1. Run each automation **once manually** from the dashboard to validate env +
   MCP + report format.
2. Confirm the run used the multi-repo environment (all seven clones present;
   prompt scopes which ones to touch).
3. UUIDs/URLs below are filled for `get-automation` lookups (update if
   recreated).

| Automation | UUID                                   | URL                                                                 | Enabled |
| ---------- | -------------------------------------- | ------------------------------------------------------------------- | ------- |
| Research   | `5d3f67b4-88af-11f1-b532-320a589b8025` | https://cursor.com/automations/5d3f67b4-88af-11f1-b532-320a589b8025 | yes     |
| General    | `7115cfdc-88b0-11f1-b532-320a589b8025` | https://cursor.com/automations/7115cfdc-88b0-11f1-b532-320a589b8025 | yes     |

## Relationship to local launchd stubs

`launch-agents/com.speedybee.repo-health.*.plist` and
`scripts/run-repo-health-*.sh` are **local placeholders** that currently only
log readiness — they do **not** spawn Cursor agents. Option A (this doc) is the
authoritative schedule. Keep or remove the LaunchAgents separately; do not
assume both fire real audits.

## Optional: SDK fan-out (not required for Option A)

If you later want a cron host to spawn cloud agents via `@cursor/sdk` instead of
(or in addition to) dashboard Automations, use the scheduled-triage / multi-repo
fan-out patterns from the Cursor SDK skill (`Agent.create` + `cloud: { repos }`,
`Promise.allSettled`, dispose in `finally`). Prefer Automations for this
workload unless you need custom batching logic outside Cursor’s scheduler.

## Prompt maintenance

Edit the files under `docs/cursor-automations/prompts/`, then paste the updated
body into the matching automation’s Instructions field. There is no API to push
prompt text into Automations from git today — treat these files as the source of
truth and the dashboard as the runtime copy.
