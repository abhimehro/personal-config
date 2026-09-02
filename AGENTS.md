# AGENTS.md

This file provides guidance to WARP (warp.dev) when working with code in this
repository.

## Repository intent (what this repo is)

`personal-config` is an “infrastructure as code” repo for a macOS workstation:
dotfiles + automation scripts + launchd agents that manage networking (Control
D/Windscribe), SSH setup, maintenance jobs, and a media pipeline.

Many scripts intentionally modify system state (symlinks in `$HOME`, `launchctl`
agents, DNS/IPv6 settings, services). Prefer reading scripts first and using the
repo’s verify/test scripts after changes.

## Common commands (local development)

### Bootstrap / install (idempotent)

```bash
# Full bootstrap (macOS-only): dotfiles + maintenance + network tools + media staging
./setup.sh

# Install/sync dotfiles only (interactive)
./scripts/install_all_configs.sh
```

### Sync + verify symlinked configs

```bash
# Create/update symlinks from repo → home directory
./scripts/sync_all_configs.sh

# Verify symlinks, targets exist, and key perms (e.g., SSH files)
./scripts/verify_all_configs.sh

# Focused SSH verification
./scripts/verify_ssh_config.sh
```

### Network mode switching (Control D ⇄ Windscribe)

Primary entrypoint is `scripts/network-mode-manager.sh`.

Profile modes (protocol × IPv6 policy):

| Mode        | Protocol | IPv6 | When                                               |
| ----------- | -------- | ---- | -------------------------------------------------- |
| `doh-ipv4`  | DoH      | Off  | Windscribe IPv4-only / static IP (leak prevention) |
| `doh3-ipv6` | DoH3     | On   | Standalone Control D (default)                     |
| `doh-ipv6`  | DoH      | On   | Windscribe IPv6-capable WireGuard locations        |

**Stable path (as of 2026-07-09):** Control D CD Mode API returns numeric
`exclude`; ctrld v1.5.3 still cannot unmarshal it. **Intentional temporary
architecture:** profile-aware Local Config with
`https://dns.controld.com/<profile_id>` (NOT free DNS / `/free`). This is not an
antipattern — it uses real profile IDs. CD Mode (`--cd`) stays broken until
upstream fixes the API or ships flexible JSON. Repair defaults to Local Config
(no 45s CD thrash); force a CD retry with `--cd-mode`.

**CD Mode (optional / broken until upstream):**
`ctrld service start --cd <profile_id> --proto doh|doh3 --config=/etc/controld/ctrld.toml --skip_self_checks`.
Never pass `--listen` with `--cd` (Lesson 0do). Never use static free-DNS toml.

**API schema (Lesson 0dr):** `/etc/controld/ctrld.log` →
`cannot unmarshal … exclude` / `failed to fetch resolver config` → CD Mode
KeepAlive thrash. Prefer Local Config; set `FALLBACK=1`.
`CONTROLD_PREFER_LOCAL=1` or default `CONTROLD_SKIP_CD_DEFAULT=1` skips CD Mode.

**One binary:** Keep Homebrew `/opt/homebrew/bin/ctrld` (v1.5.3). LaunchDaemon
already points there. Quarantine shadowed `/usr/local/bin/ctrld` (dev builds):
`sudo ./scripts/controld-dedupe-binary.sh`.

**Repair / status:**

```bash
# Free :53 if limactl holds it (Colima). Permanent: Lima override, not only colima.yaml.
./scripts/free-port53-for-controld.sh --stop-colima

# Dedupe CLI + writable status file (once)
sudo ./scripts/controld-dedupe-binary.sh

# Stable repair: Local Config directly (DHCP fail-safe; dig before pin). No CD thrash.
sudo ./scripts/repair-controld-keepalive.sh --restart privacy
# Optional: force CD Mode attempt (expected to fail until upstream fixes API)
# sudo ./scripts/repair-controld-keepalive.sh --restart privacy --cd-mode

./scripts/controld-status.sh          # WORKING / BROKEN, one screen
dig @127.0.0.1 google.com +short +time=2
# privacy expect: endpoint = 'https://dns.controld.com/<CONTROL_D_PRIVACY_RESOLVER_ID>' (never /free)
# cat /etc/controld/status   # world-readable; active_profile may need sudo until chmod 644
```

**Live status (confirmed 2026-07-09 after
`sudo ./scripts/controld-dedupe-binary.sh`):** `/etc/controld/status` =
**WORKING / local_fallback**; dig @127.0.0.1 resolves; single brew **v1.5.3**
(`/opt/homebrew/bin/ctrld`, `/usr/local/bin/ctrld` → symlink). Dedupe left the
healthy listener alone (no DNS restart). CD Mode remains broken upstream; Local
Config with real profile IDs is the stable path.

