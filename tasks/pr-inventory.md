# Bot / automated PR inventory

**Session:** backlog cleanup test (review-and-merge), **snapshot:** 2026-03-19 (execution)  
**Config:** `tasks/pr-review-agent.config.yaml` — 5 repos, squash merge, stale threshold 30d, auto-fix enabled.

## Scope rules

- **Primary authors:** `dependabot[bot]`, `renovate[bot]` (none were open in this snapshot).
- **Expanded scope:** PRs with visible author `abhimehro` when **Jules / automation markers** are present (branch prefixes `sentinel-`, `palette-`, `bolt/`, `bolt-`, `ux-`, emoji titles 🛡️/🎨/⚡, `.jules/*` learnings in diff, PR body/tooling).

## Summary

| Repo | Open (in-scope) at start | After session |
|------|--------------------------|---------------|
| `abhimehro/personal-config` | 3 | 0 |
| `abhimehro/ctrld-sync` | 0 | 0 |
| `abhimehro/email-security-pipeline` | 1 | 0 |
| `abhimehro/Seatek_Analysis` | 6 | 0 |
| `abhimehro/Hydrograph_Versus_Seatek_Sensors_Project` | 5 | 0 |
| **Total** | **15** | **0** |

## Open PRs (at start) — field inventory

| Repo | PR | Author (UI) | Category | CI (summary) | Conflicts | Notes |
|------|-----|---------------|----------|--------------|-----------|--------|
| personal-config | 648 | abhimehro (Jules) | SECURITY | UNSTABLE — Codacy Security Scan fail; tests/lint pass | None | Sentinel CWE-78 / eval |
| personal-config | 647 | abhimehro (Jules) | UI | UNSTABLE — Codacy fail | None | Palette spinner |
| personal-config | 646 | abhimehro (Jules) | SECURITY | UNSTABLE — Codacy fail | None | Overlapped 648 |
| email-security-pipeline | 555 | abhimehro (Jules) | UI | UNSTABLE — CodeScene fail; pytest/Codacy pass | None | Palette spinner |
| Seatek_Analysis | 87–92 | abhimehro (Jules) | mixed | Mostly CLEAN | 91 vs main after prior merges | See triage |
| Hydrograph_Vs_Seatek | 79–83 | abhimehro (Jules) | mixed | CLEAN / UNSTABLE | 81/82 after 79/80 | See triage |

**Stale (30d):** none of the above exceeded 30 days inactive.
