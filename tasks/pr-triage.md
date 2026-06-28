# PR Triage — 2026-06-28

## Duplicate & overlap analysis

### Closed as zero-diff

| PR | Rationale |
|----|-----------|
| Seatek #377 | Sentinel QA PR with 0 changed files vs `main` (same pattern as closed #374) |
| repoprompt-ce #69 | Jules QA Review Summary with 0 changed files vs `main` |

### Closed as security escalation

| PR | Rationale |
|----|-----------|
| personal-config #1372 | `automation-workflow-updates-*` branch regresses SHA pins to mutable tags (`@v9.0.0`, `@v6.1.0`). Recurring pattern (cf. closed #1367, Lesson 0cr). CI passes but supply-chain pinning weakened. |

### Related clusters (deferred)

| Cluster | PRs | Notes |
|---------|-----|-------|
| personal-config session reports | #1369, #1370 | Both draft cursor-agent docs from 2026-06-27. Non-blocking; merge one consolidated report when ready. |
| repoprompt-ce Palette a11y | #70 | Title claims icon-button labels but diff includes Apache→MIT license swap and large README rewrite. Salvage only the 4 Swift a11y lines onto a fresh branch. |

### Superseded

None. hg #292 submit-pypi was previously DEFER'd but now green after branch sync (Lesson 0cz); merged this session.

## Merge ordering applied

1. **Dependencies** — hg #292 (actions/cache SHA bump in pr-visual-recap.yml)
2. **Formatting** — esp #1161 (black/isort only, no logic changes)
3. **Performance** — rpce #71 (ISO8601DateFormatter static cache)

## Blockers identified

| Blocker | Affected PRs | Type | Next step |
|---------|--------------|------|-----------|
| SHA→tag workflow pins | pc #1372 (closed) | trust boundary | Human approves tag-vs-SHA policy; re-open with SHA pins only |
| License change bundled in UI PR | rpce #70 | legal/trust | ESCALATE — split a11y fix from LICENSE/README; never auto-merge license changes |
| Draft session docs | pc #1369, #1370 | non-blocking | Defer to salvage agent or human publish |

## Security gate notes

- Merged PRs: no secrets, permission escalation, or CVE regressions detected.
- rpce #70: **ESCALATE** — replaces Apache 2.0 with MIT and incorrect copyright holder; unrelated to stated Palette a11y scope.
- pc #1372: **ESCALATE-CLOSE** — mutable action tags bypass immutable SHA pinning policy.
