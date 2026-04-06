---
name: "cloud-agents-starter"
description: "Runbook for Cloud agents: setup, commands, and tests by codebase area (macOS IaC dotfiles repo)"
---

# Cloud agents — codebase runbook

macOS-first **infrastructure-as-code** repo: shell scripts, dotfiles, `launchd` agents, networking helpers. **No long-running app server.** On Linux/CI, treat this as **edit → lint → test**; skip macOS-only bootstrap and live network switching unless the task requires it.

**First 60 seconds (any agent)**

```bash
cd /path/to/repo
git status
make test-quick          # smoke: lib tests + path_validation
```

**Authoritative docs:** `AGENTS.md` (full command index), `docs/TESTING.md` (mock/`PATH` patterns).

---

## 1) Repo-wide — Cloud workspace & quality gates

### Environment setup

- **Deps:** `bash`, `python3` (stdlib only for Python tests). **Lint:** [Trunk](https://trunk.io) (`trunk check`) — first run downloads tools into `.trunk/`.
- **No `.env` required** for tests. Do not commit secrets; Cloud pre-commit may scan staged diffs if `CLOUD_AGENT_INJECTED_SECRET_NAMES` is set (canonical hook logic: `scripts/cursor_cloud_agent_pre_commit.sh`).
- **Feature flags / toggles:** No central flag file. Examples:
  - `USE_MCP_GITHUB=true` — optional GitHub automation path (`docs/github-mcp-integration.md`).
  - Tests/scripts: case-by-case env (e.g. `FORCE_RUN=1` in some maintenance tests — see the test file).

### Testing workflow

```bash
make test-quick          # fastest sanity check
make test                # all shell tests (parallel); exit 77 = skip on Linux where expected
make test-python         # Python unittest discovery under tests/
make test-all            # shell then Python
make lint-errors         # SC2155/SC2145 only; no Trunk
make lint                # full Trunk (match CI style)
trunk check path/to/file.sh   # match CI ShellCheck config vs raw local shellcheck
```

---

## 2) Dotfiles & symlink orchestration (`scripts/`, `configs/`)

### Environment setup

- **macOS:** `./setup.sh` or `./scripts/install_all_configs.sh` (interactive) — **do not run on Linux.**
- **Config “live”:** `./scripts/sync_all_configs.sh` writes symlinks under `$HOME` — **mutates user home**; only run when explicitly testing that flow.

### Testing workflow

```bash
./scripts/verify_all_configs.sh    # symlinks, targets, key perms
./scripts/verify_ssh_config.sh     # SSH-focused (needs macOS / 1Password agent — may skip/fail elsewhere)
bash tests/test_config_fish.sh     # skips if `fish` missing
```

---

## 3) Network — Control D / Windscribe (`scripts/network-mode-*.sh`, `controld-system/`)

### Environment setup

- **Real switching:** macOS only; requires installed tools and privileges implied by those scripts. **Read before running** — changes DNS/VPN-related state.
- **No mock “feature flag”** for production scripts; CI relies on tests with faked `PATH` (see `docs/TESTING.md`).

### Testing workflow

```bash
bash tests/test_network_mode_manager.sh
bash tests/test_network_mode_verify.sh
# Optional full regression (macOS / environment-dependent):
make control-d-regression
# Or directly:
./scripts/network-mode-regression.sh browsing
```

---

## 4) Maintenance (`maintenance/`)

### Environment setup

- **Manual run (macOS):** `./maintenance/bin/run_all_maintenance.sh health` or `quick` — may touch schedules/logs under `~/Library/Logs/maintenance/` per `maintenance/README.md`.
- **Scheduled agents:** `launchctl list | grep maintenance` (macOS only).

### Testing workflow

```bash
bash tests/test_health_check.sh
bash tests/test_system_cleanup.sh
bash tests/test_google_drive_backup.sh
# Many tests use MOCK_BIN + isolated HOME — see docs/TESTING.md
```

---

## 5) Media streaming (`media-streaming/`)

### Environment setup

- **Templates / agents:** Staged by `./setup.sh` (macOS). Operational scripts under `media-streaming/scripts/`.
- **Credentials:** Never hardcode; tests use temp `HOME` and mocks.

### Testing workflow

```bash
bash tests/test_media_server_auth.sh
python3 -m unittest tests.test_infuse_media_server -v
# Doc: media-streaming/README.md
```

---

## 6) Shared shell libraries (`scripts/lib/`)

### Environment setup

- Source-only modules; no separate service.

### Testing workflow

```bash
bash tests/test_lib_common.sh
bash tests/test_lib_dns_utils.sh
bash tests/test_dns_utils.sh
```

---

## 7) Python utilities (`tests/test_*.py` and referenced modules)

### Environment setup

- **Stdlib only** — no `pip install`.

### Testing workflow

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
# Single module:
python3 -m unittest tests.test_path_validation -v
```

---

## 8) GitHub / PR automation (`docs/`, `scripts/preflight-gh-pr-automation.sh`, `.github/`)

### Environment setup

- **`gh` CLI** and repo access as needed for live commands.
- Optional: `USE_MCP_GITHUB=true` for MCP-backed automation (see `docs/github-mcp-integration.md`).

### Testing workflow

```bash
bash tests/test_preflight_gh_pr_automation.sh
./scripts/preflight-gh-pr-automation.sh --config tasks/pr-review-agent.config.yaml   # read-only preflight when configured
```

---

## Maintenance protocol (keep this skill current)

1. **After adding a new test entrypoint** — document the `make` target or `bash tests/...` line here under the right area.
2. **After changing CI/lint** — update the “Repo-wide” section (e.g. new `make` targets, Trunk vs `shellcheck` notes).
3. **After new env toggles** — add one line with variable name + pointer to doc or script.
4. **Prefer commands over prose** — if you wrote steps in `AGENTS.md` or `docs/TESTING.md`, mirror the minimal runnable form here and link the long form once.
5. **Review quarterly** or when agents repeatedly mis-run (wrong OS assumptions, missing smoke command) — tighten the **First 60 seconds** block first.
