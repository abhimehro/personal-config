# Automated PR inventory — 2026-04-11 (backlog cleanup, review-and-merge)

**Config:** `tasks/pr-review-agent.config.yaml`
**Stale threshold:** 30 days — **none** of the in-scope PRs at inventory time exceeded this (all recent).
**Mode:** `review-and-merge` · **Merge strategy:** squash · **Auto-fix:** enabled (no branch pushes required this session → **0** auto-fix commits)

## Scope rules

1. **Configured bot logins:** `dependabot[bot]`, `renovate[bot]`, `google-labs-jules[bot]` (GitHub may show `app/dependabot`).
2. **Expanded automation:** include PRs where GitHub shows `abhimehro` as author when **branch**, **title**, or **body** indicates Jules / Sentinel / Bolt / Palette / `automation-workflow-*`, etc.
   **Gap noted:** `dotfiles-iac` **#759** (`fix/github-actions-checkout-version-*`) matched via **body** (Jules footer), not branch/title regex — inventory scripts should also scan PR body for the Jules task host (subdomain `jules`, then dot, then the usual Google domain TLD) / `PR created automatically by Jules`. <!-- pragma: allowlist secret -->

## Repos

| Repo | Slug |
| ---- | ---- |
| Dotfiles / IaC | `abhimehro/dotfiles-iac` | <!-- pragma: allowlist secret -->
| Control D sync | `abhimehro/ctrld-sync` |
| Email pipeline | `abhimehro/email-security-pipeline` |
| Seatek | `abhimehro/Seatek_Analysis` |
| Hydrograph | `abhimehro/Hydrograph_Versus_Seatek_Sensors_Project` |

## Initial open inventory (2026-04-11, before actions)

| Repo | PR | Author | Branch (abbr.) | Category | CI (rollup) | Mergeable | Files | Notes |
| ---- | --: | ------ | -------------- | -------- | ----------- | --------- | ----: | ----- |
| Hydrograph | 112 | abhimehro | `bolt/avoid-sort-*` | PERFORMANCE | PASS | MERGEABLE | 1 | Superseded → **closed** after #116 |
| Hydrograph | 114 | abhimehro | `bolt/optimize-sort-*` | PERFORMANCE | PASS | MERGEABLE | 5 | Superseded → **closed** after #116 |
| Hydrograph | 116 | abhimehro | `bolt-optimize-redundant-*` | PERFORMANCE | PASS | MERGEABLE | 3 | **Merged** (canonical sort optimization) |
| Seatek | 129 | abhimehro | `bolt-optimize-lang-map-*` | PERFORMANCE | PASS | MERGEABLE | 1 | **Merged** |
| Seatek | 130 | abhimehro | `bolt/optimize-code-health-*` | PERFORMANCE | PASS | MERGEABLE | 1 | **Conflicting** after #129 → escalate |
| ctrld-sync | 709 | abhimehro | `palette-ux-emojis-*` | UX | PASS | CONFLICTING | 2 | **Closed** duplicate vs #716 |
| ctrld-sync | 711 | abhimehro | `ux-no-color-emojis-*` | UX | PASS | MERGEABLE | 3 | **Closed** duplicate vs #716 |
| ctrld-sync | 712 | abhimehro | `sentinel-explicit-loopback-*` | SECURITY | PASS | MERGEABLE | 3 | **Merged** (preferred SSRF fix + tests) |
| ctrld-sync | 714 | abhimehro | `sentinel-fix-ssrf-loopback-*` | SECURITY | PASS | MERGEABLE | 1 | **Merged** |
| ctrld-sync | 715 | abhimehro | `sentinel-fix-ssrf-loopback-*` | SECURITY | PASS | MERGEABLE | 2 | **Closed** superseded by #712 |
| ctrld-sync | 716 | abhimehro | `fix-cli-output-fallbacks-*` | UX | PASS | MERGEABLE | 3 | **Merged** |
| email | 646 | abhimehro | `jules-*` | UX | PASS | MERGEABLE | 3 | **Closed** superseded by #662 |
| email | 650 | abhimehro | `palette/ux-*` | UX | FAIL (submit-pypi) | MERGEABLE | 2 | **Closed** superseded by #662 |
| email | 651 | app/dependabot | `dependabot/pip/*` | DEPENDENCY | pending/mixed → later PASS | MERGEABLE | 1 | **Escalate** transformers 5.0.0rc3 |
| email | 656 | abhimehro | `palette/cli-*` | UX | PASS | MERGEABLE | 2 | **Closed** superseded by #662 |
| email | 657 | abhimehro | `sentinel-fix-assert-*` | SECURITY | PASS | MERGEABLE | 1 | **Merged** |
| email | 658 | abhimehro | `jules-*` | PERFORMANCE | PASS | MERGEABLE | 3 | **Merged** |
| email | 659 | abhimehro | `jules-*` | CHORE | PASS | MERGEABLE | 1 | **Merged** |
| email | 660 | abhimehro | `automation-workflow-*` | CI/INFRA | PASS | MERGEABLE | 2 | **Draft** → escalate |
| email | 662 | abhimehro | `palette-improve-*` | UX | PASS | MERGEABLE | 1 | **Merged** |
| dotfiles-iac | 747 | abhimehro | `palette-accessible-*` | UX | PASS | MERGEABLE | 4 | **Closed** redundant vs #760/#754 |
| dotfiles-iac | 748 | abhimehro | `sentinel/fix-option-injection-*` | SECURITY | PASS | MERGEABLE | 2 | **Merged** |
| dotfiles-iac | 751 | abhimehro | `fix-spinner-terminal-*` | UX | PASS | MERGEABLE | 5 | **Closed** superseded |
| dotfiles-iac | 752 | abhimehro | `fix/option-injection-pgrep-*` | SECURITY | PASS | MERGEABLE | 3 | **Closed** superseded by #748 |
| dotfiles-iac | 754 | abhimehro | `palette/cli-spinner-artifacts-*` | UX | PASS | MERGEABLE | 4 | **Merged** |
| dotfiles-iac | 756 | abhimehro | `automation-workflow-*` | CI/INFRA | PASS | MERGEABLE | 1 | **Draft** → escalate |
| dotfiles-iac | 758 | abhimehro | `jules-*` | PERFORMANCE | PASS | MERGEABLE | 2 | **Merged** |
| dotfiles-iac | 760 | abhimehro | `palette-cli-spinner-cleanup-*` | UX | PASS | MERGEABLE | 2 | **Merged** |

