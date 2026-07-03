# PR Triage — 2026-07-03

## Starting state (6 in-scope open)

| Repo | PR | State | Action |
|------|-----|-------|--------|
| email-security-pipeline | #1212 | CLEAN all green | MERGE |
| personal-config | #1464 | UNSTABLE (Trunk MQ) but security green | MERGE |
| personal-config | #1470 | UNSTABLE (Gitleaks) + scope creep | CLOSE |
| personal-config | #1468 | UNSTABLE session doc | CLOSE — supersede |
| personal-config | #1466 | DIRTY + trust-boundary noise | SALVAGE file-scoped |
| ctrld-sync | #973 | DIRTY + CodeScene fail | SALVAGE file-scoped |

## Duplicate & overlap analysis

### Closed as superseded

| Closed | Reason |
|--------|--------|
| pc #1468 | Prior cron session-doc draft; consolidated into 2026-07-03 salvage run |
| cs #973 | Core isatty guards on `main` via #970; remaining newline/ANSI cleanup salvaged to #974 |
| pc #1466 | DIRTY conflict + `get_repo_vars.sh` excluded; metrics optimization salvaged to #1471 |

### Closed as not salvageable

| Closed | Reason |
|--------|--------|
| pc #1470 | Gitleaks fail on `tasks/todo.md` false positive; includes `.adk/session.db` binaries and unrelated files |

## Merge ordering applied

1. **Dependency** — esp #1212 (opencv pin, all CI green)
2. **CI/infra** — pc #1464 (action SHA bumps, Gitleaks green)
3. **Closures** — pc #1468 (session doc), pc #1470 (security gate)
4. **Salvage** — cs #973 → draft #974; pc #1466 → draft #1471

## Blockers identified

| Blocker | Affected PRs | Type | Resolution |
|---------|--------------|------|------------|
| Gitleaks + session.db artifacts | pc #1470 | security gate | Closed — needs human-focused PR |
| DIRTY after #970 merge | cs #973 | cascade | File-scoped salvage #974 |
| DIRTY + trust-boundary files | pc #1466 | conflict/noise | Salvage metrics only to #1471 |
| CodeScene code health | cs #973 | PR-specific | `/cs-agent` posted before close |

## Security gate notes

- esp #1212 passed GitGuardian, CodeScene, pytest, Snyk before merge.
- pc #1464 passed Gitleaks/TruffleHog before merge; action SHA pins only.
- pc #1470 failed Gitleaks — closed without merge.
- Salvage drafts are T3 only (display/perf); opened as **draft** per salvage policy.
