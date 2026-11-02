# Antigravity Proactive Workflows Migration Guide (v3)

Operational runbook and security architecture for migrating Google Jules
proactive repository sweeps (`Sentinel`, `Bolt`, `Palette`, and `Code Health`)
to Google Antigravity.

The evidence base for every gate and threshold below — the Jules export
analysis, the failure taxonomy, the archive integrity manifest, and the
decisions record — is in
[jules-proactive-analysis-2026-11.md](jules-proactive-analysis-2026-11.md).

## Decision and Scope Codes

| Code                       | Meaning                                                                                                                                                                                                                                                                                                                                                               |
| :------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`1B` (Pilot Scope)**     | Initial 5-repository set matching legacy proactive coverage (`ctrld-sync`, `email-security-pipeline`, `Hydrograph_Versus_Seatek_Sensors_Project`, `Seatek_Analysis`, `personal-config`).                                                                                                                                                                              |
| **`1A` (Expanded Scope)**  | Full 7-repository set (`1B` plus `repoprompt-ce` and `series_correction_project_updated`).                                                                                                                                                                                                                                                                            |
| **`2B` (Local-Only Mode)** | Sweeps execute inside isolated worktrees under `$HOME/.gemini/antigravity/worktrees/` and write local `chmod 600` digests under `$HOME/.gemini/antigravity/proactive-reports/` with zero remote pushes or pull requests.                                                                                                                                              |
| **`2A` (Draft PR Mode)**   | Post-graduation mode for `bolt`, `palette`, and `code-health` only (`sentinel` remains permanently off public Draft PRs), backed by server-side `pull_request` rulesets on `~DEFAULT_BRANCH`.                                                                                                                                                                         |
| **`3B` (Native Sidecars)** | Uses Antigravity's built-in `schedule` sidecar (`agentapi new-conversation`). `CRON_TZ` is **per-sidecar**, not globally pinned: the pilot sidecars use `CRON_TZ=America/Chicago` (08:15 sweep, 08:35 triage) so the digest lands when a human reads it. `canary-stage` still stages a disposable **UTC** cron, so a canary does not yet exercise the pilot timezone. |

## Installed Components

- **Skills (`configs/antigravity/skills/` -> `$HOME/.gemini/config/skills/`):**
  - `proactive-sentinel`: Code-level security audit (`SECURITY_REPORT_ONLY`
    local digest or private GitHub Security Advisories; never public Draft PRs).
  - `proactive-bolt`: Measurable performance/idempotency optimization with
    mandatory numeric equivalence (`rtol=1e-10, atol=1e-12` in Python,
    `tolerance = 1e-10` in R) on research repositories and separate
    `FLOAT_REORDER_DRIFT` substatus reporting.
  - `proactive-palette`: CLI/UI ergonomics, `NO_COLOR`, and TTY safety (disabled
    on scientific repositories).
  - `proactive-code-health`: Safe dead-code removal and maintainability checks
    using `references/jules-review-rules.md`.
  - `proactive-repo-sweep`: 15-minute coordinator enforcing single-improvement
    runs, open-PR file collision checks, and dual `2B` + `2A` throttling.
- **Safety Hook (`configs/antigravity/hooks.json` ->
  `$HOME/.gemini/config/hooks.json`):** Invokes
  `configs/antigravity/hooks/proactive-guard.py` on `PreToolUse` to block force
  pushes, protect primary checkouts under `$HOME/dev/` during sweep sessions,
  block unmerged `.jules/sentinel.md` writes without a verified post-merge
  lease, and block remote `git push` / `gh pr` mutations in `2B` mode.
- **Worktree & Verification Runner (`scripts/proactive-worktree.sh`):** Creates
  collision-proof worktrees (`21`-day TTL preserving dirty and unmerged
  candidate commits), sets worktree-scoped `pushurl = DISABLED`, strips
  `SSH_AUTH_SOCK`/`GH_TOKEN`/`GITHUB_TOKEN` in verification subprocesses, and
  fails closed (`exit 2`) on tamper-evident build, lockfile, script, or
  test-harness edits. Verification also runs a mandatory **base-relative
  semantic test-coverage gate**: the AST of every touched Python test file is
  diffed against the pinned `base_sha`, and any removed test class, lost test
  method, or drop in total test count blocks (`exit 2`) even when the suite is
  green, because losing a test does not fail a suite. Touched Python files that
  do not parse are blocked too, with an undefined-name check
  (`ruff --select=F82`, else `pyflakes`) when one is installed. Intentional
  reductions must be declared with `--expected-test-count <n>`. `check-throttle`
  refreshes `origin` before any ref-based verdict and fails closed (`exit 6`)
  rather than judging against a stale ref, and `--include-worktrees` extends the
  local cap across every git-registered proactive worktree rather than only the
  default root. `check-collisions --include-worktrees --repo-path <clone>`
  closes the same gap for file ownership: under `2B` local-first mode there are
  no bot PRs, so a PR-only collision check is a no-op for exactly the class that
  stranded real work — two sessions editing the same file in one burst. It
  unions in every live candidate worktree's changed paths (excluding one whose
  work already merged, so it cannot block that path for the whole TTL), fails
  closed on a truncated PR listing (`exit 5`) or an unenumerable worktree set
  (`exit 6`), and reports a collision as `exit 4`.
  `print-test-cmd --repo-name <name>` exposes the repo-to-test-command mapping
  so the control CLI resolves the same command `verify` runs instead of
  duplicating it.
