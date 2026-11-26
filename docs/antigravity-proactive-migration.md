# Antigravity Proactive Workflows Migration Guide (v3)

Operational runbook and security architecture for migrating Google Jules
proactive repository sweeps (`Sentinel`, `Bolt`, `Palette`, and `Code Health`)
to Google Antigravity.

The evidence base for every gate and threshold below — the Jules export
analysis, the failure taxonomy, the archive integrity manifest, and the
decisions record — is in
[jules-proactive-analysis-2026-11.md](jules-proactive-analysis-2026-11.md).

## Decision and Scope Codes

| Code                       | Meaning                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| :------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`1B` (Pilot Scope)**     | Initial 5-repository set matching legacy proactive coverage (`ctrld-sync`, `email-security-pipeline`, `Hydrograph_Versus_Seatek_Sensors_Project`, `Seatek_Analysis`, `personal-config`).                                                                                                                                                                                                                                                                                                              |
| **`1A` (Expanded Scope)**  | Full 7-repository set (`1B` plus `repoprompt-ce` and `series_correction_project_updated`).                                                                                                                                                                                                                                                                                                                                                                                                            |
| **`2B` (Local-Only Mode)** | Sweeps execute inside isolated worktrees under `$HOME/.gemini/antigravity/worktrees/` and write local `chmod 600` digests under `$HOME/.gemini/antigravity/proactive-reports/` with zero remote pushes or pull requests.                                                                                                                                                                                                                                                                              |
| **`2A` (Draft PR Mode)**   | Post-graduation mode for `bolt`, `palette`, and `code-health` only (`sentinel` remains permanently off public Draft PRs), backed by server-side `pull_request` rulesets on `~DEFAULT_BRANCH`.                                                                                                                                                                                                                                                                                                         |
| **`3B` (Native Sidecars)** | Uses Antigravity's built-in `schedule` sidecar (`agentapi new-conversation`). `CRON_TZ` is **per-sidecar**, not globally pinned: the pilot sidecars use `CRON_TZ=America/Chicago` (08:15 sweep, 08:35 `[PROACTIVE-JUDGE-SHADOW]` Judge & Triage), `stage-repo --stagger` assigns deterministic 25-minute weekday intervals across all 7 repositories (`08:15`/`08:35` through `10:45`/`11:05`), and `canary-stage` defaults to `--timezone America/Chicago` (with `UTC` still selectable explicitly). |

## Installed Components

- **Skills (`configs/antigravity/skills/` -> copied to
  `$HOME/.gemini/config/skills/`):**
  - `proactive-sentinel`: Code-level security audit (`SECURITY_REPORT_ONLY`
    local digest or private GitHub Security Advisories; never public Draft PRs).
  - `proactive-bolt`: Measurable performance/idempotency optimization with
    mandatory numeric equivalence (`rtol=1e-10, atol=1e-12` in Python,
    `tolerance = 1e-10` in R) on research repositories and separate
    `FLOAT_REORDER_DRIFT` substatus reporting.
  - `proactive-palette`: CLI/UI ergonomics, `NO_COLOR`, and TTY safety (disabled
    on scientific repositories).
  - `proactive-code-health`: Safe dead-code removal and maintainability checks
    using `references/jules-review-rules.md`. **Also carries the testing lens**
    via `--focus` (decided 2026-11-03): no separate rotation slot until there is
    data to justify one. Promote testing to its own slot only if, at the R1
    readout, testing findings exceed **~⅓ of `code-health` output**, or if
    `--focus` runs keep **pushing other findings out**. Rationale: a new slot
    costs a sweep cycle and a review queue entry regardless of yield, and R1 has
    not produced any testing-lens yield data yet.
  - `proactive-repo-sweep`: 15-minute coordinator enforcing single-improvement
    runs, open-PR file collision checks, and dual `2B` + `2A` throttling.
- **Safety Hook (`configs/antigravity/hooks.json` -> copied to
  `$HOME/.gemini/config/hooks.json`):** Prefers
  `$HOME/.gemini/config/proactive/hooks/proactive-guard.py` (copied from
  `configs/antigravity/hooks/proactive-guard.py`, decoupled from the repo
  working tree), falls back to
  `$HOME/dev/personal-config/configs/antigravity/hooks/proactive-guard.py`
  during pre-install legacy symlink upgrades, and exits `2` fail-closed if
  neither exists. Runs on `PreToolUse` to block force pushes, protect primary
  checkouts under `$HOME/dev/` during sweep sessions, block unmerged
  `.jules/sentinel.md` writes without a verified post-merge lease, and block
  remote `git push` / `gh pr` mutations in `2B` mode.
