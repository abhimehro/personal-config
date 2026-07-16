# GitHub Actions Workflows

Canonical catalog for `.github/workflows/` (ABHI-1321 / #1469). **17 active
YAML workflows** after consolidation (2026-07-16). Prefer this table over
hunting through the directory.

> **Consolidation history:** Scheduled agentic jobs live in
> `repository-automation-daily.yml` and `repository-automation-weekly.yml`.
> Removed as redundant/obsolete: standalone `shellcheck.yml` (covered by
> `mac-audit.yml`), stub `test-refactoring-agent.yml`, and the disabled Gemini
> CLI suite (`gemini-*.yml`). Companion prompts remain under
> `.github/commands/gemini-*.toml` if Gemini workflows are reintroduced.

## Catalog

### CI / quality gates

| Workflow | Trigger | Purpose |
| --- | --- | --- |
| `code-quality.yml` | PR/push (shell/Python paths), dispatch | ShellCheck + radon/Trunk quality checks; unit tests |
| `security-scan.yml` | PR/push (ignore docs), weekly, dispatch | TruffleHog, Gitleaks, ShellCheck (error), pip-audit, CodeQL, SBOM |
| `dependency-review.yml` | PR → main | GitHub Dependency Review Action on manifest changes |
| `case-collision.yml` | PR/push main, dispatch | Detect case-only filename collisions (macOS vs Linux) |
| `mac-audit.yml` | Paths `mac-audit/**`, weekly Mon, dispatch | ShellCheck job + macOS-14/15 audit modules |

### PR / issue hygiene

| Workflow | Trigger | Purpose |
| --- | --- | --- |
| `label.yml` | `pull_request_target` | Auto-label PRs from changed paths |
| `summary.yml` | Issue opened | Summarize new issues |
| `release-drafter.yml` | Push main + `pull_request_target` | Maintain draft release notes |
| `pr-visual-recap.yml` | PR lifecycle events | Visual/recap comment on PRs |
| `stale.yml` | `workflow_dispatch` only | Mark stale issues/PRs (manual; schedule removed) |
| `main.yml` | `workflow_dispatch` | Clean stale remote branches (manual) |

### Agent / automation

| Workflow | Trigger | Purpose |
| --- | --- | --- |
| `repository-automation-daily.yml` | Daily cron + dispatch | Workflow updater, perf, QA, backlog, status report |
| `repository-automation-weekly.yml` | Weekly cron + dispatch | Weekly retrospective (writes gated by input) |
| `agentics-maintenance.yml` | `workflow_dispatch` | gh-aw maintenance (disable/enable/update/upgrade) |
| `jules-daily-qa.yml` | Daily cron + dispatch | Multi-repo Jules QA prompts — **verify integration** (no runs since 2026-03-28) |
| `refactoring-agent.yml` | Issue comment `/cs-agent` | CodeScene PR refactoring agent |
| `copilot-setup-steps.yml` | PR/issues + dispatch | Development Partner setup comments (**CWE-94:** bind `request` via `env.REQUEST`) |

## Security notes

- Prefer **least privilege** `permissions:` on every workflow; do not broaden
  when editing.
- Never interpolate untrusted `github.event.*` strings into shell via `${{ }}`
  — bind through `env:` first (see `docs/AI_AGENT_SECURITY_REMEDIATION_GUIDE.md`).
- `security-scan.yml` and `dependency-review.yml` are the supply-chain/secrets
  gates; do not remove without an explicit replacement.
- Do not hand-edit generated gh-aw lockfiles if they reappear; edit sources and
  recompile with `gh aw compile`.

## Local verification

```bash
# List workflows
ls .github/workflows/*.yml | wc -l   # expect 17

# Actionlint if installed
actionlint .github/workflows/*.yml

# Repo smoke tests (unrelated to Actions runtime, but catches YAML consumers)
make test-quick
```

## Optional: re-enable Gemini CLI workflows

Gemini workflows were removed while disabled. To restore:

1. Recover `gemini-*.yml` from git history before this consolidation commit.
2. Configure `GEMINI_API_KEY` (or Vertex / WIF) per prior README guidance.
3. Re-enable the workflows in the Actions UI after validating auth.
