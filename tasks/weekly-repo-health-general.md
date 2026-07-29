# Task Specification: Weekly Repository Health & Housekeeping (General Repos)

**Authoritative runtime:** Cursor Automations (Option A) — see
[`docs/cursor-automations/weekly-repo-health.md`](../docs/cursor-automations/weekly-repo-health.md)
and paste-ready prompt
[`docs/cursor-automations/prompts/weekly-repo-health-general.md`](../docs/cursor-automations/prompts/weekly-repo-health-general.md).

| Field                                  | Value                                                                  |
| -------------------------------------- | ---------------------------------------------------------------------- |
| Schedule                               | Weekly **Thursday 10:00** (`America/Chicago` recommended)              |
| Automation name                        | `Weekly Repo Health — General`                                         |
| Local launchd stub (non-authoritative) | `com.speedybee.repo-health.general` — logs only; does not spawn agents |

## Repositories

1. `@abhimehro/personal-config`
2. `@abhimehro/email-security-pipeline`
3. `@abhimehro/ctrld-sync`
4. `@abhimehro/repoprompt-ce`

## Scope

Exclude security review and PR review (covered by daily automations). Assess:

1. **Code health & performance** — technical debt, dead code, complex modules,
   easy wins.
2. **Documentation** — README / setup / AGENTS.md gaps and drift.
3. **Repository upkeep** — stale branches, outdated dependencies (drift),
   missing templates, broken/stale Actions.

## Allowed actions

- Open draft PRs and/or file GitHub / Linear / Notion issues.
- Run lightweight checks and full test suites when cheap; plan (don’t require)
  heavy builds (`repoprompt-ce`).
- Orchestrate subagents; prioritize from Memories / prior session findings.
- Never merge; never touch auth/secrets/DB schemas / live DNS paths without
  human approval.

## Deliverable

Single prioritized markdown report (final agent message): grouped by repo;
`[High/Medium/Low] one-line, file/branch ref`; **Suggested Next Actions** at
end.
