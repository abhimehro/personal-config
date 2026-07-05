# PR Triage — 2026-07-05 (evening salvage)

## Context

Morning Phase 1 (cron 13:00 UTC) cleared 27/31 PRs; artifacts merged via [#1504](https://github.com/abhimehro/personal-config/pull/1504). This evening salvage pass (cron 17:00 UTC) processes the 9-PR tail plus any new bot PRs opened during the day.

## Starting state (9 in-scope open)

| Repo | PR | State | Action |
|------|-----|-------|--------|
| email-security-pipeline | #1229 | CLEAN zero-diff | MERGE |
| personal-config | #1504 | UNSTABLE (Trunk MQ) session doc | MERGE |
| personal-config | #1505 | UNSTABLE (swift pending) | DEFER |
| ctrld-sync | #983 | UNSTABLE (CodeScene) | SALVAGE |
| series_correction_project_updated | #178 | DIRTY refactor | SALVAGE file-scoped |
| series_correction_project_updated | #195 | T1 security salvage draft | DEFER — human review |
| repoprompt-ce | #91 | Style fail | DEFER |
| repoprompt-ce | #92 | Style + Build fail | DEFER |

## Duplicate & overlap analysis

### Closed as superseded

| Closed | Salvage | Reason |
|--------|---------|--------|
| sc #178 | [#197](https://github.com/abhimehro/series_correction_project_updated/pull/197) | DIRTY after morning cascade; excluded `tasks/todo.md` |
| cs #983 | [#984](https://github.com/abhimehro/ctrld-sync/pull/984) | CodeScene gate; builds on #979/#981 TTY work |

### No-op merges

| Merged | Reason |
|--------|--------|
| esp #1229 | Zero-diff Daily QA — all 676 tests pass on `main` already |
| pc #1504 | Session artifacts from morning Phase 1 |

## Merge ordering applied

1. **QA no-op** — esp #1229 (CLEAN)
2. **Session doc** — pc #1504 (artifacts land on `main`)
3. **Salvage** — sc #178 → draft #197; cs #983 → draft #984
4. **Defer** — pc #1505, sc #195, rpce #91/#92

## Blockers identified

| Blocker | Affected PRs | Type | Resolution |
|---------|--------------|------|------------|
| CodeScene code health | cs #983 | PR-specific | `/cs-agent` posted; salvage draft #984 |
| DIRTY merge cascade | sc #178 | conflict | File-scoped salvage #197 (58 pytest pass) |
| Swift Analyze pending | pc #1505 | CI latency | Defer until green |
| SwiftFormat Style | rpce #91, #92 | tooling | Defer — needs macOS format lane |
| T1 security salvage policy | sc #195 | trust boundary | Never autonomous merge |

## Security gate notes

- esp #1229: zero-diff QA review; no code changes.
- sc #195: T1 security salvage from #184 — remains draft for human review.
- Salvage drafts #197 and #984 are T3 only; opened as **draft** per salvage policy S1.
- No force-pushes. All salvage work done in `/tmp/salvage-*` clones.