**Binary note:** brew `ctrld` 1.5.3 is fine for Local Config. Upgrade alone does
**not** fix CD Mode numeric `exclude` until Control D ships flexible JSON.
**Colima + Control D coexistence:** patch
`~/.colima/_lima/_config/override.yaml` (`guestIPMustBeZero: false` for guest
DNS) via `--patch-colima-ignore`. Do **not** rely on appending `portForwards`
only to `~/.colima/default/colima.yaml`.

**Installed manager:** `/usr/local/bin/controld-manager` must have
`CONTROLD_REPO` in `/etc/controld/controld.env` (set by
`scripts/setup-controld.sh`). Prefer repo paths:
`./scripts/network-mode-manager.sh` and
`./controld-system/scripts/controld-manager`.

```bash
# Show current status
./scripts/network-mode-manager.sh status

# Switch to Control D DNS mode (profiles: browsing|privacy|gaming) → doh3-ipv6
./scripts/network-mode-manager.sh controld browsing

# Explicit DoH + IPv6 off (leak prevention without VPN)
./scripts/network-mode-manager.sh controld privacy doh

# Explicit DoH + IPv6 on (standalone doh-ipv6)
CONTROLD_IPV6=enable ./scripts/network-mode-manager.sh controld privacy doh

# Switch to Windscribe-only mode (Control D stopped, DNS resets, IPv6 off)
./scripts/network-mode-manager.sh windscribe

# Combined mode (Windscribe + Control D). Pre-connect defaults to doh-ipv4;
# after connect, reconcile / windscribe-connect auto-upgrades to doh-ipv6
# when the tunnel has global IPv6.
./scripts/network-mode-manager.sh windscribe privacy

# Force IPv6 policy (bash / zsh — prefix assignment works):
WINDSCRIBE_IPV6=1 ./scripts/network-mode-manager.sh windscribe privacy   # force doh-ipv6
WINDSCRIBE_IPV6=0 ./scripts/network-mode-manager.sh windscribe privacy   # force doh-ipv4

# Force IPv6 policy (fish — use env; prefix assignment is not valid fish syntax):
env WINDSCRIBE_IPV6=1 ./scripts/network-mode-manager.sh windscribe privacy
env WINDSCRIBE_IPV6=0 ./scripts/network-mode-manager.sh windscribe privacy
# Same for windscribe-connect:
#   IPv4/static (Dallas): env WINDSCRIBE_IPV6=0 ./scripts/windscribe-connect.sh privacy
#   IPv6 (Atlanta/Peachtree non-static):
#   env WINDSCRIBE_IPV6=1 ./scripts/windscribe-connect.sh privacy Atlanta
```

Soft verify noise (expected, not failures):

- `whoami.control-d.net` timeout/empty — soft check only; Control D can still be
  ACTIVE.
- `AAAA example.com` empty — expected when mode is `doh-ipv4` (IPv6 Off) or the
  path has no IPv6; warning only.

Verification/regression:

```bash
# Verify current state (profile-aware for controld)
./scripts/network-mode-verify.sh controld browsing
./scripts/network-mode-verify.sh windscribe

# Full regression: Control D → Windscribe → Combined
./scripts/network-mode-regression.sh browsing

# Mode matrix (privacy)
./scripts/validate-controld-ipv6-modes.sh privacy

# Makefile shortcut (runs regression)
make control-d-regression
```

Fish helpers (`configs/.config/fish/functions/nm-*.fish`, abbrs in
`config.fish`) `cd` to the repo and call `network-mode-manager.sh` /
`windscribe-connect.sh`:

| Abbr                        | Behavior                                              |
| --------------------------- | ----------------------------------------------------- |
| `nmp` / `nmb` / `nmg`       | Standalone Control D (default `doh3-ipv6`)            |
| `nmpd` / `nmbd` / `nmgd`    | DoH + IPv6 off (`doh-ipv4`)                           |
| `nmp6` / `nmb6` / `nmg6`    | DoH + IPv6 on (`doh-ipv6` via `CONTROLD_IPV6=enable`) |
| `nmvp` / `nmvb` / `nmvg`    | Windscribe + Control D (auto IPv6)                    |
| `nmvp4` / `nmvb4` / `nmvg4` | Same, force `WINDSCRIBE_IPV6=0`                       |
| `nmvp6` / `nmvb6` / `nmvg6` | Same, force `WINDSCRIBE_IPV6=1`                       |

Pass location for VPN abbrs: `nmvp4 Dallas` (static IPv4) or `nmvp6 Atlanta`
(IPv6 non-static / Peachtree). Defaults: Dallas static when IPv6 is off/auto;
Atlanta non-static when `WINDSCRIBE_IPV6=1`. Reload with `exec fish`.