- **Worktree & Verification Runner (`scripts/proactive-worktree.sh`):** Creates
  collision-proof worktrees (`21`-day TTL preserving dirty and unmerged
  candidate commits, plus `cleanup --prune-merged` to remove clean
  verified-merged worktrees and their `proactive/*` branches regardless of age),
  sets worktree-scoped `pushurl = DISABLED` and headless local
  `commit.gpgsign=false` in `local` mode (preventing 1Password `op-ssh-sign`
  Touch ID stalls during unattended `2B` candidate commits while leaving
  `~/.gitconfig`, primary checkouts, and `draft-pr` mode untouched), strips
  `SSH_AUTH_SOCK`/`GH_TOKEN`/`GITHUB_TOKEN`/`VIRTUAL_ENV` in verification
  subprocesses, resolves repo `.venv/bin` onto `PATH` (`<worktree>/.venv/bin`
  then `<repo_path>/.venv/bin`) when commands do not use `uv run`, and fails
  closed (`exit 2`) on tamper-evident build, lockfile, script, or test-harness
  edits. Verification also runs a mandatory **base-relative semantic
  test-coverage gate**: the AST of every touched Python test file is diffed
  against the pinned `base_sha`, and any removed test class, lost test method,
  or drop in total test count blocks (`exit 2`) even when the suite is green,
  because losing a test does not fail a suite. Touched Python files that do not
  parse are blocked too, followed by a **mandatory** undefined-name check
  resolved in order `ruff --select=F82` -> `uv run [--frozen] --all-extras ruff`
  (uv-managed repos such as `ctrld-sync` ship ruff through their lockfile rather
  than onto `PATH`) -> `<repo_path>/.venv/bin/ruff` -> `python3 -m pyflakes` /
  `<repo_path>/.venv/bin/python3 -m pyflakes`. When **none** is available the
  gate **fails closed (`exit 2`)** instead of degrading to the parse floor: an
  AST parse proves a file is syntactically valid, not that its names resolve, so
  a missing linter must block rather than quietly turn a required check into a
  decorative one. `ruff==0.17.3` is pinned in `requirements.txt` (matching
  `ruff@0.17.3` in `.trunk/trunk.yaml`) so a provisioned environment never
  reaches that branch — though it was reachable on the host where R1 was built,
  meaning the tier had been a silent no-op there. Intentional reductions must be
  declared with `--expected-test-count <n>`.

  For headless reliability, `fetch_origin_resilient` handles SSH->HTTPS+`gh`
  fallback (`https-gh` using `GIT_TERMINAL_PROMPT=0` and
  `gh auth
  git-credential`, falling back to `https-anon` and bounded
  `ssh -o
  BatchMode=yes` unless `PROACTIVE_FETCH_FORCE_SSH=1`; configurable
  via `PROACTIVE_FETCH_RETRIES`, `PROACTIVE_FETCH_BACKOFF_S`,
  `PROACTIVE_FETCH_TIMEOUT_S`), keeping `require_fresh_origin_ref` fail-closed
  (`exit 6`). `run_gh_resilient` wraps `gh` queries in `check-collisions` and
  `check-throttle` with bounded timeouts and backoff (`PROACTIVE_GH_RETRIES`,
  `PROACTIVE_GH_BACKOFF_S`, `PROACTIVE_GH_TIMEOUT_S`), failing fast on permanent
  errors (`HTTP 401`/`404`, unauthenticated host, unknown flag), validating
  `--json` output, and exiting `6` on exhaustion.
  `preflight --repo
  <owner/name> --repo-path <dir> [--auto-heal] [--skip-fetch]`
  verifies `origin` refresh, `gh auth status`, and per-repo toolchain readiness
  (exiting `6` on fetch/auth failures or `7` with actionable `remediation=`
  hints on missing toolchains); with `--auto-heal`, it prunes stale git worktree
  records, repairs missing `origin/HEAD` best-effort, and prunes clean
  verified-merged worktrees. `check-throttle` refreshes `origin` before any
  ref-based verdict and fails closed (`exit 6`) rather than judging against a
  stale ref, and `--include-worktrees` extends the local cap across every
  git-registered proactive worktree rather than only the default root. Candidate
  worktrees follow a **two-tier head-bound lifecycle** in `proactive-meta.json`:
  `prepare` initializes `"lifecycle_state": "UNJUDGED"` (`cap=2` via
  `--max-open 2`, strict `> 7d` fail-closed age gate), `set-state --worktree
  <dir> --state <UNJUDGED|JUDGED|EXPIRED|REJECTED> [--verdict <v>] [--subreason
  <s>]` transitions clean committed worktrees while binding `judged_head_sha` to
  `HEAD` (any subsequent dirty edit or new commit automatically downgrades the
  worktree back to `UNJUDGED`), `--max-judged-open 5` bounds evaluated
  `JUDGED` candidates separately so unmerged candidates awaiting human review do
  not block fresh sweeps, `--auto-expire` transitions `> 7d` `JUDGED` worktrees
  on disk to `EXPIRED` (`SLA_7D_AUTO_EXPIRE`, branch and worktree preserved,
  while keeping `UNJUDGED` `> 7d` fail-closed), and `reopen --worktree <dir>`
  restores an `EXPIRED` candidate with `reopened_at` and `original_created_at`.
  `check-collisions --include-worktrees --repo-path <clone> [--exclude-worktree
  <dir>]` closes the same gap
  for file ownership: under `2B` local-first mode there are no bot PRs, so a
  PR-only collision check is a no-op for exactly the class that stranded real
  work — two sessions editing the same file in one burst. It unions in every
  live candidate worktree's changed paths (`UNJUDGED`, `JUDGED`, and preserved
  `EXPIRED` candidates, excluding `--exclude-worktree` self-checks and any
  worktree whose work already merged so merged branches cannot block paths for
  the whole TTL), fails closed on a truncated PR listing (`exit 5`) or an
  unenumerable worktree set (`exit 6`), and reports a collision as `exit 4`.
  `print-test-cmd --repo-name <name>` exposes the repo-to-test-command mapping
  (including `MPLBACKEND=Agg python3 -m pytest scripts/tests/ -q` for
  `series_correction_project_updated`) so the control CLI resolves the same
  command `verify` runs instead of duplicating it.
