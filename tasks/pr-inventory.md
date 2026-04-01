# Automated PR inventory — 2026-04-01 (backlog cleanup, review-and-merge)

**Config:** `tasks/pr-review-agent.config.yaml`  
**Stale threshold:** 30 days (no in-scope open PR exceeded this at inventory time)  
**Mode:** `review-and-merge` · **Merge strategy:** squash · **Auto-fix:** enabled (none applied this session — merges were API-only)

**Repo note:** `abhimehro/personal-config` is the canonical GitHub name; some tooling redacts it in CLI output as `[REDACTED]-config`. They are the same repository.

## Scope rules

1. **Configured bot logins:** `dependabot[bot]`, `renovate[bot]`, `google-labs-jules[bot]` (GitHub may surface Dependabot as `app/dependabot`).
2. **Expanded automation:** include PRs where GitHub shows `abhimehro` as author when **branch**, **title**, **labels**, or **comments** indicate Jules / Sentinel / Bolt / Palette / daily QA / `automation-workflow-*`, etc.

## Inventory at session start (open, in-scope)

| Repo | PR # | Visible author | Automation signals | Category | CI (summary) | Merge state | changedFiles | Notes |
| ---- | ---: | -------------- | ------------------ | -------- | ------------ | ----------- | -----------: | ----- |
| personal-config | 703 | abhimehro | Jules Daily QA title + branch | CI/INFRA / docs | All required green | CLEAN | 16 | TOML + formatting |
| personal-config | 701 | abhimehro | Sentinel title | SECURITY | Green | CLEAN | 4 | `secrets.choices` crash |
| personal-config | 699 | abhimehro | Bolt title + branch | PERFORMANCE | Green (CodeScene advisory on method complexity) | CLEAN | 4 | AdGuard list I/O |
| personal-config | 697 | abhimehro | `automation-workflow-*` draft | CI/INFRA | UNSTABLE (draft) | MERGEABLE | 1 | **Escalate** — workflow trust boundary |
| ctrld-sync | 687 | abhimehro | draft workflow consolidation | CI/INFRA | **Failing** ruff/mypy/test | MERGEABLE | 7 | **Escalate** |
| email-security-pipeline | 618 | abhimehro | `jules/daily-qa-*` | CI/INFRA | Green | CLEAN | 0 | **Close** — no-op diff |
| email-security-pipeline | 617 | abhimehro | Bolt + branch | PERFORMANCE | Green | CLEAN | 2 | Laplacian `meanStdDev` |
| email-security-pipeline | 616 | abhimehro | Palette title | UI | **submit-pypi** failed (GitHub API transient) | UNSTABLE | 2 | Merged after classifying failure unrelated |
| email-security-pipeline | 614 | abhimehro | Bolt spam fast path | PERFORMANCE | Green required checks; CodeScene **commented** | CLEAN → **CONFLICT** after #617 | 2 | **Hold** — conflicts + hotspot |
| email-security-pipeline | 612 | abhimehro | draft workflow consolidation | CI/INFRA | Green | MERGEABLE | 14 | **Escalate** |
| email-security-pipeline | 611 | abhimehro | Bolt Laplacian (older) | PERFORMANCE | Green | CLEAN | 2 | **Close** — duplicate of #617 |
| Seatek_Analysis | 119 | abhimehro | Sentinel GH Actions injection | SECURITY | Green | CLEAN | 1 | Changelog workflow |
| Seatek_Analysis | 118 | abhimehro | Bolt DataFrame drop | PERFORMANCE | **validate** fail (F821 `BytesIO` on base) | UNSTABLE | 2 | **Close** — superseded by #114 after #114 merged |
| Seatek_Analysis | 117 | abhimehro | Sentinel CLI injection | SECURITY | Green | CLEAN | 2 | Automation scripts |
| Seatek_Analysis | 116 | app/dependabot | `dependabot/github_actions/actions/checkout-6` | DEPENDENCY | validate fail (pre-fix main) | UNSTABLE | 2 | Merged after #114 — failure unrelated to bump |
| Seatek_Analysis | 115 | app/dependabot | `setup-python` bump | DEPENDENCY | validate fail (pre-fix main) | UNSTABLE | 3 | Merged after #114 |
| Seatek_Analysis | 114 | abhimehro | Bolt + `BytesIO` import | PERFORMANCE + fix | Green | CLEAN | 1 | **Merge first** — fixes `main` ruff F821 |
| Hydrograph_Versus_Seatek_Sensors_Project | 98 | abhimehro | Bolt | PERFORMANCE | Green | CLEAN | 3 | Boolean masking |
| Hydrograph_Versus_Seatek_Sensors_Project | 97 | abhimehro | Sentinel path traversal | SECURITY | Green | CLEAN | 2 | Test data processor |

**Total in-scope at start:** 20 open PRs across 5 repos.

## Inventory after session (remaining open)

| Repo | PR # | State | Reason still open |
| ---- | ---: | ----- | ----------------- |
| personal-config | 697 | DRAFT | Escalated — workflow consolidation / trust boundary |
| ctrld-sync | 687 | DRAFT | Escalated — failing CI + workflow consolidation |
| email-security-pipeline | 612 | DRAFT | Escalated — workflow consolidation |
| email-security-pipeline | 614 | OPEN | Merge conflicts with `main`; human rebase + CodeScene hotspot review |
