# CI/CD Performance Engineering Guide

## Overview
This repository uses GitHub Actions for code quality checks, complexity analysis, and automated workflows. CI performance directly impacts developer productivity and GitHub Actions costs.

## Current CI Workflows

### code-quality.yml
- **ShellCheck complexity:** Lints 117+ shell scripts
- **Python complexity:** Analyzes Python files with radon
- **Trunk check:** Runs multiple linters (shellcheck, shfmt, markdownlint, etc.)
- **Duration:** Currently 2-3 minutes per run

## Performance Goals
- **PR feedback:** <2 minutes from push to completion
- **Cache hit rate:** >80% on repeated runs
- **Resource efficiency:** Minimize GitHub Actions minutes
- **Incremental checks:** Only analyze changed files when possible

## Key Optimization Strategies

### 1. Effective Caching
The code-quality workflow already implements caching:

**ShellCheck cache:**
```yaml
- name: Cache ShellCheck
  uses: actions/cache@v3
  with:
    path: ~/.local/bin/shellcheck
    key: shellcheck-${{ runner.os }}-v0.10.0
```

**Trunk cache:**
```yaml
- name: Cache Trunk
  uses: actions/cache@v3
  with:
    path: |
      ~/.cache/trunk
      .trunk/out
    key: trunk-${{ runner.os }}-${{ hashFiles('.trunk/trunk.yaml') }}
```

**Python pip cache (built-in):**
```yaml
- name: Set up Python
  uses: actions/setup-python@v5
  with:
    python-version: '3.12'
    cache: 'pip'
```

### 2. Parallel Job Execution
Current workflow runs 3 jobs in parallel:
- `shellcheck-complexity`
- `python-complexity`
- `trunk-check`

This is optimal - they're independent and maximize throughput.

### 3. Path-Based Triggering
Workflow only runs when relevant files change:
```yaml
on:
  pull_request:
    paths:
      - '**.sh'
      - '**.py'
      - '**.bash'
      - 'scripts/**'
```

**Improvement opportunity:** Add more specific patterns to skip docs-only changes.

### 4. Concurrency Control
Already implemented to cancel stale runs:
```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

## Performance Measurement

### Measure Workflow Duration
```bash
# Get workflow run times
gh run list --workflow=code-quality.yml --limit 10 --json conclusion,startedAt,updatedAt

# Calculate average duration
gh api "repos/abhimehro/personal-config/actions/workflows/code-quality.yml/runs" \
  | jq '.workflow_runs[:10] | map(.run_duration_ms / 1000) | add / length'
```

### Identify Slow Steps
Look at individual step timings in Actions UI or via API:
```bash
gh run view <run-id> --log
```

Common bottlenecks:
- Installing tools (solved by caching)
- Finding all files (use incremental checking)
- Running linters on all files (use changed files only)

## Advanced Optimization Techniques

### Technique 1: Incremental Linting
Currently Trunk attempts this with `--upstream`, but can be more aggressive:

**Before:**
```bash
trunk check --all --upstream origin/main
```

**Optimized:**
```bash
# Only check files changed in this PR
git diff --name-only origin/main...HEAD \
  | grep -E '\.(sh|bash|py)$' \
  | xargs trunk check
```

**Impact:** 80% faster for small PRs (only checks 5 files instead of 117)

### Technique 2: Fast-Fail Strategy
Exit early on first critical error to save time:

```yaml
- name: Quick syntax check
  run: |
    # Fast shell syntax check before expensive linting
    find . -name '*.sh' -exec bash -n {} \; || exit 1
```

### Technique 3: Matrix Parallelization
For very large repos, split work across matrix:

```yaml
strategy:
  matrix:
    directory: [scripts, maintenance, tests, controld-system]
jobs:
  lint:
    steps:
      - run: trunk check ${{ matrix.directory }}
```

**Trade-off:** More parallelism but higher startup overhead

## Real-World Optimization Example

### Scenario: ShellCheck Taking 45 Seconds
**Problem:** Running shellcheck on all 117 scripts sequentially

**Optimization:**
```bash
# Parallel shellcheck with xargs
find . -name '*.sh' -print0 \
  | xargs -0 -P 4 -I {} shellcheck {}
```

**Result:** 45s → 15s (3x faster)

**Implementation in workflow:**
```yaml
- name: Run ShellCheck in parallel
  run: |
    find . -name '*.sh' -print0 > /tmp/shell_files.txt
    xargs -0 -P 4 -I {} shellcheck {} < /tmp/shell_files.txt
```

## Cache Validation and Monitoring

### Check Cache Hit Rate
```bash
# Get recent runs with cache info
gh api "repos/abhimehro/personal-config/actions/workflows/code-quality.yml/runs" \
  | jq '.workflow_runs[0].jobs | map(select(.name | contains("Cache"))) | .[].conclusion'
```

### Invalidate Cache When Needed
Change cache key when dependencies change:
```yaml
key: shellcheck-${{ runner.os }}-v0.11.0  # Bumped version
```

## When to Optimize CI

✅ **Optimize when:**
- Workflow takes >3 minutes consistently
- Developers complain about slow feedback
- GitHub Actions minutes approaching limit
- Same work repeated across multiple jobs

❌ **Don't optimize when:**
- Already under 2 minutes
- Complexity outweighs benefit
- Caching already optimal

## Success Metrics

**Target benchmarks:**
- **Cold cache (first run):** <4 minutes
- **Warm cache (subsequent runs):** <2 minutes
- **Cache hit rate:** >80%
- **Changed files only:** <1 minute

**Monitoring:**
```bash
# Create performance tracking
echo "$(date): $(gh run list --workflow=code-quality.yml --limit 1 --json conclusion,durationMs | jq '.[] | .durationMs')" \
  >> .github/workflows/performance-log.txt
```

**Key principle:** Optimize for the common case (incremental changes on PRs with warm cache). First-time setup can be slower since it's rare.
