# CI/CD Performance Engineering Guide

## Overview

This repository uses GitHub Actions for code quality checks, complexity analysis, and automated workflows. CI performance directly impacts developer productivity and GitHub Actions costs.

## Current CI Workflows

### code-quality.yml

- **Shell quality:** Lint/correctness gate via cached ShellCheck (`./.github/actions/setup-shellcheck`)
- **Python quality:** Analyzes Python files with radon/ruff/bandit
- **Tests:** `make test-all`
- **Duration target:** <2 minutes on warm cache

### repository-automation-daily.yml (quality_assurance)

- **ShellCheck:** Cached pinned binary via `setup-shellcheck`
- **Trunk:** Cached CLI + `~/.cache/trunk` via `setup-trunk` (key includes `hashFiles('.trunk/trunk.yaml')`)
- Runs `make lint-errors`, smoke tests, full suite, optional `make lint`

## Key Optimization Strategies

### 1. Effective Caching (ABHI-1135)

Reusable composite actions centralize install + cache:

**ShellCheck** — `.github/actions/setup-shellcheck`:

```yaml
- name: Setup ShellCheck (cached)
  uses: ./.github/actions/setup-shellcheck
  # optional: with: { version: v0.11.0 }
```

- Path: `~/.local/bin/shellcheck`
- Key: `shellcheck-${{ runner.os }}-${{ runner.arch }}-<version>`
- Invalidates when the `version` input changes
- Downloads from `koalaman/shellcheck` releases (not apt) for pin + cacheability

**Trunk** — `.github/actions/setup-trunk`:

```yaml
- name: Setup Trunk (cached)
  uses: ./.github/actions/setup-trunk
```

- Paths: `~/.cache/trunk`, `~/.local/bin/trunk`
- Key: `trunk-${{ runner.os }}-${{ runner.arch }}-${{ hashFiles('.trunk/trunk.yaml') }}`
- Invalidates when CLI/linter/plugin versions in `.trunk/trunk.yaml` change
- On cache miss, runs `trunk install` to warm the tool cache

**Python pip cache (built-in):**

```yaml
- name: Set up Python
  uses: actions/setup-python@v5
  with:
    python-version: "3.12"
    cache: "pip"
```

### 2. Parallel Job Execution

`code-quality.yml` runs independent jobs in parallel (`shell-quality`, `python-quality`, `test`).

### 3. Path-Based Triggering

Workflows only run when relevant files change (e.g. `**.sh`, `mac-audit/**`).

### 4. Concurrency Control

Prefer canceling stale runs:

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

## Performance Measurement

```bash
# Get workflow run times
gh run list --workflow=code-quality.yml --limit 10 --json conclusion,startedAt,updatedAt

# Calculate average duration
gh api "repos/abhimehro/personal-config/actions/workflows/code-quality.yml/runs" \
  | jq '.workflow_runs[:10] | map(.run_duration_ms / 1000) | add / length'
```

## Cache Invalidation

| Tool       | Change this                         | Effect                          |
| ---------- | ----------------------------------- | ------------------------------- |
| ShellCheck | `version` input on setup-shellcheck | New cache key; fresh download   |
| Trunk      | `.trunk/trunk.yaml`                 | New cache key; `trunk install`  |

## Success Metrics

- **Cold cache (first run):** same as pre-cache baseline (download + install)
- **Warm cache (subsequent runs):** ~30–60s faster (skip apt/curl tool downloads)
- **Cache hit rate:** >80% on repeated runs