## Post-session remainder (open, in-scope)

| Repo | PR | Reason still open |
| ---- | --: | ----------------- |
| dotfiles-iac | 756 | Draft workflow consolidation — escalated |
| email-security-pipeline | 660 | Draft workflow consolidation — escalated |
| email-security-pipeline | 651 | RC major dependency bump — escalated |
| Seatek_Analysis | 130 | Merge conflict after #129 — escalated |

## Summary counts (initial inventory)

- **Total in-scope open:** 28
- **By theme:** SECURITY 6 · PERFORMANCE/UX 18 · DEPENDENCY 1 · CI/INFRA (draft) 2 · CHORE 1

---

# Automated PR inventory — 2026-04-23 (review session)

**Config:** `tasks/pr-review-agent.config.yaml`
**Stale threshold:** 30 days
**Mode:** `review-and-merge` · **Merge strategy:** squash · **Auto-fix:** enabled

## Scope rules

1. **Configured bot logins:** `dependabot[bot]`, `renovate[bot]`, `google-labs-jules[bot]`
2. **Expanded automation:** Include PRs where GitHub shows `abhimehro` as author when **body** contains "PR created automatically by Jules"

## Current open inventory (2026-04-23)

| Repo | PR | Author | Branch | Category | CI Status | Mergeable | Files | Age | Notes |
| ---- | --: | ------ | ------ | -------- | --------- | --------- | ----: | --- | ----- |
| Hydrograph | **135** | abhimehro (Jules) | `bolt-replace-sum-with-any-*` | PERFORMANCE | **PASS** | CLEAN | 2 | 3 days | `.any()` optimization — **keep as canonical** |
| Hydrograph | **133** | abhimehro (Jules) | `bolt-any-optimization-*` | PERFORMANCE | **PASS** | CLEAN | 4 | 4 days | Superset of #135 — **close as superseded** |
| Hydrograph | **131** | abhimehro (Jules) | `bolt/optimize-sum-operations-*` | PERFORMANCE | **PASS** | CLEAN | 6 | 5 days | Superset of #133 — **close as superseded** |

## File overlap analysis

| File | #135 | #133 | #131 |
| ---- | :--: | :--: | :--: |
| `src/hydrograph_seatek_analysis/data/validator.py` | ✓ | ✓ | ✓ |
| `benchmark_boolean.py` | ✓ | ✓ | ✓ |
| `test_perf.py` | — | ✓ | ✓ |
| `.jules/bolt.md` | — | ✓ | ✓ |
| `utils/processor.py` | — | — | ✓ |
| `benchmark_array_cache.py` | — | — | ✓ |

**Observation:** PR #135 ⊂ PR #133 ⊂ PR #131 (nested supersets). All implement same optimization pattern.

## Disposition summary

| PR | Disposition | Rationale |
| --: | ----------- | --------- |
| 135 | **MERGE** | Most focused, recent, all gates pass |
| 133 | **CLOSE-DUPLICATE** | Superseded by #135 (subset) |
| 131 | **CLOSE-DUPLICATE** | Superseded by #135 (subset) |

## Summary counts

- **Total in-scope open:** 3
- **By theme:** PERFORMANCE 3
- **Action:** MERGE 1 · CLOSE-DUPLICATE 2