### LaunchAgents (2026-07-09 audit)

- Archived (do not re-enable without review):
  `launch-agents/archived/com.personal.ctrld-network-watch.plist` (was invalid
  `scutil --watch` crash-loop), permute agent.
- SecOps agents restored to in-repo stubs where skill paths were missing.
- `sync-launchagents` only covers `media-streaming/launchd` + `launch-agents` —
  maintenance plists are a separate install path (`maintenance/install.sh`).
- Historical monitor log: `~/Public/Scripts/controld_monitor.log`; LaunchDaemon
  is vendor `system/ctrld` (not a custom `/Library/LaunchDaemons/ctrld.plist` we
  maintain long-term).

### Media streaming / Jellyfin

See `media-streaming/jellyfin/MIGRATION_PLAN.md`. Phase 1 = **native** Homebrew
cask + LaunchAgent; credentials from local bootstrap; VideoToolbox via Homebrew
`ffmpeg` (not `jellyfin-ffmpeg`) — **do not** `brew install jellyfin-ffmpeg`.
API key soft-skip in `validate-jellyfin.sh` when unset. Colima Jellyfin deferred
(email-security-pipeline shares the VM).

### Maintenance system (manual run + status)

The maintenance system is documented in `maintenance/README.md`.

```bash
# Run specific maintenance actions via the orchestrator
./maintenance/bin/run_all_maintenance.sh health
./maintenance/bin/run_all_maintenance.sh quick

# Check scheduled agents
launchctl list | grep com.abhimehrotra
```

### Media streaming pipeline

High-level docs live in `media-streaming/README.md`. Setup is staged by
`setup.sh` (templates + LaunchAgents).

```bash
# Verify media automation agents (names vary; grep is the easiest entrypoint)
launchctl list | grep -E '(media|alldebrid|speedybee)'

# Fish shortcuts (see media-streaming/README.md)
media-status
media-restart
gaming-mode status   # suspend/restore full stack for GeForce NOW
```

Mount notes (2026-07-30):

- `media-streaming/scripts/mount-media.sh` waits up to 60s for the fuse-t
  process before `rclone mount` (login race with FSKit).
- `gaming-mode` uses `launchctl bootout` / `bootstrap`+`kickstart` because the
  media plists are KeepAlive.

### Lint / formatting (Trunk)

This repo is wired for Trunk via `.trunk/trunk.yaml` (shellcheck, shfmt, ruff,
black, prettier, trufflehog, etc.).

```bash
# Run all configured linters
make lint

# Correctness-only regression gate (SC2155/SC2145; no Trunk required)
make lint-errors

# Auto-format (where supported)
make lint-fix

# Or invoke trunk directly
trunk check --all
trunk fmt
```

> **ShellCheck dual-config note:** Local `shellcheck` uses `.shellcheckrc`
> (defaults, disables SC1091/SC1090) while Trunk/CI uses
> `.trunk/configs/.shellcheckrc` (`enable=all`, disables SC2154/SC1091/SC1090),
> so CI will report more issues than direct `shellcheck`. To match CI behavior
> locally, run `trunk check <file>` instead of calling `shellcheck` directly.

### Tests

There isn’t a single “test runner” script; most tests are directly executable
shell scripts under `tests/`.

Run a single shell test:

```bash
bash tests/test_ssh_config.sh
bash tests/test_network_mode_manager.sh
```

Run all shell tests:

```bash
make test
```

Run all tests (shell + Python):

```bash
make test-all
```

Run a single Python test module:

```bash
python3 -m unittest tests.test_path_validation
```

Run Python tests only:

```bash
make test-python
```

### Benchmarks

```bash
# Requires hyperfine
make benchmark

# Or run the benchmark runner directly
./tests/benchmarks/benchmark_scripts.sh all
```

### PR Review Agent (preflight gate)

Before running a bot PR triage/review session, preflight must pass. See
`docs/automated-pr-review-agent.md` and
`docs/github-app-pr-automation-checklist.md`.

```bash
# Run preflight gate and print next steps (uses tasks/pr-review-agent.config.yaml if present)
./scripts/run-pr-review-session.sh

# Preflight with explicit config
./scripts/run-pr-review-session.sh --config tasks/pr-review-agent.config.yaml

# Preflight only (read-only), default repos
./scripts/preflight-gh-pr-automation.sh --config tasks/pr-review-agent.config.yaml
```

### CodeScene failure remediation during PR sessions

When PR triage/review/salvage runs encounter a CodeScene failure, post this
command on the affected PR before final defer/salvage decisions:

```bash
/cs-agent skill:fix-code-health-degradations
```

Canonical policy references:

- `docs/automated-pr-review-agent.md`
- `docs/automated-pr-salvage-agent.md`
- `docs/pr-visual-recap-agent-backends.md` — optional sticky visual/plan summary
  on PRs (OpenCode + Mistral). Agents should **read** an existing recap when
  present; do not re-trigger on every triage (quota). Refresh via label
  `visual-recap` only when needed.

### Stacked PRs during review/salvage sessions (`gh-stack`)

The `github/gh-stack` `gh` extension is installed via
`scripts/install_gh_extensions.sh`; its usage skill is tracked at
`.agents/skills/gh-stack/SKILL.md` (mirrored to `.claude/skills` and
`.windsurf/skills`). Load it before doing any of the below.

`/purge-anthropies` is vendored at `.agents/skills/purge-anthropies/` (mirrored
into `.claude/skills`, `.cursor/skills`, `.windsurf/skills`, and
`.devin/skills`). Local CLI: `pipx install -e ~/dev/anthropies` then
`anthropies clean|humanize|inspect`. Claude/Gemini hosts must clean and
print-prompt only; do not rewrite with those models.

Use `gh stack` during Review (Phase 1) and Salvage (Phase 2) sessions to break
the **post-merge conflict cascade** (see "Post-merge conflict cascade" heuristic
in `docs/automated-pr-review-agent.md` and the domino-effect guidance in
`docs/automated-pr-salvage-agent.md`): PRs that touch the same hot file
frequently flip `DIRTY` one after another as siblings merge ahead of them.
Rather than merging or salvaging each sibling independently and re-triaging the
fallout, chain the related PRs/branches into a stack so each one is rebased on
the branch below it:

```bash
# Link existing open PRs (same repo, overlapping files) into a stack, bottom to top
gh stack link <pr-bottom> <pr-middle> <pr-top>

# Or, when salvaging, create the replacement branches as a chain from the start
gh stack init salvage/<repo>-<a> salvage/<repo>-<b> salvage/<repo>-<c>

# Merge a linked stack bottom-to-top once reviewed (never run unattended by Review/Salvage agents)
gh stack merge --yes
```

Agent-specific rules:

- **Review Agent (Phase 1):** may use `gh stack link` to group already-open
  sibling PRs that collide on the same file(s) before merging, then merge the
  stack with `gh stack merge --yes` instead of merging them one at a time and
  re-checking mergeable state after each. Still subject to all existing merge
  gates per-PR.
- **Salvage Agent (Phase 2):** when the salvage queue contains multiple
  deferred/escalated PRs that touch the same files or the same consolidation
  category, build the replacement branches with `gh stack init` (chained)
  instead of independent branches off `main`, then `gh stack submit --auto` to
  open them all as **draft** PRs. This preserves the "never merge autonomously"
  boundary (S1) while eliminating the need for each salvage branch to re-resolve
  conflicts introduced by its siblings. Stage 2 still must not merge those
  drafts. After create, re-read `isDraft` (lesson **0gd**), CAS-write a ledger
  item for each replacement PR, and leave merge to Stage 1 routine re-ingest,
  Stage 3 after approved calibration, or a human. See
  `docs/automated-pr-lifecycle.md` (Merge authority for Stage 2 outputs) and
  `docs/pr-lifecycle-pipeline-run-retro-2026-08-20.md`. Cron session reports
  belong on the shared `pr-lifecycle-docs-YYYYMMDD` lineage (Stage 1 lands it);
  do not open a third overlapping `tasks/*` docs PR. Notion stays human packets.
- Always run `gh stack rebase --no-trunk` immediately before
  `gh stack submit`/`merge`; `gh stack init` with multiple branch names creates
  them off trunk in parallel, not chained, until the first rebase.

For a one-page command cheat sheet, see
[docs/gh-stack/quick-reference.md](docs/gh-stack/quick-reference.md). When in
doubt during a session, run this quick verification before submitting or
merging:

- [ ] `gh stack view` shows every layer with a linear chain (no forks, no
      `needsRebase=true`).
- [ ] Each PR's `baseRefName` is the layer directly below it (the bottom targets
      `main`).
- [ ] You are about to merge only the **top** layer, via `gh stack merge --yes`
      (or the merge-async REST API for API-only sessions).
- [ ] A human has approved the merge (boundary S1); agents stop at opening
      drafts.

**Merging a stack (Lesson 0ez — learned the hard way on 2026-07-31):** stacked
PRs **cannot** be merged with `gh pr merge`, GraphQL `mergePullRequest`, or the
ordinary `PUT /repos/{owner}/{repo}/pulls/{n}/merge` (even with
`Prefer: respond-async`). They fail with "part of a stack… use the asynchronous
merge REST API". Use whichever path matches your environment:

- **Has the `gh` extension** (local / provisioned runner):
  `gh stack merge --yes`.