- **Control & Ordered Rollback CLI (`scripts/antigravity-proactive-ctl.sh`):**
  Manages installation (`install [--pilot]`), status (`status`), self-healing
  diagnostics
  (`doctor [--fix] [--source-repo <dir>] [--repo <name> ...]
  [--all-repos] [--skip-fetch]`),
  multi-repo sidecar staging
  (`stage-repo --repo
  <name> [--stagger] [--cron "<expr>"] [--triage-cron "<expr>"] [--repo-path <dir>]`),
  disposable timezone-aware cron verification (`canary-stage` / `canary-clean`),
  merged-PR-verified Sentinel journal leases (`sentinel-post-merge`),
  missed-wake logging (`audit-missed`), base-relative failure classification
  (`base-check`), two-tier automated candidate judging (`judge`), and ordered
  teardown (`disable`).

  `doctor` checks deployed runtime health (`skills_linked`, `hooks_linked`,
  `hooks_mode`, `dangling_links`, `runtime_*`) — repairing defects via
  `install
  --pilot` when `--fix` is passed — and invokes
  `proactive-worktree.sh
  preflight` (passing `--auto-heal` under `--fix` and
  `--skip-fetch` when requested) across explicit `--repo` targets, all 7
  repositories under `--all-repos`, or `ctrld-sync` by default, surfacing
  `remediation` hints on `FAIL_TOOLCHAIN` (`exit 7`) and emitting
  `doctor_status=HEALTHY` (`exit 0`) or `DEGRADED` (`exit 1`). `stage-repo`
  atomically writes `0600` `proactive-sweep-<repo>` and
  `proactive-triage-<repo>` (`[PROACTIVE-JUDGE-SHADOW]`) sidecars (never
  creating `user_config.json`), granting `preflight --auto-heal`,
  `gh auth
  status`, `judge`, `ocr`, `coderabbit`, `lrc`, `node`, and `doctor`
  access while tailoring lens rotation for research repos (`code-health`, `bolt`
  with mandatory `--numeric-check-cmd`, read-only `sentinel`, never `palette`)
  vs core repos (`bolt`, `code-health`, `palette`, read-only `sentinel`). When
  `--stagger` is passed without explicit `--cron` / `--triage-cron`,
  `stage-repo` assigns deterministic non-overlapping weekday slots
  (`CRON_TZ=America/Chicago`, 25-minute spacing with a +20-minute Judge
  companion): `ctrld-sync` (`08:15` / `08:35`), `email-security-pipeline`
  (`08:40` / `09:00`), `personal-config` (`09:05` / `09:25`),
  `Hydrograph_Versus_Seatek_Sensors_Project` (`09:30` / `09:50`),
  `Seatek_Analysis` (`09:55` / `10:15`), `series_correction_project_updated`
  (`10:20` / `10:40`), and `repoprompt-ce` (`10:45` / `11:05`). Without
  `--stagger`, `stage-repo` preserves the `08:15` / `08:35` default schedule.
  `disable` also tears down staged `proactive-sweep-*` / `proactive-triage-*`
  sidecars only when their directory carries `.managed-by-proactive-ctl`,
  leaving unrelated user sidecars untouched.

  `judge [--repo <name> ...] [--all-repos] [--date <YYYY-MM-DD>] [--cron "<expr>"]
  [--skip-tier2] [--with-lrc] [--force-rejudge]`
  runs in the companion `[PROACTIVE-JUDGE-SHADOW]` slot to evaluate `UNJUDGED`
  candidate worktrees and prevent queue deadlocks:
  - **Tier 1 (Local / Deterministic & Graph):** Runs a fast policy/semantic
    coverage probe (`proactive-worktree.sh verify --test-cmd true`), runs
    `base-check` automatically on any unclassified `Substatus: GATE_FAILURE`
    digest, checks conflict-free upstream integration via
    `git merge-tree
    --write-tree`, checks open-PR and sibling-worktree file
    collisions via
    `check-collisions --include-worktrees --exclude-worktree <wt>`, runs
    `ocr
    delegate preview`, and runs `gitnexus-review`
    (`node .gitnexus/run.cjs
    impact` upstream blast-radius + symbol
    test-reference verification, refreshing a stale index once per repo via
    `analyze --index-only` when Tier 2 is enabled).
  - **Tier 2 (Reviewer Stack & Hard Privacy Boundary):** Strictly skipped when
    `lens == "sentinel"` or `Status: SECURITY_REPORT_ONLY` so security findings
    never leave the host. Otherwise runs `open-code-review`
    (`ocr review
    --audience agent --format json`), `CodeRabbit`
    (`coderabbit auth status
    --agent` +
    `coderabbit review --agent --committed --base-commit <base_sha>`, preserving
    `critical`, `major`, `minor`, `trivial`, and `info` severities), and sparing
    LiveReview
    (`lrc review --no-serve --output json --range
    <base_sha>...HEAD` only
    when `--with-lrc` is requested, CodeRabbit did not complete with 0
    critical/high OCR issues, or GitNexus reports `HIGH` risk with 0
    critical/major/high CodeRabbit+OCR issues — gated to `<= 250` diff LOC,
    `< 1` daily `lrc` run in `judge-shadow-ledger.jsonl`, and
    `lrc usage
    inspect` reporting `can_trigger_reviews: true` with `>= 2000`
    remaining monthly LOC).
  - **Verdicts, Shadow Ledger & Digest Contract:** Appends `0600` JSONL rows to
    `$HOME/.gemini/antigravity/proactive-reports/judge-shadow-ledger.jsonl` and
    `## Judge Evaluation` to the candidate digest. `JUDGE_REJECT` (deterministic
    harness/coverage violation or `base-check` `CAUSED_BY_CHANGE`) writes
    `Action: reject (retired automatically on <YYYY-MM-DD>)` and force-removes
    the rejected worktree and `proactive/*` branch after confirming the ledger
    receipt is on disk. `JUDGE_PASS_ROUTINE` (all tiers clean) and
    `JUDGE_ESCALATE_HUMAN` (findings, degraded reviewer, `--skip-tier2`,
    `sentinel` local boundary, or untested `CRITICAL` blast radius) transition
    clean worktrees to `JUDGED` and emit deterministic
    `Action: promote | reject | expire (default: expire on <YYYY-MM-DD>)` (never
    an open-ended question), while `> 7d` `JUDGED` worktrees auto-expire to
    `EXPIRED` on disk.

  `base-check --repo <name> --worktree <dir> [--digest <path>]` answers the
  question a bare verify exit code cannot: **was this failure caused by the
  candidate, or was base already broken?** It reads `repo_path` alongside
  `repo_name` and `base_sha` from `proactive-meta.json`, splits the repo's
  compound test command on `&&`, re-runs the failing stage once in the candidate
  to catch a flake, then re-runs the stages on a pristine `base_sha` worktree,
  and prints a `VERDICT` of `NO_FAILURE`, `FLAKE_ON_RETRY`,
  `PRE_EXISTING_ON_BASE` (`exit 0`, candidate still promotable, base breakage
  filed separately) or `CAUSED_BY_CHANGE` (`exit 2`, discard the candidate).
  Credentials (`SSH_AUTH_SOCK`, `GH_TOKEN`, `GITHUB_TOKEN`) and `VIRTUAL_ENV`
  are stripped exactly as `verify` strips them, with repo `.venv/bin`
  auto-resolution (`<dir>/.venv/bin` or `<repo_path>/.venv/bin`) prepended to
  `PATH` when a stage does not use `uv run`. No `origin` ref is consulted (the
  comparison is against a local `base_sha`, so it stays valid offline), and
  `--digest` appends a `## Base-Check Classification` section to the `chmod 600`
  report rather than rewriting it. It runs in the `08:35` triage slot, never
  inside the sweep, because a base re-run can double test time and the sweep is
  boxed at 15 minutes. The triage sidecar therefore gains read/write grants on
  the worktrees directory — re-running a suite writes `__pycache__` and
  `.pytest_cache` in place — but deliberately keeps a **reports-only
  `workspace_uris`**: the `PreToolUse` guard classifies a session as a sweep
  from its workspace paths, so adding the worktrees root would upgrade a
  read-mostly review slot into a sweep session able to push and open PRs.

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
# Deploy copy-on-deploy skills, safety hook, runtime scripts, and disabled pilot sidecars
./scripts/antigravity-proactive-ctl.sh install --pilot

