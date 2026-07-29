# Task Specification: Weekly Repository Health & Housekeeping (Research Repos)

**Authoritative runtime:** Cursor Automations (Option A) — see
[`docs/cursor-automations/weekly-repo-health.md`](../docs/cursor-automations/weekly-repo-health.md)
and paste-ready prompt
[`docs/cursor-automations/prompts/weekly-repo-health-research.md`](../docs/cursor-automations/prompts/weekly-repo-health-research.md).

| Field                                  | Value                                                                   |
| -------------------------------------- | ----------------------------------------------------------------------- |
| Schedule                               | Weekly **Monday 10:00** (`America/Chicago` recommended)                 |
| Automation name                        | `Weekly Repo Health — Research`                                         |
| Local launchd stub (non-authoritative) | `com.speedybee.repo-health.research` — logs only; does not spawn agents |

## Repositories

1. `@abhimehro/series_correction_project_updated`
2. `@abhimehro/Hydrograph_Versus_Seatek_Sensors_Project`
3. `@abhimehro/Seatek_Analysis`

## Scope

Exclude security review and PR review (covered by daily automations). Assess:

1. **Code health & performance** — technical debt, dead code, complex modules,
   easy wins (e.g. NumPy/Pandas vectorization).
2. **Documentation** — README / setup / data-format / AGENTS.md gaps and drift.
3. **Repository upkeep** — stale branches, outdated dependencies (drift),
   missing templates, broken/stale Actions.

## Allowed actions

- Open draft PRs and/or file GitHub / Linear / Notion issues.
- Run lightweight checks and full test suites when cheap; plan (don’t require)
  heavy builds.
- Orchestrate subagents; prioritize from Memories / prior session findings.
- Never merge; never touch auth/secrets/DB schemas without human approval.

## Deliverable

Single prioritized markdown report (final agent message): grouped by repo;
`[High/Medium/Low] one-line, file/branch ref`; **Suggested Next Actions** at
end.
