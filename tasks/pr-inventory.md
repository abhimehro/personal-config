# Bot / automated PR inventory

**Session:** one-time backlog cleanup test (review-and-merge), **snapshot:** 2026-03-22  
**Config:** `tasks/pr-review-agent.config.yaml` — 5 repos, squash merge, stale threshold 30d, auto-fix enabled, schedule none.

## Scope rules

- **Primary authors:** `dependabot[bot]`, `renovate[bot]`, `google-labs-jules[bot]` (no open PRs from Dependabot/Renovate in this snapshot).
- **Expanded scope:** PRs with visible author `abhimehro` when automation markers are present:
  - Branch prefixes: `sentinel-`, `sentinel/`, `palette-`, `bolt/`, `bolt-`, `ux-`, `jules-`, `automation-workflow-`
  - Title prefixes: 🛡️ Sentinel, 🎨 Palette, ⚡ Bolt
  - PR body: “PR created automatically by Jules”, `jules.google.com/task`, consolidated automation workflow text, Co-authored-by `google-labs-jules[bot]`

## Summary

| Repo | Open (in-scope) at start | Open after session |
|------|--------------------------|--------------------|
| `abhimehro/personal-config` | 3 | 2 |
| `abhimehro/ctrld-sync` | 2 | 1 |
| `abhimehro/email-security-pipeline` | 2 | 1 |
| `abhimehro/Seatek_Analysis` | 0 | 0 |
| `abhimehro/Hydrograph_Versus_Seatek_Sensors_Project` | 0 | 0 |
| **Total** | **7** | **4** |

## Open PRs — field inventory (at start)

| Repo | PR | Author (UI) | Category | CI (summary) | Conflicts | Notes |
|------|-----|-------------|----------|--------------|-----------|--------|
| personal-config | 658 | abhimehro (Jules) | PERFORMANCE | Core tests/CodeQL pass; `label` fail | None | Bolt; **100k-line `test.txt` artifact** |
| personal-config | 659 | abhimehro (Jules) | UI + scope creep | Partial (no full test rollup); `label` fail | **Yes** | Palette body; diff includes Docker/.cursor/network |
| personal-config | 660 | abhimehro (Jules) | SECURITY | Core tests pass; `label` fail | None | Sentinel CWE-78 `eval` → `printf -v` / `${!name}` |
| ctrld-sync | 655 | abhimehro (Jules) | PERFORMANCE | **ruff** fail → fixed | None | Bolt; lock contention in rate-limit parsing |
| ctrld-sync | 656 | abhimehro (Jules) | UI | **ruff**, **submit-pypi**, **CodeScene** issues | None | Palette; emoji branch name |
| email-security-pipeline | 565 | abhimehro (automation) | CI/INFRA | Mostly green; Trunk MQ pending earlier | None | Draft; **SHA → mutable tag** workflow bumps |
| email-security-pipeline | 566 | abhimehro (Jules) | UI | Green | None | Palette countdown UX |

**Stale (≥30d):** none (all recent).

## Prior session carry-over

`tasks/pr-review-2026-03-09.md` documented read-only tooling; this run executed **writes** (merge, push, comments) using `GH_TOKEN` as `abhimehro`.