# Check runtime + repo readiness (and optionally auto-heal runtime + origin/HEAD + merged worktrees)
./scripts/antigravity-proactive-ctl.sh doctor --all-repos
./scripts/antigravity-proactive-ctl.sh doctor --fix --repo ctrld-sync

# Stage disabled sweep + Judge/triage sidecars (add --stagger for non-overlapping multi-repo weekday slots)
./scripts/antigravity-proactive-ctl.sh stage-repo --repo Seatek_Analysis --stagger

# Run post-sweep Judge evaluation (full Tier 1 + Tier 2 stack, or offline Tier 1 only via --skip-tier2)
# Note: --skip-tier2 runs strictly offline (skips origin refresh, GitHub open-PR collision checks, and Tier 2 reviewers),
# so candidates on remote GitHub-hosted clones escalate as COLLISION_OR_UNVERIFIABLE or TIER2_SKIPPED_OFFLINE until online Judge runs.
./scripts/antigravity-proactive-ctl.sh judge --repo ctrld-sync
./scripts/antigravity-proactive-ctl.sh judge --all-repos --skip-tier2

# Reopen an auto-expired (>7d) judged candidate worktree for fresh promotion review
./scripts/proactive-worktree.sh reopen --worktree "$HOME/.gemini/antigravity/worktrees/<candidate>"

# Run standalone preflight with auto-heal on one repository
./scripts/proactive-worktree.sh preflight --repo abhimehro/ctrld-sync --repo-path "$HOME/dev/ctrld-sync" --auto-heal

# Stage and later clean up a disposable cron canary (defaults to America/Chicago; pass --timezone UTC for UTC isolation)
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

# Ordered rollback (removes sidecars -> removes managed skills -> removes hooks.json & runtime dir last;
# keeps hooks.json / runtime dir if user-edited or referenced by a restored custom hook)
./scripts/antigravity-proactive-ctl.sh disable
```