- **API-only agent sessions** (Cursor cloud, MCP, bare `GH_TOKEN`):

  ```bash
  # Merging the TOP of the stack merges every lower layer into the ultimate base
  gh api -X PUT repos/$REPO/pulls/$TOP_PR/merge-async -f merge_method=squash

  # Poll until status=merged (uuid lives under .details.uuid)
  gh api repos/$REPO/pulls/$TOP_PR/merge-async/$UUID
  ```

  Retry once if it fails with "Base branch was modified" (sibling merges still
  settling). **Auto-merge is unsupported for stacks** — never queue one and walk
  away.

#### Recovering from a broken stack

If a layer is merged out of order or a stack goes stale against `main`:

- **Accidental bottom-layer merge:** GitHub locks a PR once merged (it cannot be
  reopened), and auto-retargets the next layer to `main`. The stack survives as
  the remaining open PRs; do **not** force-push a collapsed local rebase over
  them. Reset your local branches to the remote tips instead
  (`git branch -f <branch> origin/<branch>`), then decide whether a replacement
  bottom PR is even needed (it is usually empty if the content already reached
  `main`).
- **Layer merged but immediately reverted:** the net diff on `main` is zero, so
  the surviving stack layers still carry the real content. Verify with
  `git diff --name-only origin/main <top-branch>` before assuming anything was
  lost.
- **Stack went stale / all content already on `main`:** a plain `git rebase`
  will drop the now-empty commits and collapse the chain. Prefer rebuilding a
  fresh stack from current `main` over resurrecting a collapsed one.
- **Before any recovery,** confirm the automation-facing guidance is still
  intact on `main` (skill files, this AGENTS.md section, the review/salvage doc
  notes, and Lessons 0ez/0fb in `tasks/lessons.md`) so agents are unaffected
  while you repair the test stack.

## Big-picture architecture (how the pieces fit)

### 1) Config-as-code via symlink orchestration

Core pattern: keep authoritative config files in-repo and symlink them into the
real locations.

Key entrypoints:

- `scripts/sync_all_configs.sh`: creates/updates symlinks and backups when
  appropriate.
- `scripts/verify_all_configs.sh`: verifies links/targets and checks a few
  invariants (e.g., SSH perms, fish functions presence).

This is the backbone that makes “git pull” translate into a live system update.

### 2) Network mode manager (DNS + VPN state machine)

The networking subsystem is intentionally centralized so that “mode switching”
is not a series of manual steps.

Key components:

- `scripts/network-mode-manager.sh`: orchestrates the state transition.
- `scripts/network-mode-verify.sh`: asserts the machine is in the expected state
  (Control D active vs Windscribe ready), including DNS resolver checks and some
  profile/DoH3 assertions.
- `scripts/network-mode-regression.sh` + `Makefile`: repeatable end-to-end
  regression to catch drift.
- `controld-system/scripts/controld-manager`: low-level Control D profile
  management; `network-mode-manager.sh` delegates to this.
- `scripts/macos/ipv6-manager.sh`: toggled as part of mode switching.

If you’re debugging a network issue, start from the manager → verify script
outputs before changing anything.

### 3) Automated maintenance (launchd + modular scripts)

Maintenance is structured as:

- `maintenance/bin/*`: task scripts and orchestrators.
- `maintenance/install.sh` (invoked by `setup.sh`): installs/boots LaunchAgents.
- Logs are written under `~/Library/Logs/maintenance/` (see
  `maintenance/README.md`).

The important architectural idea: tasks are meant to be launchd-driven and
observable via logs and `launchctl`.

### 4) Media streaming pipeline (agents + scripts)

The media pipeline is split into:

- Setup + configuration templates (e.g., rclone template seeded by `setup.sh`).
- Automation via LaunchAgents (installed if present).
- Operational scripts in `media-streaming/scripts/` (sync, rename/finalize,
  repair, mount, gaming-mode).

The docs in `media-streaming/README.md` describe the intended “zero-click” flow
and the responsibilities of each agent/script. Day-to-day ops:

- `media-status` / `media-restart` / `media-logs` (Fish)
- `gaming-mode on|off|status` to pause the stack for latency-critical gaming
- `mount-media.sh` FSKit gate + stale-mount safeguards (see README)

### 5) Code quality + automation workflows

- Trunk is the “local lint hub” (`.trunk/trunk.yaml`).
- CI additionally runs complexity checks (ShellCheck + radon) and a Trunk check
  (see `.github/workflows/code-quality.yml`).
- `.github/workflows/README.md` documents additional agentic workflows and notes
  that `.md` workflow sources compile to `.lock.yml` (compiled files should not
  be edited by hand).

## Repo-specific agent behavior (important excerpts from existing rules)

