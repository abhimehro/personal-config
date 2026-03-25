# Repository Automation Architecture

This repository uses a consolidated automation model with two scheduled agent workflows:

1. `.github/workflows/repository-automation-daily.yml`
2. `.github/workflows/repository-automation-weekly.yml`

Repo-specific behaviour lives in `.github/repository-automation.yml`, while shared logic lives in `.github/scripts/repository_automation.py`.

The consolidated daily and weekly workflows are intentionally **Copilot-independent**. They rely on repository-local scripting plus `GH_TOKEN`, so they can run without consuming GitHub Copilot allowances.

## Schedule plan

The current workflow files in this repo use the `personal-config` slot from the staggered schedule plan below.

| Repo                      | Daily automation | Weekly automation  | Reasoning                                                                                                                                        |
| ------------------------- | ---------------- | ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `ctrld-sync`              | `03:17 UTC`      | `04:11 UTC` Sunday | Leaves a buffer after the live `sync.yml` run at `02:00 UTC`, avoids top-of-hour congestion, and keeps production-sensitive automation isolated. |
| `personal-config`         | `08:23 UTC`      | `09:11 UTC` Sunday | Mid-morning UTC is typically quieter than top-of-hour windows, and the odd-minute offset avoids bunching with common shared cron defaults.       |
| `email-security-pipeline` | `12:41 UTC`      | `13:29 UTC` Sunday | Keeps the third repo well separated from the other two while still landing during a same-day review window.                                      |

Future rollouts to the other repos should reuse the table above so the three repositories never start their daily or weekly automation at the same moment.

## Guardrails

- Security gates run before every write action.
- Write actions are limited to status issues, weekly retrospective issues, and draft PRs for low-risk workflow updates.
- No force-pushes, no automatic merges, and no automatic edits outside allow-listed paths.
- Protected paths such as auth, migration, and database areas are surfaced for human review instead of silent automation.

## Human-readable output

Every task writes:

- a Markdown report in `.automation-output/<task>/report.md`
- a machine-readable summary in `.automation-output/<task>/result.json`
- a GitHub Actions step summary

The daily workflow always ends by creating or updating a GitHub Issue that explains what ran, what changed, what failed, and what requires human review.

Daily and weekly issues use fixed generated section layouts from the runner rather than ad hoc prose, so past reports stay easy to skim while still preserving a small machine-readable footer for weekly aggregation.

The runner applies predictable labels to those issues:

- `automation:daily-status`
- `automation:weekly-retro`

## Legacy schedules

Older fragmented scheduled workflows are left available for manual dispatch only. Their schedules were removed so the consolidated daily and weekly orchestration owns the automation cadence.

## GH_TOKEN requirements

Use the `GH_TOKEN` secret for all GitHub API calls. Recommended scopes:

- `contents:read` for repository inspection
- `actions:read` for weekly retrospective run analysis
- `issues:write` for daily and weekly reports
- `pull_requests:write` and `contents:write` if draft PR creation is enabled

## Repo-specific notes

- `ctrld-sync` intentionally keeps its existing `sync.yml` schedule because it mutates production Control D state and should not be folded into AI-style automation without explicit maintainer approval.
- Any additional safe write actions can be enabled through `.github/repository-automation.yml` once you are comfortable with the review posture.

## Write-safety mode sketch

`.github/repository-automation.yml` now documents three intended write-safety levels:

- `read-only` — analysis and local artifacts only
- `safe-writes` — status issues, label creation, and allow-listed draft PRs
- `expanded-writes` — broader non-protected-path draft PRs, but still no force-pushes, merges, or protected-path edits

That block is descriptive for now; the runner still enforces the existing explicit per-task write gates until you choose to wire the higher-level modes into execution logic.
