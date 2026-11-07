# Ported Jules Review and QA Rules

Adapted from `personal-config/.github/jules-review-rules.md` for Antigravity
proactive sweeps and local review sessions.

## Severity Mapping

- **High (Blocking):** Data loss or corruption, security exposure, secret
  leakage, unsafe system mutation, broken critical workflow, wrong
  network/DNS/VPN state, silent contract or scientific-output break, or leaving
  a workstation in an unrecoverable state.
- **Warning (Actionable):** Working code with fragile shell quoting/exit
  handling, unbounded resource/timeout behavior, missing error recovery on
  critical paths, or clear dead-code debt verified safe to remove.
- **Info (Skip in Unattended Sweeps):** Naming, cosmetic formatting, or
  stylistic preference with zero behavioral risk. Do not open proactive branches
  or PRs for `Info`-only items.

Every finding must name a concrete failure mechanism and impact rather than a
category label.

## Hard Review Rules

Flag as **High** and never introduce changes that:

1. Log, commit, echo, or weaken handling of credentials, tokens, API keys, SSH
   material, or local secret files.
2. Run destructive commands without guardrails, clear scope, and confirmation.
3. Broaden GitHub Actions permissions, use `pull_request_target` on untrusted PR
   code, or interpolate `${{ github.event.* }}` directly into `run:` shell
   blocks instead of binding via `env:`.
4. Introduce unsafe Control D or Windscribe behavior (static free-DNS fallbacks
   where real profile IDs are required, combining `--listen` with `--cd`, or
   misclassifying known CD Mode numeric `exclude` behavior).
5. Break idempotent dotfile syncing, `launchd` installation, network mode
   switching, maintenance jobs, media pipeline scripts, or reproducible
   scientific outputs.

## Shell and Cross-Platform Hygiene

- Quote variable expansions, use `set -Eeuo pipefail` where appropriate, clean
  up temp directories via `trap`, and isolate tests with `$TEST_DIR/home`.
- Account for macOS-vs-Linux differences (`sed -i ''` vs `sed -i`, `launchctl`
  availability, and documented exit-77 CI test skips).

## Verification Commands by Repository

- `personal-config`:
  `make lint-errors && bash tests/test_lib_common.sh && bash tests/test_lib_dns_utils.sh && python3 -m unittest tests.test_path_validation`
  (plus `trunk check <changed-files>` when Trunk is initialized).
- `ctrld-sync`:
  `uv run --all-extras pytest tests/ test_main.py -q && uv run --all-extras ruff check .`
- `email-security-pipeline`: `python3 -m pytest -q`
- `Hydrograph_Versus_Seatek_Sensors_Project`:
  `MPLBACKEND=Agg python3 -m pytest tests/ -q && flake8 src/ tests/`
- `Seatek_Analysis`:
  `Rscript -e "library(testthat); source('Updated_Seatek_Analysis.R', local = TRUE); testthat::test_dir('tests/testthat', reporter = 'summary')"`
- `repoprompt-ce`:
  `.agents/skills/rpce-contribution-check/scripts/preflight.sh commit`
