# PR Triage — 2026-06-09

**Preflight:** PASS (6/6)  
**Mode:** salvage-and-cleanup (Phase 2)  
**Disposition key:** SALVAGE · CLOSE-SUPERSEDED · DEFER · ESCALATE

## Duplicate & overlap analysis

| Group | Keeper | Action on others | Rationale |
| --- | --- | --- | --- |
| Hydrograph Bolt perf salvage | **#241** (v2 draft) | Close #227 | #227 went `DIRTY` after `main` gained `_create_chart_metadata` / `_save_generated_chart`; v2 uses intent files only (Lesson 0cd) |
| Session doc artifacts (personal-config) | **This session branch** | Defer #1196, #1191, #1188 | Overlapping `tasks/pr-*` files; consolidated into 2026-06-09 report |
| Seatek scanner perf salvage | **#261** | (none) | Carried tail; CodeScene sole failure — human merge decision |
| Jules Palette spinner (personal-config) | **#1197** | Defer to Phase 1 | Not conflicted; MERGEABLE with substantive checks green |

No semantic duplicates among active bot queues. ctrld-sync, email-security-pipeline, and series_correction have zero open PRs.

## Session dispositions (executed)

| Disposition | PRs | Count |
| --- | --- | ---: |
| **SALVAGE** (new draft) | hg #241 | 1 |
| **CLOSE-SUPERSEDED** | hg #227 | 1 |
| **DEFER** | pc #1197; pc #1196, #1191, #1188; sa #261 | 5 |
| **ESCALATE** | — | 0 |

## Security gate review

| PR | Tier | Gate result | Notes |
| --- | --- | --- | --- |
| hg #241 | T3 perf salvage | PASS (local) | `data_loader.py` / `processor.py` only; pytest subset 26/26 green; GitGuardian green on push |
| hg #227 | — | N/A | Closed — conflicted branch superseded |
| sa #261 | T3 perf salvage | PASS (security) | lint-and-test, CodeQL, GitGuardian green; CodeScene advisory only |
| pc #1197 | UI | PASS | Spinner UX in non-TTY; tests green; no secrets/auth surface |

## CodeScene advisory failures (not security blockers)

- **sa #261**: scanner perf salvage — sole CodeScene failure (unchanged 5d tail).
- **hg #241**: awaiting CI; prior #227 had same pattern (Lesson 0ce contrast for perf vs security).

## Infra-broken main check (Lesson 0t)

No repo-wide infra breakage detected. Four repos have zero open PRs. Hydrograph conflict was branch drift on a stale salvage base, not `main` CI failure.

## Salvage decision tree outcomes

| Repo | PR | Tree outcome | Action |
| --- | ---: | --- | --- |
| Hydrograph | #227 | Conflict + valuable diff on intent files | v2 salvage branch; close original |
| Seatek | #261 | MERGEABLE; value retained; advisory CI | Defer for human review |
| personal-config | #1197 | Not in salvage queue (clean, not conflicted) | Hand off to Phase 1 |
