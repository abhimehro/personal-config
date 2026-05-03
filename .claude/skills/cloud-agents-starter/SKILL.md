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
make cursor-cloud-hooks  # Cursor Cloud only: sync secret-scan hooks from repo (printenv fix)
make test-quick          # smoke: lib tests + path_validation
```

**Authoritative docs:** `AGENTS.md` (full command index), `docs/TESTING.md` (mock/`PATH` patterns).

---

## Devin Secrets Needed

- **None required** for local lint/unit tests and mock-based CLI tests.
- **`GH_TOKEN` / `GH_TOKEN_2`** may be needed only for live GitHub/`gh` flows; prefer mocked `gh` on `PATH` for deterministic tests of triage logic.

---

## 1) Repo-wide — Cloud workspace & quality gates

### Environment setup

- **Deps:** `bash`, `python3` (stdlib only for Python tests). **Lint:** [Trunk](https://trunk.io) (`trunk check`) — first run downloads tools into `.trunk/`.
- **No `.env` required** for tests. Do not commit secrets; Cloud pre-commit may scan staged diffs if `CLOUD_AGENT_INJECTED_SECRET_NAMES` is set (canonical hook logic: `scripts/cursor_cloud_agent_pre_commit.sh`). **Run `make cursor-cloud-hooks`** after clone in Cursor Cloud so injected hooks match the repo (avoids `${!var}` breakage on secret labels with spaces). The sync only runs when both `pre-commit.cursor` and `commit-msg.cursor` exist as regular files under each hash directory.
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
# Verification coverage uses the regression entrypoint below (macOS / environment-dependent):
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

### Duplicate triage (`detect_duplicates.py`)

When changing `detect_duplicates.py`, validate the rewrite behavior in an isolated temp workspace with `tasks/pr-triage.md` and a mocked `gh` executable first on `PATH`. Use full `abhimehro/<repo>#<number>` entries because the script only processes lines beginning with `- abhimehro/`.

Use adversarial PR numbers where one is a prefix of another, e.g. SUPERSEDED has `abhimehro/example#123` and READY has `abhimehro/example#12`, `abhimehro/example#123`, and `abhimehro/example#124`. These assertions are pass criteria only after the duplicate-triage fixes from PR #869 (or an equivalent implementation) are present; on older branches, treat failures as confirmation that the script must be fixed before relying on the runbook.

PR #869 adds a dedicated `tests/test_detect_duplicates_triage.py` regression for this scenario. If that file is not present on your branch, port/create the regression first or run the same mocked temp-workspace scenario manually; do not run a module-specific unittest command for a file that does not exist.

Key assertions:

- The script exits `0` and prints `Duplicates: []` when mocked file sets are unique.
- `## SUPERSEDED` preserves `- abhimehro/example#123` exactly once.
- `## READY` keeps the prefix PR `- abhimehro/example#12` when `abhimehro/example#123` appears before READY.
- `## READY` removes the already-SUPERSEDED `- abhimehro/example#123`.
- `## DUPLICATE` stays empty when mocked file paths differ.

```bash
# After the duplicate-triage regression exists on this branch:
python3 -m unittest discover -s tests -p 'test_*.py' -v
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