If you are operating as an agent in this repo, align with:

- `.cursorrules`: security-first collaboration style (state approach before
  coding, comment _why_, provide a handoff summary after changes) + hard
  boundaries (don’t implement auth/payment/db schema changes without explicit
  user approval; don’t run destructive commands without confirmation).
- `.github/copilot-instructions.md`: “development partner” protocol
  (before/while/after coding rhythm).

## Writing Tests

Detailed patterns, mock recipes, and a copy-paste test skeleton live in
[`docs/TESTING.md`](docs/TESTING.md). The key points:

- **`$MOCK_BIN` / PATH injection** — create a temp dir of fake executables and
  prepend it to `PATH` before running the script under test. Most shell unit
  tests in `tests/` use this pattern.
- **Log-file assertion** — write mock binaries that record their invocations to
  a file in `$TEST_DIR`, then `grep` that file to assert the right command and
  arguments were used.
- **Mock `HOME` isolation** — set `HOME="$TEST_DIR/home"` so scripts that write
  to `~/Library/Logs/` don't touch real user data and don't collide between
  parallel runs.
- **Script-patching via `sed`** — when a script hardcodes a dependency path
  (e.g. `IPV6_MANAGER=…`), copy the script to `$TEST_DIR` and patch with `sed`.
  Branch on `$(uname -s)` for `sed -i ''` (macOS) vs `sed -i` (Linux).
- **Capturing expected-failure output under `set -e`** — use
  `$(cmd 2>&1 || true)` or capture the exit code with `|| actual=$?` to prevent
  `set -euo pipefail` from aborting the test on a deliberately failing command.
- **Credential file parsing** — use `parse_cred_value()` from
  `tests/lib/test_helpers.sh` when reading values from media-server credential
  files (`KEY='value'` format); never use raw `cut -d'=' -f2-` on a credential
  line (it returns quoted values like `'infuse'` instead of `infuse`).

**Tests that skip on Linux/CI** (not bugs — each file contains an early-exit
skip guard that prints `SKIP:` and exits 77):

| Test                               | Skip Reason                       | Guard                |
| ---------------------------------- | --------------------------------- | -------------------- |
| `test_config_fish.sh`              | Needs `fish` shell                | `command -v fish`    |
| `test_ssh_config.sh`               | Needs 1Password agent socket      | `uname -s == Darwin` |
| `test_security_manager_restore.sh` | Uses BSD `sed -i ''` (macOS only) | `uname -s == Darwin` |

See [`docs/TESTING.md`](docs/TESTING.md) for the full guide including a
copy-paste test skeleton and a known-limitations table.

## Cursor Cloud specific instructions

This is a macOS-focused dotfiles/IaC repo. There are no web services or
databases to start. The dev workflow is: edit scripts, lint, and run tests.

### Key services and how to run them

| What                       | Command                                          | Notes                                                                                                                                                                                                            |
| -------------------------- | ------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Cursor Cloud hook sync     | `make cursor-cloud-hooks`                        | Copies `scripts/cursor_cloud_agent_*.sh` into `~/.cursor/agent-hooks/*` when **both** `pre-commit.cursor` and `commit-msg.cursor` exist as regular files; refuses symlink hook paths (`install(1)`, TOCTOU-safe) |
| Shell tests only           | `make test`                                      | Fastest full suite; 47 `tests/test_*.sh`, 3 expected macOS-only skips (fish, BSD sed, 1Password socket)                                                                                                          |
| Smoke tests (pre-commit)   | `make test-quick`                                | 3 fast cross-platform tests; ~5s; defined in Makefile `test-quick` target                                                                                                                                        |
| All tests (shell + Python) | `make test-all`                                  | Runs shell tests in parallel, then Python tests. Platform-specific shell tests emit `SKIP:` and exit 77 on Linux/CI.                                                                                             |
| Single Python module       | `python3 -m unittest tests.test_path_validation` | Mostly stdlib; some tests (e.g. `test_repository_automation_common.py`) need `pip install -r requirements.txt` (`pyyaml==6.0.3`, `jsonschema==4.26.0`)                                                           |
| Python tests only          | `make test-python`                               | Mostly stdlib; install via `python3 -m pip install -r requirements.txt` (`pyyaml==6.0.3`, `jsonschema==4.26.0`) for the full suite                                                                               |
| Lint (all)                 | `make lint`                                      | Trunk downloads its own tool versions on first run                                                                                                                                                               |
| Lint (correctness gate)    | `make lint-errors`                               | SC2155/SC2145 only; exits non-zero on violations. Fast regression gate.                                                                                                                                          |
| Format                     | `make lint-fix`                                  | Auto-fixes where supported                                                                                                                                                                                       |
| Auth hygiene (optional)    | `make verify-credentials`                        | Runs `scripts/verify-repo-auth-hygiene.sh` (trufflehog `--only-verified` + password grep)                                                                                                                        |

