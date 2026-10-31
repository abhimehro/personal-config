# Antigravity Proactive Workflows Migration Guide (v3)

Operational runbook and security architecture for migrating Google Jules
proactive repository sweeps (`Sentinel`, `Bolt`, `Palette`, and `Code Health`)
to Google Antigravity.

## Decision and Scope Codes

| Code                       | Meaning                                                                                                                                                                                                                  |
| :------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`1B` (Pilot Scope)**     | Initial 5-repository set matching legacy proactive coverage (`ctrld-sync`, `email-security-pipeline`, `Hydrograph_Versus_Seatek_Sensors_Project`, `Seatek_Analysis`, `personal-config`).                                 |
| **`1A` (Expanded Scope)**  | Full 7-repository set (`1B` plus `repoprompt-ce` and `series_correction_project_updated`).                                                                                                                               |
| **`2B` (Local-Only Mode)** | Sweeps execute inside isolated worktrees under `$HOME/.gemini/antigravity/worktrees/` and write local `chmod 600` digests under `$HOME/.gemini/antigravity/proactive-reports/` with zero remote pushes or pull requests. |
| **`2A` (Draft PR Mode)**   | Post-graduation mode for `bolt`, `palette`, and `code-health` only (`sentinel` remains permanently off public Draft PRs), backed by server-side `pull_request` rulesets on `~DEFAULT_BRANCH`.                            |
| **`3B` (Native Sidecars)** | Uses Antigravity's built-in `schedule` sidecar (`agentapi new-conversation`) pinned to `CRON_TZ=UTC`.                                                                                                                    |

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
  test-harness edits.
- **Control & Ordered Rollback CLI (`scripts/antigravity-proactive-ctl.sh`):**
  Manages installation (`install [--pilot]`), status (`status`), disposable UTC
  cron verification (`canary-stage` / `canary-clean`), merged-PR-verified
  Sentinel journal leases (`sentinel-post-merge`), missed-wake logging
  (`audit-missed`), and ordered teardown (`disable`).

## Schedule and Operations

- **Pilot Cron:** `CRON_TZ=America/Chicago 15 8 * * 1-5` (Mon-Fri `08:15` local
  time year-round, with companion triage at `08:35` local
  `CRON_TZ=America/Chicago 35 8 * * 1-5`).
- **Digest Statuses:** `CANDIDATE_READY`, `SECURITY_REPORT_ONLY`, `CLEAN_NO_OP`
  (`Substatus: NONE | FLOAT_REORDER_DRIFT | GATE_FAILURE`), `THROTTLED`, and
  `MISSED`.
- **Graduation Gate (`2B` -> `2A`):** `>= 5` mergeable candidates out of `>= 8`
  executed (non-`MISSED`) weekday runs, with `< 2` `GATE_FAILURE` runs.

## Common Commands

```bash
# Install global skill/hook symlinks and stage disabled pilot sidecar
./scripts/antigravity-proactive-ctl.sh install --pilot

# Stage and later clean up a disposable UTC cron canary
./scripts/antigravity-proactive-ctl.sh canary-stage --offset-minutes 5
./scripts/antigravity-proactive-ctl.sh canary-clean

# Record a missed weekday wake slot
./scripts/antigravity-proactive-ctl.sh audit-missed --date YYYY-MM-DD --repo ctrld-sync

# Issue a 5-minute verified post-merge lease before updating .jules/sentinel.md
./scripts/antigravity-proactive-ctl.sh sentinel-post-merge --repo ctrld-sync --pr <merged_pr>

# Ordered rollback (removes sidecars -> unlinks skills -> unlinks hooks.json last)
./scripts/antigravity-proactive-ctl.sh disable
```
