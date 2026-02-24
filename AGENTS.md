# AGENTS.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Repository intent (what this repo is)
`personal-config` is an “infrastructure as code” repo for a macOS workstation: dotfiles + automation scripts + launchd agents that manage networking (Control D/Windscribe), SSH setup, maintenance jobs, and a media pipeline.

Many scripts intentionally modify system state (symlinks in `$HOME`, `launchctl` agents, DNS/IPv6 settings, services). Prefer reading scripts first and using the repo’s verify/test scripts after changes.

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

```bash
# Show current status
./scripts/network-mode-manager.sh status

# Switch to Control D DNS mode (profiles: browsing|privacy|gaming)
./scripts/network-mode-manager.sh controld browsing

# Switch to Windscribe-only mode (Control D stopped, DNS resets)
./scripts/network-mode-manager.sh windscribe

# Switch to “combined mode” (Windscribe + Control D profile)
./scripts/network-mode-manager.sh windscribe privacy
```

Verification/regression:
```bash
# Verify current state (profile-aware for controld)
./scripts/network-mode-verify.sh controld browsing
./scripts/network-mode-verify.sh windscribe

# Full regression: Control D → Windscribe → Combined
./scripts/network-mode-regression.sh browsing

# Makefile shortcut (runs regression)
make control-d-regression
```

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
High-level docs live in `media-streaming/README.md`. Setup is staged by `setup.sh` (templates + LaunchAgents).

```bash
# Verify media automation agents (names vary; grep is the easiest entrypoint)
launchctl list | grep -E '(media|alldebrid|speedybee)'
```

### Lint / formatting (Trunk)
This repo is wired for Trunk via `.trunk/trunk.yaml` (shellcheck, shfmt, ruff, black, prettier, trufflehog, etc.).

```bash
# Run all configured linters
trunk check --all

# Auto-format (where supported)
trunk fmt
```

### Tests
There isn’t a single “test runner” script; most tests are directly executable shell scripts under `tests/`.

Run a single shell test:
```bash
bash tests/test_ssh_config.sh
bash tests/test_network_mode_manager.sh
```

Run all shell tests:
```bash
for f in tests/test_*.sh; do bash "$f"; done
```

Python tests use `unittest` (see `tests/test_*.py`).

Run a single Python test module:
```bash
python3 -m unittest tests.test_path_validation
```

Run all Python tests:
```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

### Benchmarks
```bash
# Requires hyperfine
make benchmark

# Or run the benchmark runner directly
./tests/benchmarks/benchmark_scripts.sh all
```

## Big-picture architecture (how the pieces fit)
### 1) Config-as-code via symlink orchestration
Core pattern: keep authoritative config files in-repo and symlink them into the real locations.

Key entrypoints:
- `scripts/sync_all_configs.sh`: creates/updates symlinks and backups when appropriate.
- `scripts/verify_all_configs.sh`: verifies links/targets and checks a few invariants (e.g., SSH perms, fish functions presence).

This is the backbone that makes “git pull” translate into a live system update.

### 2) Network mode manager (DNS + VPN state machine)
The networking subsystem is intentionally centralized so that “mode switching” is not a series of manual steps.

Key components:
- `scripts/network-mode-manager.sh`: orchestrates the state transition.
- `scripts/network-mode-verify.sh`: asserts the machine is in the expected state (Control D active vs Windscribe ready), including DNS resolver checks and some profile/DoH3 assertions.
- `scripts/network-mode-regression.sh` + `Makefile`: repeatable end-to-end regression to catch drift.
- `controld-system/scripts/controld-manager`: low-level Control D profile management; `network-mode-manager.sh` delegates to this.
- `scripts/macos/ipv6-manager.sh`: toggled as part of mode switching.

If you’re debugging a network issue, start from the manager → verify script outputs before changing anything.

### 3) Automated maintenance (launchd + modular scripts)
Maintenance is structured as:
- `maintenance/bin/*`: task scripts and orchestrators.
- `maintenance/install.sh` (invoked by `setup.sh`): installs/boots LaunchAgents.
- Logs are written under `~/Library/Logs/maintenance/` (see `maintenance/README.md`).

The important architectural idea: tasks are meant to be launchd-driven and observable via logs and `launchctl`.

### 4) Media streaming pipeline (agents + scripts)
The media pipeline is split into:
- Setup + configuration templates (e.g., rclone template seeded by `setup.sh`).
- Automation via LaunchAgents (installed if present).
- Operational scripts in `media-streaming/scripts/` (sync, rename/finalize, repair).

The docs in `media-streaming/README.md` describe the intended “zero-click” flow and the responsibilities of each agent/script.

### 5) Code quality + automation workflows
- Trunk is the “local lint hub” (`.trunk/trunk.yaml`).
- CI additionally runs complexity checks (ShellCheck + radon) and a Trunk check (see `.github/workflows/code-quality.yml`).
- `.github/workflows/README.md` documents additional agentic workflows and notes that `.md` workflow sources compile to `.lock.yml` (compiled files should not be edited by hand).

## Repo-specific agent behavior (important excerpts from existing rules)
If you are operating as an agent in this repo, align with:
- `.cursorrules`: security-first collaboration style (state approach before coding, comment *why*, provide a handoff summary after changes) + hard boundaries (don’t implement auth/payment/db schema changes without explicit user approval; don’t run destructive commands without confirmation).
- `.github/copilot-instructions.md`: “development partner” protocol (before/while/after coding rhythm).

## Existing guidance files (suggested improvements)
- `docs/archive/AGENTS.md` and `docs/archive/WARP.md` contain older guidance. Consider either:
  - deleting them to avoid drift, or
  - replacing them with a short pointer to this root `AGENTS.md`.

## Cursor Cloud specific instructions

This is a macOS-focused dotfiles/IaC repo. There are no web services or databases to start. The dev workflow is: edit scripts, lint, and run tests.

### Key services and how to run them

| What | Command | Notes |
|---|---|---|
| Python tests | `python3 -m unittest discover -s tests -p 'test_*.py'` | stdlib only, no pip deps |
| Shell tests | `for f in tests/test_*.sh; do bash "$f"; done` | Some tests are expected to fail on Linux; see caveats below. |
| Lint (all) | `trunk check --all` | Trunk downloads its own tool versions on first run |
| Format | `trunk fmt` | Auto-fixes where supported |

### Non-obvious caveats

- **Trunk first-run latency**: The first `trunk check` or `trunk fmt` invocation downloads shellcheck, shfmt, ruff, black, prettier, etc. into `.trunk/`. Subsequent runs are fast. The update script installs the Trunk launcher, but tool downloads happen lazily.
- **No `requirements.txt`**: Python tests and scripts use only the standard library. No `pip install` is needed for the test suite.
- **`package.json` is empty**: The root `package.json` is `{}` — it exists as a Trunk runtime anchor for Node-based linters (prettier, markdownlint). Do not run `npm install`.
- **macOS-specific test failures on Linux**: `test_config_fish.sh` (needs fish), `test_ssh_config.sh` (needs 1Password agent socket), `test_security_manager_restore.sh` (BSD sed syntax), and `test_media_server_auth.sh` (credential flow assertion) fail on Linux. These are not bugs.
- **`setup.sh` is macOS-only**: Do not run `./setup.sh` on Linux — it calls `launchctl`, Homebrew, and macOS system utilities.
