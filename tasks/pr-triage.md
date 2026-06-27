# PR Triage — 2026-06-27

## Duplicate & overlap analysis

### Closed as duplicate / superseded

| Keeper | Closed | Overlap | Rationale |
|--------|--------|---------|-----------|
| pc #1366 (merged) | pc #1363 | 16/20 maintenance scripts — osascript `--` delimiter | #1366 is CRITICAL/HIGH, broader file set (archive, fish backup, smart_notifier) |
| — | Seatek #374 | 0 files | Zero-diff QA summary only; no code changes |

### Related clusters (resolved)

| Cluster | PRs | Resolution |
|---------|-----|------------|
| personal-config Sentinel osascript | #1363, #1366 | Merged #1366; closed #1363 |
| repoprompt-ce dependabot cache | #63, #62 | Both merged (distinct actions) |
| series_correction Bolt perf | #157, #158 | Both merged (distinct files/intent) |

### Superseded / stale

- No stale (>30d) bot PRs in scope.
- hg #292 remains open (3d old) — blocked on CI, not stale.

## Merge ordering applied

1. **Security** — pc #1366 (Sentinel osascript option injection)
2. **Dependencies** — ctrld #953, esp #1160, rpce #63, rpce #62
3. **UI / perf / refactor** — esp #1158, sc #157, sc #158, hg #301, rpce #67, #66, #65

## Blockers identified

| Blocker | Affected PRs | Type | Next step |
|---------|--------------|------|-----------|
| SHA→tag workflow pin regression | pc #1367 | CI/INFRA trust boundary | ESCALATE — restore commit SHA pins or human approval for tag policy |
| submit-pypi failing | hg #292 | recurring CI infra | DEFER — investigate PyPI publish workflow (since 2026-06-23) |
| Draft salvage report | pc #1362 | Phase 2 handoff | DEFER — Salvage Agent |

## Security gate notes

- **Merged #1366:** Adds `osascript ... --` delimiter before user-controlled notification args — defense-in-depth against AppleScript option injection. All gates passed.
- **Blocked #1367:** Regresses pinned SHAs to mutable `@v*` tags across 7 workflow files — violates supply-chain pinning policy (Lesson 0cr).
- No secrets, permission escalation, or CVE regressions in merged PRs.
- rpce security salvage cluster cleared — #62 merged checkout bump; no open security PRs remain.