- **Control & Ordered Rollback CLI (`scripts/antigravity-proactive-ctl.sh`):**
  Manages installation (`install [--pilot]`), status (`status`), disposable UTC
  cron verification (`canary-stage` / `canary-clean`), merged-PR-verified
  Sentinel journal leases (`sentinel-post-merge`), missed-wake logging
  (`audit-missed`), base-relative failure classification (`base-check`), and
  ordered teardown (`disable`).

  `base-check --repo <name> --worktree <dir> [--digest <path>]` answers the
  question a bare verify exit code cannot: **was this failure caused by the
  candidate, or was base already broken?** It splits the repo's compound test
  command on `&&`, re-runs the failing stage once in the candidate to catch a
  flake, then re-runs the stages on a pristine `base_sha` worktree, and prints a
  `VERDICT` of `NO_FAILURE`, `FLAKE_ON_RETRY`, `PRE_EXISTING_ON_BASE` (`exit 0`,
  candidate still promotable, base breakage filed separately) or
  `CAUSED_BY_CHANGE` (`exit 2`, discard the candidate). Credentials are stripped
  exactly as `verify` strips them, no `origin` ref is consulted (the comparison
  is against a local `base_sha`, so it stays valid offline), and `--digest`
  appends a `## Base-Check Classification` section to the `chmod 600` report
  rather than rewriting it. It runs in the `08:35` triage slot, never inside the
  sweep, because a base re-run can double test time and the sweep is boxed at 15
  minutes. The triage sidecar therefore gains read/write grants on the worktrees
  directory — re-running a suite writes `__pycache__` and `.pytest_cache` in
  place — but deliberately keeps a **reports-only `workspace_uris`**: the
  `PreToolUse` guard classifies a session as a sweep from its workspace paths,
  so adding the worktrees root would upgrade a read-mostly review slot into a
  sweep session able to push and open PRs.

## Schedule and Operations

- **Pilot Cron:** `CRON_TZ=America/Chicago 15 8 * * 1-5` (Mon-Fri `08:15` local
  time year-round, with companion triage at `08:35` local
  `CRON_TZ=America/Chicago 35 8 * * 1-5`).
- **Digest Statuses:** `CANDIDATE_READY`, `SECURITY_REPORT_ONLY`, `CLEAN_NO_OP`
  (`Substatus: NONE | FLOAT_REORDER_DRIFT | GATE_FAILURE | PRE_EXISTING_FAILURE`),
  `THROTTLED`, and `MISSED`. The sweep writes only the first three substatuses;
  `PRE_EXISTING_FAILURE` is appended by the `08:35` triage slot's `base-check`,
  together with a `## Base-Check Classification` verdict.
- **Graduation Gate (`2B` -> `2A`):** `>= 5` mergeable candidates out of `>= 8`
  executed (non-`MISSED`) weekday runs, with `< 2` `GATE_FAILURE` runs. Only a
  run whose final classification is `CAUSED_BY_CHANGE` counts against that
  budget: a `PRE_EXISTING_ON_BASE` or `FLAKE_ON_RETRY` verdict means the
  pipeline worked, so charging it to the gate would let unrelated base breakage
  block graduation forever.

## Common Commands

```bash
# Install global skill/hook symlinks and stage disabled pilot sidecar
./scripts/antigravity-proactive-ctl.sh install --pilot

# Stage and later clean up a disposable UTC cron canary
./scripts/antigravity-proactive-ctl.sh canary-stage --offset-minutes 5
./scripts/antigravity-proactive-ctl.sh canary-clean

# Record a missed weekday wake slot
./scripts/antigravity-proactive-ctl.sh audit-missed --date YYYY-MM-DD --repo ctrld-sync

# Classify a verify failure as base-relative before discarding the candidate
# (exit 0 = NO_FAILURE / FLAKE_ON_RETRY / PRE_EXISTING_ON_BASE, promote it;
#  exit 2 = CAUSED_BY_CHANGE, discard it; exit 6 = base worktree unusable)
./scripts/antigravity-proactive-ctl.sh base-check --repo ctrld-sync \
  --worktree "$HOME/.gemini/antigravity/worktrees/<candidate>" \
  --digest "$HOME/.gemini/antigravity/proactive-reports/YYYY-MM-DD-ctrld-sync.md"

# Show the test command verify (and therefore base-check) will run for a repo
./scripts/proactive-worktree.sh print-test-cmd --repo-name ctrld-sync

# Issue a 5-minute verified post-merge lease before updating .jules/sentinel.md
./scripts/antigravity-proactive-ctl.sh sentinel-post-merge --repo ctrld-sync --pr <merged_pr>

# Ordered rollback (removes sidecars -> unlinks skills -> unlinks hooks.json last)
./scripts/antigravity-proactive-ctl.sh disable
```
