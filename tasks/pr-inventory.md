# Automated PR inventory — 2026-04-01 (backlog cleanup, review-and-merge)

**Config:** `tasks/pr-review-agent.config.yaml`
**Stale threshold:** 30 days (no in-scope open PR exceeded this at inventory time)
**Mode:** `review-and-merge` · **Merge strategy:** squash · **Auto-fix:** enabled (none applied this session — merges were API-only)

**Repo note:** Use `abhimehro/personal-config` in config and URLs; some environments redact the slug as `personal-config` in CLI or logs. Same repository.

## Scope rules

1. **Configured bot logins:** `dependabot[bot]`, `renovate[bot]`, `google-labs-jules[bot]` (GitHub may surface Dependabot as `app/dependabot`).
2. **Expanded automation:** include PRs where GitHub shows `abhimehro` as author when **branch**, **title**, **labels**, or **comments** indicate Jules / Sentinel / Bolt / Palette / daily QA / `automation-workflow-*`, etc.

## Historical inventory — 2026-03-27 (archived snapshot)

| Repo | PR # | Visible author | Automation signals | Category | CI (rollup) | Conflicts | changedFiles | Notes |
| ---- | ---: | -------------- | ------------------ | -------- | ----------- | --------- | -----------: | ----- |
| personal-config | 682 | abhimehro | Jules branch + footer | SECURITY | Green | CLEAN → merged | 3 | Trunk symlink fixed before merge |
| personal-config | 681 | abhimehro | `chore/jules-daily-*` | CI/INFRA | Green | CONFLICTING | 2 | Escalated — resolve conflicts |
| personal-config | 678 | abhimehro | `automation-workflow-*` draft | CI/INFRA | Green | CLEAN | 1 | Escalated — draft workflow trust boundary |
| personal-config | 677 | abhimehro | Sentinel branch | SECURITY | Green | CONFLICTING | 2 | **Closed** superseded by #682 |
| ctrld-sync | 672 | abhimehro | Sentinel branch | SECURITY | Green | CLEAN → merged | 2 | Preferred over #668 |
| ctrld-sync | 669 | abhimehro | `automation-workflow-*` draft | CI/INFRA | Green | CLEAN | 2 | Escalated |
| ctrld-sync | 668 | abhimehro | Sentinel branch | SECURITY | Green | CONFLICTING | 3 | **Closed** superseded by #672 |
| email-security-pipeline | 597 | abhimehro | Sentinel | SECURITY | Green | CLEAN → merged | 3 | Malware/attachment parsing |
| email-security-pipeline | 596 | abhimehro | Palette branch | UI | Green | CLEAN → merged | 2 | Screen reader / CLI |
| email-security-pipeline | 594 | abhimehro | `automation-workflow-*` draft | CI/INFRA | Green | CLEAN | 14 | Escalated |
| email-security-pipeline | 593 | abhimehro | `daily-qa-review-*` | CI/INFRA | Green | CLEAN | 0 | **Closed** no-op diff |
| email-security-pipeline | 592 | abhimehro | Bolt branch | PERFORMANCE | Green | CLEAN → merged | 2 | Magic-byte fast path |
| email-security-pipeline | 587 | abhimehro | fix pre-commit | CI/INFRA | Green | CLEAN → merged | 1 | Valid pre-commit rev |
| email-security-pipeline | 585 | abhimehro | Sentinel | SECURITY | Green | CONFLICTING | 2 | **Closed** superseded post-#597 |
| Seatek_Analysis | 107 | abhimehro | Bolt | PERFORMANCE | Green | CLEAN → merged | 1 | Vectorized pandas |
| Seatek_Analysis | 106 | abhimehro | Sentinel | SECURITY | Green | CLEAN → merged | 1 | Generic error leakage |
| Hydrograph_Versus_Seatek_Sensors_Project | 94 | abhimehro | Sentinel | SECURITY | Green | CLEAN → merged | 3 | Shared sanitize_filename |
| Hydrograph_Versus_Seatek_Sensors_Project | 93 | abhimehro | Bolt | PERFORMANCE | Green | CLEAN → merged | 4 | `len(df)` vs `.empty` |

**Totals at snapshot:** 18 in-scope open PRs across 5 repos (Seatek + Hydro had none beyond the listed).

## Inventory at session start — 2026-04-01 (open, in-scope)

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

## Inventory after session — 2026-04-01 (remaining open)

| Repo | PR # | State | Reason still open |
| ---- | ---: | ----- | ----------------- |
| personal-config | 697 | DRAFT | Escalated — workflow consolidation / trust boundary |
| ctrld-sync | 687 | DRAFT | Escalated — failing CI + workflow consolidation |
| email-security-pipeline | 612 | DRAFT | Escalated — workflow consolidation |
| email-security-pipeline | 614 | OPEN | Merge conflicts with `main`; human rebase + CodeScene hotspot review |
