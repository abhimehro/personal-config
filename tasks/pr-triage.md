# PR triage — automated PR review agent (2026-04-11)

**Preflight:** `bash scripts/preflight-gh-pr-automation.sh --config tasks/pr-review-agent.config.yaml` — **passed** (read-only).

## Merge ordering (executed)

1. **ctrld-sync:** #712 (Sentinel + tests) → #714 (complementary loopback guard) → #716 (Palette UX). Re-checked mergeability after each merge.
2. **dotfiles-iac:** #748 (Sentinel) → #758 (Bolt) → #760 (Palette) → #754 (Palette) → #759 (Jules CI pin; discovered mid-run). <!-- pragma: allowlist secret -->
3. **email-security-pipeline:** #657 (Sentinel) → #658 (Bolt) → #659 (chore) → #662 (Palette) — then close duplicate Palette PRs.
4. **Seatek_Analysis:** #129 → attempted #130 (**blocked** — conflicting after base update).
5. **Hydrograph:** #116 → close #112 / #114 as superseded.

## Dispositions table

| Repo | PR | Category | Disposition | Rationale |
| ---- | --: | -------- | ----------- | --------- |
| ctrld-sync | 712 | SECURITY | **MERGED** | SSRF loopback tests + implementation; CI green |
| ctrld-sync | 714 | SECURITY | **MERGED** | Small complementary guard; CI green |
| ctrld-sync | 716 | UX | **MERGED** | Canonical NO_COLOR / completion UX |
| ctrld-sync | 715 | SECURITY | **CLOSED** | Superseded by #712; conflicting after merge |
| ctrld-sync | 711 | UX | **CLOSED** | Duplicate of merged #716 |
| ctrld-sync | 709 | UX | **CLOSED** | Superseded by #716 |
| dotfiles-iac | 748 | SECURITY | **MERGED** | CWE-88 hardening; CI green |
| dotfiles-iac | 752 | SECURITY | **CLOSED** | Superseded by #748 |
| dotfiles-iac | 758 | PERFORMANCE | **MERGED** | Bolt date parsing; CI green |
| dotfiles-iac | 760 | UX | **MERGED** | Spinner cleanup; CI green |
| dotfiles-iac | 754 | UX | **MERGED** | Spinner artifacts; CI green |
| dotfiles-iac | 747 | UX | **CLOSED** | Redundant vs merged stack; conflicting |
| dotfiles-iac | 751 | UX | **CLOSED** | Superseded by #754/#760; conflicting |
| dotfiles-iac | 759 | CI/INFRA | **MERGED** | Jules PR: pin `actions/checkout` SHA; checks green |
| dotfiles-iac | 756 | CI/INFRA | **ESCALATE** | Draft workflow consolidation — trust boundary |
| email | 657 | SECURITY | **MERGED** | B101 / assert hygiene; CI green |
| email | 658 | PERFORMANCE | **MERGED** | Unicode sanitization path; CI green |
| email | 659 | CHORE | **MERGED** | Formatting only; CI green |
| email | 662 | UX | **MERGED** | Canonical Palette CLI summary |
| email | 646 | UX | **CLOSED** | Superseded by #662 |
| email | 650 | UX | **CLOSED** | Superseded by #662; `submit-pypi` fail unrelated to code (lesson 0f) |
| email | 656 | UX | **CLOSED** | Superseded by #662 |
| email | 651 | DEPENDENCY | **ESCALATE** | `transformers` **5.0.0rc3** — major RC; needs human call |
| email | 660 | CI/INFRA | **ESCALATE** | Draft workflows — permissions / pins review |
| Seatek | 129 | PERFORMANCE | **MERGED** | CI green |
| Seatek | 130 | PERFORMANCE | **ESCALATE** | Conflicting after #129; needs merge-from-main |
| Hydro | 116 | PERFORMANCE | **MERGED** | Canonical redundant-sort fix |
| Hydro | 112 | PERFORMANCE | **CLOSED** | Superseded by #116 |
| Hydro | 114 | PERFORMANCE | **CLOSED** | Superseded by #116 |

## Automation expansion (policy reminder)

Include when **any** of: bot author, Dependabot branch, branch/title/body matches Jules/Sentinel/Bolt/Palette/`automation-workflow-*`, or Jules task link in body.