### Non-obvious caveats

- **`make test` vs `make test-all`**: `make test` runs shell tests only (faster
  for iteration). `make test-all` additionally runs Python tests. Use
  `make test-quick` for pre-commit smoke checks.
- **Trunk first-run latency**: The first `trunk check` or `trunk fmt` invocation
  downloads shellcheck, shfmt, ruff, black, prettier, etc. into `.trunk/`.
  Subsequent runs are fast. The update script installs the Trunk launcher, but
  tool downloads happen lazily.
- **`requirements.txt`**: The root `requirements.txt` pins `pyyaml==6.0.3` and
  `jsonschema==4.26.0`, which are needed by the full test suite (e.g.,
  `tests/test_repository_automation_common.py` exercises
  `.github/scripts/repository_automation_common.py`). The Devin environment
  blueprint installs this dependency automatically; otherwise run
  `python3 -m pip install -r requirements.txt`.
- **`package.json` is empty**: The root `package.json` is `{}` — it exists as a
  Trunk runtime anchor for Node-based linters (prettier, markdownlint). Do not
  run `npm install`.
- **macOS-specific test skips on Linux**: `test_config_fish.sh`,
  `test_ssh_config.sh`, and `test_security_manager_restore.sh` emit a `SKIP:`
  message and exit with code 77 on Linux/CI. The test runner treats this as a
  skip, not a failure.
- **`setup.sh` is macOS-only**: Do not run `./setup.sh` on Linux — it calls
  `launchctl`, Homebrew, and macOS system utilities.

### Cursor Cloud pre-commit secret scan

Cursor injects `pre-commit.cursor` and `commit-msg.cursor` (under
`~/.cursor/agent-hooks/<workspace-hash>/`) to scan staged diffs and the commit
message for values of secrets listed in `CLOUD_AGENT_INJECTED_SECRET_NAMES`.
Secret **labels** may include spaces (e.g. `GitHub SSH Key`); both hooks must
use `printenv` for lookup, not bash `${!var}` indirect expansion (which errors
with `invalid variable name`). Canonical copies:
`scripts/cursor_cloud_agent_pre_commit.sh` and
`scripts/cursor_cloud_agent_commit_msg.sh` — keep them aligned with the injected
hooks when debugging Cloud Agent commits.

**Fresh Cloud workspaces** may ship older injected copies. After clone, run
**`make cursor-cloud-hooks`** (or
`./scripts/install_cursor_cloud_agent_hooks.sh`) once per session to overwrite
the injected hooks with the canonical scripts from this repo. The installer only
updates a directory when **both** hook files are already present as **regular**
(non-symlink) files—matching Cursor’s layout—and uses `install -m 0755` so
symlink destinations are never followed. To target one hash directory:
`CURSOR_AGENT_HOOKS_DIR=~/.cursor/agent-hooks/<hash> ./scripts/install_cursor_cloud_agent_hooks.sh`.

## Learned User Preferences

- Stage 1/2/3 names the daily PR-lifecycle cron. In the gh-stack section, Phase
  1/Phase 2 are Review/Salvage _sessions_, and boundary S1 means those session
  agents do not merge a stack unattended. S1 does not revoke Stage 1's routine
  merge/close of bot-authored non-sensitive PRs.
- Stage 2 PR salvage must never autonomously merge, approve, close, or request
  review; open draft salvage or infra-fix PRs and leave merge decisions to a
  human. Stage 1 holds routine merge and close authority for bot-authored
  non-sensitive work.
- Security, auth, secrets, and trust-boundary PRs stay escalated for human
  review even when CI is green.
- Ordinary human-authored PRs stay untouched by the three-stage pipeline. Stage
  3 files a one-question packet only when sticky security, HUMAN, or real
  platform judgment is irreducible. Jules/Bolt/Palette file-overlap clusters are
  Stage 1 canonical-pick, not packets.
- Stage 3 calibration reached seven successful runs on 2026-08-26. Human
  `APPROVED` is recorded in the runtime ledger (`approved_by: abhimehro`).
  Bounded completion is on. Disable the calibration Dashboard automation and
  enable the completion variant after pasting the updated prompts. Resetting
  stale calibration to `REPORT_ONLY` / count 0 is not a successful run.
- Grok Bot **PR Desk** (`docs/grok-bot/`) is a human-facing filter, not a fourth
  lifecycle stage. It must not merge, approve, close, comment, create GitHub
  issues, CAS-write the ledger, launch Cloud Agents, or write
  `tasks/*-session-reports.md`. Digests cap at five human items. Health must
  flag Stage 2 EMPTY_INTAKE while salvage-eligible work remains.

