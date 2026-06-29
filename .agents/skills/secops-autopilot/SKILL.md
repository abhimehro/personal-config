---
name: secops-autopilot
description: >-
  Automated workstation maintenance agent integrating GHA workflow updating (Pin),
  tech debt triage (Triage), and test/drift audits (Health) with Google Antigravity SDK diagnostics.
---

# SecOps Autopilot

## Overview
The `secops-autopilot` skill provides automated, local-first workstation technical debt triage, security/drift monitoring, and repository health audits. It leverages the Google Antigravity Python SDK for intelligent diagnostic analysis of test suites and system status reports.

## Dependencies
- [google-antigravity-sdk](file:///Users/speedybee/.gemini/config/plugins/google-antigravity-sdk/skills/google-antigravity-sdk/SKILL.md): Orchestrates local diagnostics and LLM execution.
- [uv](file:///Users/speedybee/.gemini/config/plugins/science/skills/uv/SKILL.md): Manages isolated dependency runtimes.
- `gh-aw` CLI extension: Automatically updates GitHub Actions workflows to pinned commit SHAs.

## Quick Start
Execute the full suite of maintenance checks or targeted modules via `uv run`:
```bash
# Pin GHA workflows (weekly cadence)
uv run .agents/skills/secops-autopilot/scripts/secops_agent.py pin

# Technical debt triage (bi-weekly cadence)
uv run .agents/skills/secops-autopilot/scripts/secops_agent.py triage --max-tasks 3

# Run tests and audit system drift (daily cadence)
uv run .agents/skills/secops-autopilot/scripts/secops_agent.py health
```

## Utility Scripts

### `secops_agent.py` subcommands:

#### `pin`
- **Purpose**: Checks for GHA lockfile (`.github/aw/actions-lock.json`), runs `gh aw update`, validates compilation via `gh aw compile --validate`, and commits/pushes changes.
- **Parameters**:
  - `--dry-run`: Evaluate changes without writing commits or pushing.
  - `--max-retries <n>`: Maximum push retries on conflicts (default: 1).
- **Safety**: Aborts rebase and halts on non-lockfile conflicts. Staggers or skips execution if active bot PR reviews are detected.

#### `triage`
- **Purpose**: Audits repository tech debt files (`tasks/todo.md`, `tasks/lessons.md`) and compiles technical debt summaries.
- **Parameters**:
  - `--dry-run`: Log technical debt statistics without updating files.
  - `--max-tasks <n>`: Limit number of tasks outputted (default: 3).
  - `--init-scaffold`: Automatically initialize `tasks/` directory and backlog files if missing.

#### `health`
- **Purpose**: Executes repository test suites and audits macOS system drift (DNS resolvers, LaunchAgents, SSH configuration status).
- **Parameters**:
  - `--dry-run`: Runs checks without applying allowlisted auto-fixes.
  - `--confidence-threshold <0.0-1.0>`: Minimum confidence score for auto-fixes (default: 0.85).
  - `--no-llm`: Skip LLM-based diagnostic analysis of failure logs.

#### `run`
- **Purpose**: General dispatcher that maps cadence inputs (`--cadence <weekly|bi-weekly|daily>`) to targeted commands. Useful as a single entrypoint for LaunchAgents.

#### `status`
- **Purpose**: Returns summaries of the recent history logs and pending technical debt tasks.

## Rate Limiting & Gating
- **Gemini API**: Diagnostic runs are restricted to a maximum of 5 LLM calls per execution. Rate limits are handled with exponential backoff on HTTP 429 warnings.
- **GitHub API**: Automatically implements pagination throttling.

## Common Mistakes
- **Applying Auto-Heals on Config Drift**: System drift (DNS leaks, SSH key permissions) should strictly remain Audit-Only. Never attempt to rewrite workstation DNS or LaunchAgents in an automated script.
- **Bypassing Security Tests**: Repositories flagged as security-sensitive must never bypass a failing test check, even if the error appears unrelated or exists on the base branch.
- **Blind checkout of journal files**: When cherry-picking or salvaging commits, never use `git checkout pr_branch -- CHANGELOG.md` or other journal files. Always extract unique lines and append to preserve history integrity.
