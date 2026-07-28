# ELIR Handoff — ABHI-1517: Pin GitHub Actions & Least-Privilege Permissions

## Purpose

Eliminate supply-chain and over-permission risk from GitHub Actions in `abhimehro/personal-config` by:

1. Pinning every remote `uses:` reference to an independently verified 40-character commit SHA.
2. Applying job-level least-privilege `permissions` and a top-level default of `permissions: {}` where appropriate.
3. Auditing `persist-credentials`, `pull_request_target`, PAT/App-token exposure, implicit `github.token`, and attacker-controlled interpolation.
4. Adding a fail-closed CI gate that rejects any non-SHA remote action reference or placeholder.

## What changed

- `.github/scripts/validate_workflow_pins.py` — new fail-closed gate. Parses every workflow and composite action, allows local (`./...`) / Docker (`docker://...`) refs, and requires every other `uses:` to be a full 40-character SHA. Rejects literal placeholders such as `<FULL_40_CHAR...>`.
- `.github/workflows/security-scan.yml` — new `workflow-integrity` job that runs the Python gate plus `trunk check --filter=pinact --no-fix` and `trunk check --filter=actionlint --no-fix`. Added to the `summary` report.
- All active workflows with floating action refs were pinned:
  - `actions/github-script@v9.0.0` → `3a2844b7e9c422d3c10d287c895573f7108da1b3` (# v9.0.0)
  - `github/codeql-action/*@v4.37.3` → `e4fba868fa4b1b91e1fdab776edc8cfbe6e9fb81` (# v4.37.3)
  - `gitleaks/gitleaks-action@v3.0.0` → `e0c47f4f8be36e29cdc102c57e68cb5cbf0e8d1e` (# v3.0.0)
  - `anchore/sbom-action@v0.24.0` → `e22c389904149dbc22b58101806040fa8d37a610` (# v0.24.0)
  - `actions/upload-artifact@v7.0.1` → `043fb46d1a93c77aae656e7c1c64a875d1fc6a0a` (# v7.0.1)
  - `actions/download-artifact@v8.0.1` → `3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c` (# v8.0.1)
  - `pnpm/action-setup@v6.0.9` → `0ebf47130e4866e96fce0953f49152a61190b271` (# v6.0.9)
  - `release-drafter/release-drafter@v7.6.0` → `eada3c96a64734dd381cfbda23511034e328ddb0` (# v7.6.0)
  - `actions/stale@v10.4.0` → `1e223db275d687790206a7acac4d1a11bd6fe629` (# v10.4.0)
  - `actions/dependency-review-action@v5.0.0` → `a1d282b36b6f3519aa1f3fc636f609c47dddb294` (# v5.0.0)
  - `github/gh-aw/actions/setup-cli@<FULL_40_CHAR_COMMIT_SHA_FOR_V0.66.1>` → `d688a4a5fa8aa96ad18fa13f0b187c38548a275c` (# v0.66.1)
  - `codescene-oss/pr-refactoring-agent@...` annotation corrected to `# v1.0.8`; SHA preserved.
- `permissions` tightened:
  - `security-scan.yml` `sbom-generation` no longer requests `packages: write`.
  - `pr-visual-recap.yml` `gate` and `recap` jobs dropped `issues: write`; `recap` also dropped `actions: write`.
  - `copilot-setup-steps.yml` dropped `issues: write`.
  - `refactoring-agent.yml` dropped `issues: write`.
  - `repository-automation-daily.yml` / `repository-automation-weekly.yml` moved from broad top-level write permissions to `permissions: {}`.
  - `release-drafter.yml` and `dependency-review.yml` moved top-level `permissions` to job-level.
- `persist-credentials: false` added to every checkout that does not push code; `workflow_updater` in `repository-automation-daily.yml` keeps `persist-credentials: true` because it creates draft PR branches via `git push`.
- `summary.yml` `Comment with AI summary` step now writes the LLM response to a temp file and passes `--body-file` to `gh`, removing the remaining shell interpolation path.
- `agentics-maintenance.yml` `operation` input changed from `type: choice` with an empty-string option to `type: string` to satisfy `actionlint`/`yamllint` (the empty option was not valid).
- `copilot-setup-steps.yml` removed invalid top-level `description:` key flagged by `actionlint`.

## Security

- Every remote action is now an immutable commit SHA, eliminating tag-rollback / compromised-release attacks.
- `GITHUB_TOKEN` permissions are at the lowest job-level scope needed; top-level defaults are `permissions: {}` or explicit read-only defaults.
- Checkout tokens are not persisted unless a job must `git push`, reducing lateral movement if a later step is compromised.
- `pull_request_target` workflows (`label.yml`, `release-drafter.yml`) were left unchanged because they intentionally run in the base repository context.
- PAT/App-token exposure audited: `GH_TOKEN`, `PLAN_RECAP_TOKEN`, and API keys are bound to `env:` and not echoed; `refactoring-agent` auth JSON remains a step output used as an action input (existing pattern, outside this remediation).

## Failure modes

- `agentics-maintenance.yml` is a generated file. `gh aw` is not installed in this environment, so the source `pkg/workflow/maintenance_workflow.go` could not be regenerated. The file was hand-patched; future `gh aw compile` may need reconciliation.
- `repository-automation-daily/weekly` now run with `permissions: {}` and rely on the `GH_TOKEN` PAT for all writes. If `GH_TOKEN` is missing, the workflows will fail informatively.
- `workflow-integrity` CI gate will fail any PR that introduces a floating tag, placeholder, or non-SHA remote action reference.
- Full `trunk check --all` still reports many pre-existing lint/format/security issues across the repo; the targeted `pinact`/`actionlint` gates and repository tests pass.

## Verify

- `python .github/scripts/validate_workflow_pins.py` — clean.
- `python -c 'import yaml; ...'` parsed all 17 workflows — clean.
- `trunk check --filter=pinact --no-fix .github/workflows .github/actions` — clean.
- `trunk check --filter=actionlint --no-fix .github/workflows .github/actions` — clean.
- `make lint-errors` — clean.
- `make test-quick` — 17 shell tests + 4 Python tests passed.
- `make test` — 43/46 tests passed, 3 skipped.
- `make test-python` — 429 tests passed.

## Post-merge

1. Run the workflows on `main` or a representative PR to confirm `workflow-integrity` and the modified jobs pass.
2. Only after representative runs succeed, set the repository default `GITHUB_TOKEN` to **restricted/read-only**:
   `Settings → Actions → General → Workflow permissions → Read repository contents and packages permissions`.
3. Do **not** enable PR creation/approval for Actions unless explicitly required.
# ELIR Handoff — ABHI-1549 Placeholder Secrets

## 📋 Purpose

Standardize committed placeholder markers so scanners and humans cannot confuse
templates with live credentials. MCP templates keep `op://` 1Password CLI refs;
`.env.example`-style files use `REPLACE_WITH_*` markers; docs no longer say
`your_actual_…`.

## 🛡️ Security

- **Threats addressed:** Ambiguous placeholders mistaken for real keys; legacy
  `YOUR_*_API_KEY` MCP template diverging from the canonical `op://` source of
  truth; docs implying filled credentials belong in-repo.
- **Assumptions:** No live keys were present in the flagged files (confirmed by
  audit). Windsurf `op://` values are intentional secure refs.
- **Trust boundary:** Committed templates vs generated/local configs outside
  git.

## ⚠️ Failure Modes

| Break                                      | Consequence                         | Mitigation                                      |
| ------------------------------------------ | ----------------------------------- | ----------------------------------------------- |
| Someone pastes a live key into a template  | Key lands in git                    | Generator + hygiene test; regenerate with `op`  |
| Legacy template drifts from canonical JSON | Conflicting docs / scanner noise    | Legacy file now mirrors `.template.json`        |
| Scanner still flags `op://`                | False positive                      | Documented as secure-storage refs in MCP docs   |

## ✅ Review Checklist

- [ ] Confirm `mcp-configs/mcp-servers.template` == `mcp-servers.template.json`
- [ ] Confirm Windsurf templates still use only `op://` (not live keys)
- [ ] Skim `docs/MCP_SECRETS_MANAGEMENT.md` placeholder convention table
- [ ] `bash tests/test_repo_credential_hygiene.sh` passes

## 🔧 Maintenance

- Edit **only** `mcp-configs/mcp-servers.template.json`, then copy/sync the
  legacy `.template` mirror (or regenerate via the same content).
- New env examples must use `REPLACE_WITH_*`, never `your_actual_*`.
- Keep `scripts/generate-mcp-configs.sh` as the path that resolves secrets
  outside the repo.