## Learned Workspace Facts

- Sibling Bolt/Jules PRs that both touch `.jules/bolt.md` often conflict on the
  journal only after one merges; salvage remaining source changes and resolve
  the journal by taking `main`'s `.jules/bolt.md` (Lesson 0cs).
- Multi-repo cloud PR sessions often leave dirty tracked
  `seatek_series_correction.egg-info/` files under
  `series_correction_project_updated` after editable installs; restore or
  discard those changes and do not commit them.
- Runtime PR-lifecycle state is
  `automation/pr-lifecycle-ledger:pr-lifecycle-ledger.yaml`, written with
  `github_contents_api` CAS (blob-SHA precondition).
  `tasks/pr-lifecycle-ledger.yaml` is a bootstrap pointer only; docs PRs on
  `main` must not rewrite the ledger.
- The three-stage pipeline covers seven repos (`personal-config`, `ctrld-sync`,
  `email-security-pipeline`, `Seatek_Analysis`,
  `Hydrograph_Versus_Seatek_Sensors_Project`,
  `series_correction_project_updated`, `repoprompt-ce`). Stage 1 inventories at
  most 80 items and **reselects** SHA-unchanged items that are still
  Stage-1-executable (MERGEABLE green BOT, canonical-pick clusters, elapsed
  close-candidates, Stage 3 bounce-backs, salvage-eligible CONFLICTING/DIRTY
  BOT). Product-mutation cap is 40 so daily drain exceeds arrivals. Queuing a
  Stage 2 work item is ledger bookkeeping. Unchanged SHA with an unexpired
  non-executable next_action is skipped. A changed base/head SHA invalidates
  prior evidence and returns the item to Stage 1. Stage 2 completes at most five
  work items per run; empty intake is a short record and stop unless
  salvage-eligible remainder exists (`EMPTY_INTAKE_STARVATION`, still no
  invented recoveries).
- Stage 2 work-item IDs use `s2-YYYYMMDD-...`; Stage 3 ledger events use
  `evt-s3-YYYYMMDD-...` (`ACKNOWLEDGEMENT`, `HANDOFF`, `CALIBRATION`).
- RepoPrompt CE salvage that needs Swift or `make guardrails` cannot complete on
  Linux cloud agents; leave `HOLD_PLATFORM` rather than retrying on Linux.
  `HOLD_PLATFORM` does **not** block Stage 1 from squash-merging a BOT PR whose
  required GitHub checks are already green.
- `personal-config` routine merges use the Trunk queue, not a raw GitHub squash.

## Agent shell (POSIX for coding agents)

Login shell stays **Fish**. Coding agents should not be given raw Fish as their
command shell.

### Local command pattern

```bash
agent-zsh -c '<command>'    # primary
agent-bash -c '<command>'   # fallback
agent-term-doctor           # diagnostics
agent-session               # doctor then interactive agent-zsh
```

Launchers live in-repo under `configs/bin/agent-*` (synced to `~/bin` on the
Mac). Profiles: `configs/.config/agent-shell/`. Prefer non-interactive-safe env:
`PYTHONUNBUFFERED=1`, `PAGER=cat`, `GIT_PAGER=cat`.

### Host-specific notes

| Host                    | Configure where          | Auto-uses agent-zsh?                     |
| :---------------------- | :----------------------- | :--------------------------------------- |
| Cursor IDE              | User + terminal profiles | Yes, when default/automation profile set |
| Cursor CLI              | + this file              | No — prefix commands                     |
| Mistral Vibe            | + this file              | No — prefix commands                     |
| Claude Code             | + repo docs              | No — prefix commands                     |
| Codex                   | + repo docs              | No — prefix commands                     |
| Devin cloud             | (Ubuntu bash)            | N/A (no Fish on VM)                      |
| Antigravity/Gemini      | + repo                   | No — prefix commands                     |
| Raycast Script Commands | shebang on each script   | N/A if shebang is bash/zsh               |
| Raycast AI Terminal     | instruction / wrapper    | No — prefix or wrapper                   |

### Rules

- Agents do **not** auto-select these launchers unless the host tool is
  configured
- Do **not** change the macOS login shell away from Fish
- Prefer absolute or PATH-resolved over assuming Fish abbreviations
- Full matrix:
  [`docs/AGENT_SHELL_CONFIG_MATRIX.md`](docs/AGENT_SHELL_CONFIG_MATRIX.md)
- Launcher details:
  [`configs/.config/agent-shell/README.md`](configs/.config/agent-shell/README.md)
- Raycast: [`docs/RAYCAST_AGENT_SHELL.md`](docs/RAYCAST_AGENT_SHELL.md)
