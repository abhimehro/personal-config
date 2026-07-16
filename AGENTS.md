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
# privacy expect: endpoint = 'https://dns.controld.com/6m971e9jaf' (never /free)
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
#   env WINDSCRIBE_IPV6=0 ./scripts/windscribe-connect.sh privacy Atlanta
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

Fish helpers (`configs/.config/fish/functions/nm-*.fish`, abbrs in `config.fish`)
`cd` to the repo and call `network-mode-manager.sh` / `windscribe-connect.sh`:

| Abbr | Behavior |
| ---- | -------- |
| `nmp` / `nmb` / `nmg` | Standalone Control D (default `doh3-ipv6`) |
| `nmpd` / `nmbd` / `nmgd` | DoH + IPv6 off (`doh-ipv4`) |
| `nmp6` / `nmb6` / `nmg6` | DoH + IPv6 on (`doh-ipv6` via `CONTROLD_IPV6=enable`) |
| `nmvp` / `nmvb` / `nmvg` | Windscribe + Control D (auto IPv6) |
| `nmvp4` / `nmvb4` / `nmvg4` | Same, force `WINDSCRIBE_IPV6=0` |
| `nmvp6` / `nmvb6` / `nmvg6` | Same, force `WINDSCRIBE_IPV6=1` |

Pass location for VPN abbrs (e.g. `nmvp6 Atlanta`). Reload with `exec fish`.

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
launchctl list | grep maintenance
```

### Media streaming pipeline

High-level docs live in `media-streaming/README.md`. Setup is staged by
`setup.sh` (templates + LaunchAgents).

```bash
# Verify media automation agents (names vary; grep is the easiest entrypoint)
launchctl list | grep -E '(media|alldebrid|speedybee)'
```

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
  repair).

The docs in `media-streaming/README.md` describe the intended “zero-click” flow
and the responsibilities of each agent/script.

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
| Shell tests only           | `make test`                                      | Fastest full suite; 31 tests, 3 expected macOS-only skips (fish, BSD sed, 1Password socket)                                                                                                                      |
| Smoke tests (pre-commit)   | `make test-quick`                                | 3 fast cross-platform tests; ~5s; defined in Makefile `test-quick` target                                                                                                                                        |
| All tests (shell + Python) | `make test-all`                                  | Runs shell tests in parallel, then Python tests. Platform-specific shell tests emit `SKIP:` and exit 77 on Linux/CI.                                                                                             |
| Single Python module       | `python3 -m unittest tests.test_path_validation` | Mostly stdlib; some tests (e.g. `test_repository_automation_common.py`) need `pip install pyyaml`                                                                                                                |
| Python tests only          | `make test-python`                               | Mostly stdlib; install `pyyaml` (`pip install pyyaml`) for the full suite                                                                                                                                        |
| Lint (all)                 | `make lint`                                      | Trunk downloads its own tool versions on first run                                                                                                                                                               |
| Lint (correctness gate)    | `make lint-errors`                               | SC2155/SC2145 only; exits non-zero on violations. Fast regression gate.                                                                                                                                          |
| Format                     | `make lint-fix`                                  | Auto-fixes where supported                                                                                                                                                                                       |

### Non-obvious caveats

- **`make test` vs `make test-all`**: `make test` runs shell tests only (faster
  for iteration). `make test-all` additionally runs Python tests. Use
  `make test-quick` for pre-commit smoke checks.
- **Trunk first-run latency**: The first `trunk check` or `trunk fmt` invocation
  downloads shellcheck, shfmt, ruff, black, prettier, etc. into `.trunk/`.
  Subsequent runs are fast. The update script installs the Trunk launcher, but
  tool downloads happen lazily.
- **No `requirements.txt`**: Python tests and scripts are mostly standard
  library. The full test suite needs `pyyaml` (`pip install pyyaml`) — used by
  `tests/test_repository_automation_common.py` which exercises
  `.github/scripts/repository_automation_common.py`.
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

- Phase 2 PR salvage must never autonomously merge; open draft salvage or infra-fix PRs and leave merge decisions to a human.
- Security, auth, secrets, and trust-boundary PRs stay escalated for human review even when CI is green.

## Learned Workspace Facts

- Sibling Bolt/Jules PRs that both touch `.jules/bolt.md` often conflict on the journal only after one merges; salvage remaining source changes and resolve the journal by taking `main`'s `.jules/bolt.md` (Lesson 0cs).
- Multi-repo cloud PR sessions often leave dirty tracked `seatek_series_correction.egg-info/` files under `series_correction_project_updated` after editable installs; restore or discard those changes and do not commit them.
