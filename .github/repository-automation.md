# Repository Automation Architecture

This repository uses a consolidated automation model with two scheduled agent workflows:

1. `.github/workflows/repository-automation-daily.yml`
2. `.github/workflows/repository-automation-weekly.yml`

Repo-specific behaviour lives in `.github/repository-automation.yml`, while shared logic lives in `.github/scripts/repository_automation.py`.

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
