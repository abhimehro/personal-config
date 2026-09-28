# Jules PR Review Rules, personal-config

This repository is macOS workstation infrastructure-as-code: dotfiles, shell/Python automation, launchd agents, Control D/Windscribe networking, maintenance jobs, and media pipeline operations. Review as a senior engineer responsible for correctness, security, maintainability, and safe system-state changes.

## Severity mapping

Map the repo's existing `REVIEW.md` model onto Jules findings:

* **High** = Blocking: data loss or corruption, security exposure, secret leakage, unsafe system mutation, broken critical workflow, wrong network/DNS/VPN state, silent contract break, or a change that could leave the workstation in an unrecoverable or unsafe state.
* **Warning** = Discuss: working code that introduces meaningful debt, weak evidence for risky behavior, unbounded resource use, architectural drift, fragile shell behavior, or missing tests around critical paths.
* **Info** = Optional: clarity, naming, decomposition, documentation, or style comments with no behavioral risk. Keep these rare.

Every finding must name a concrete failure mechanism and impact. Do not report category-only concerns.

## Review scope

Review changed lines and the behavior they demonstrably affect. Raise pre-existing issues only when the PR makes them reachable, worse, or newly relevant. Prefer consistency with existing repo patterns over stylistic preference.

## Repo-specific priorities

Prioritize:

1. Security and secret hygiene.
2. Correctness of scripts that modify system state.
3. Safe handling of file paths, symlinks, launchd agents, DNS/VPN state, and credentials.
4. Least-privilege GitHub Actions permissions.
5. Tests or verification commands appropriate to the risk of the change.
6. macOS/Linux portability where relevant, while remembering this is primarily a macOS-focused repo.

## Hard review rules

Flag as **High** when a change:

* Logs, commits, echoes, or weakens handling of credentials, tokens, API keys, SSH material, or local secret files.
* Runs destructive commands without guardrails, clear scope, or confirmation where appropriate.
* Broadens GitHub Actions permissions without a concrete need.
* Uses `pull_request_target` for untrusted PR code.
* Interpolates untrusted `github.event.*` data directly into shell commands instead of binding through `env:`.
* Suggests or introduces unsafe Control D/Windscribe behavior, including static free-DNS fallbacks where real profile IDs are required, `--listen` with `--cd`, or treating known CD Mode numeric `exclude` failures as a simple local config mistake.
* Breaks idempotent dotfile syncing, launchd installation, network mode switching, maintenance jobs, or media pipeline operations.

Flag as **Warning** when a change:

* Adds or modifies shell scripts without adequate quoting, exit behavior, cleanup, or path validation.
* Changes system-state scripts without verification guidance.
* Adds critical behavior without tests or a documented manual verification path.
* Makes CI/workflows noisier, more privileged, or less deterministic without a clear reason.
* Ignores known macOS-vs-Linux differences such as BSD/GNU `sed`, launchctl availability, macOS-only tests, or expected CI skips.

## Testing and verification expectations

Prefer the existing commands documented in `AGENTS.md`:

* `make test-quick` for fast smoke checks.
* `make test` for shell tests.
* `make test-all` for shell + Python tests.
* `make lint-errors` for correctness-focused ShellCheck gates.
* `make lint` or `trunk check --all` for full linting when appropriate.
* `make verify-credentials` for optional auth/secret hygiene checks.
* Network-specific changes should reference relevant verification scripts such as `scripts/network-mode-verify.sh`, `scripts/network-mode-regression.sh`, or `make control-d-regression`.

Do not treat macOS-only test skips on Linux as failures when the repo documents them as expected skips.

## Bot and automation policy

This workflow reviews only. It must not approve, merge, close PRs, create follow-up issues, or alter the repo.

Codacy, qodo, and CodeRabbit review threads with no human reply are advisory according to existing repo policy. Human replies, security holds, required checks, merge conflicts, and sticky human review markers remain blocking.

## Output expectations

Keep feedback concise and high-signal. Consolidate repeated instances into one root-cause comment. Name what is good when it is specifically useful. Prefer minimal fixes and concrete verification guidance over broad rewrites.
