# GitHub Actions Workflows

This repository currently keeps **23 workflow files** under
`.github/workflows/`.

## Audit outcome

- `repository-automation-daily.yml` and `repository-automation-weekly.yml`
  remain the consolidated automation entrypoints.
- `shellcheck.yml` was removed because `mac-audit.yml` and
  `code-quality.yml` already cover the same shell linting scope.
- `test-refactoring-agent.yml` was removed because it was a stub that duplicated
  the real `/cs-agent` trigger handled by `refactoring-agent.yml`.
- GitHub may still show additional **dynamic** workflows (for example CodeQL or
  platform-managed Copilot/Dependabot workflows) in the Actions UI; this file
  only documents workflows stored in this repository.

## Current workflow inventory

### Core repository workflows

| Workflow | Trigger summary | Purpose |
| --- | --- | --- |
| `agentics-maintenance.yml` | Manual dispatch | gh-aw maintenance helper for expiring agentic artifacts and running update/upgrade operations. |
| `case-collision.yml` | Push, PR, manual | Detects case-colliding paths that can break macOS checkouts and symlink syncs. |
| `code-quality.yml` | Push, PR, manual | Runs shell and Python quality checks plus the repository test suite. |
| `copilot-setup-steps.yml` | PRs, issues, manual | Applies the Development Partner protocol and related automation for Copilot-driven work. |
| `dependency-review.yml` | PRs | Uses GitHub dependency review to catch vulnerable or risky dependency changes. |
| `label.yml` | `pull_request_target` | Applies path-based labels from `.github/labeler.yml`. |
| `mac-audit.yml` | Push, PR, weekly schedule, manual | Lints and runs the macOS-focused `mac-audit` regression on GitHub-hosted runners. |
| `main.yml` | Manual dispatch | Deletes remote branches that were merged and have aged out. |
| `pr-visual-recap.yml` | PR lifecycle events | Generates a guarded visual recap comment for pull requests without exposing secrets to untrusted forks. |
| `refactoring-agent.yml` | PR comments with `/cs-agent` | Invokes the CodeScene PR refactoring agent for explicit maintainer requests. |
| `release-drafter.yml` | Pushes to `main`, PR sync events | Keeps the release draft updated from merged and in-flight pull requests. |
| `security-scan.yml` | Push, PR, weekly schedule, manual | Runs repository-wide security checks such as secret scanning, dependency scanning, CodeQL, and SBOM generation. |
| `stale.yml` | Manual dispatch | Marks inactive issues and pull requests as stale. |
| `summary.yml` | New issues | Posts an AI-generated summary comment on newly opened issues. |

### Repository automation orchestration

| Workflow | Trigger summary | Purpose |
| --- | --- | --- |
| `jules-daily-qa.yml` | Daily schedule, manual | Opens cross-repository Jules QA review issues for this repo and sibling repositories. |
| `repository-automation-daily.yml` | Daily schedule, manual | Runs the consolidated daily automation pipeline: workflow upkeep, performance review, QA, backlog management, and status reporting. |
| `repository-automation-weekly.yml` | Weekly schedule, manual | Reviews the past week's automation runs and publishes a retrospective with follow-up guidance. |

### Optional Gemini automation

These workflows are optional and safely skip when Gemini authentication is not
configured.

| Workflow | Trigger summary | Purpose |
| --- | --- | --- |
| `gemini-dispatch.yml` | PRs, issues, comments, reviews | Routes incoming `@gemini-cli` requests to the appropriate Gemini sub-workflow. |
| `gemini-invoke.yml` | Reusable workflow | Handles general-purpose Gemini requests dispatched from `gemini-dispatch.yml`. |
| `gemini-plan-execute.yml` | Reusable workflow | Runs the Gemini `/approve` plan-and-execute flow. |
| `gemini-review.yml` | Reusable workflow | Performs Gemini-powered pull request review. |
| `gemini-scheduled-triage.yml` | Hourly schedule, manual, self-update events | Performs scheduled Gemini issue triage and labeling. |
| `gemini-triage.yml` | Reusable workflow | Handles issue triage requests dispatched from `gemini-dispatch.yml`. |

## Focused validation

- `tests/test_workflow_inventory.py` keeps this inventory synchronized with the
  actual `.github/workflows/*.yml` files.
- `tests/test_copilot_setup_workflow.py` and related workflow tests cover
  security-sensitive workflow behavior.

## Updating this inventory

When you add, remove, or rename a workflow:

1. Update this README in the same change.
2. Keep the workflow listed exactly once in the inventory tables above.
3. Run `python3 -m unittest tests.test_workflow_inventory`.
