# PR Triage — 2026-06-10

**Preflight:** PASS (6/6)  
**Mode:** salvage-and-cleanup (Phase 2)  
**Disposition key:** MERGE · CLOSE-SUPERSEDED · DEFER · ESCALATE · PHASE1-HANDOFF · SALVAGE

## Duplicate & overlap analysis

| Group | Keeper | Action on others | Rationale |
| --- | --- | --- | --- |
| Session doc drafts (personal-config) | **This salvage branch** | Close #1203 | Phase-1 morning draft superseded by 2026-06-10 salvage report |
| Workflow automation (pc/esp/sa) | **None** | Escalate #1201, #1066, #273 | Trust-boundary pin changes; same class as merged #1193 |
| Bolt sum optimization (ctrld-sync) | **None** | Defer #881 | Benchmark shows ~1.5–2× regression from list materialization |
| Seatek scanner salvage | **None** | Defer #261 | CodeScene green but diff drops `read_file_safe` guards |

No semantic duplicates among active code PRs. Hydrograph and series_correction queues are empty.

## Session dispositions (executed)

| Disposition | PRs | Count |
| --- | --- | ---: |
| **CLOSE-SUPERSEDED** | pc #1203 | 1 |
| **ESCALATE** | pc #1201; esp #1066; sa #273 | 3 |
| **DEFER** | ctrld #881; sa #261 | 2 |
| **PHASE1-HANDOFF** | pc #1204; esp #1068 | 2 |
| **SALVAGE** (new draft) | — | 0 |
| **MERGE** | — | 0 |

## Per-PR notes

### personal-config #1204 — PHASE1-HANDOFF

Jules Palette UX: adds `aria-hidden="true"` on decorative Infuse listing text. Substantive checks green; Swift CodeQL still in progress. Route to Phase 1 once CodeQL completes.

### personal-config #1201 — ESCALATE

Single-line change bumps `codescene-oss/pr-refactoring-agent` from commit pin `bc0d8b91` to tag `@v1.0.1`. Trust-boundary workflow automation — human review required (Lesson 0z pattern).

### ctrld-sync #881 — DEFER

Bolt replaces `sum(genexpr)` with `sum([list comp])` in four `main.py` locations. All tests/ruff/mypy/bandit/CodeScene pass; **benchmark** fails with ~1.5–2× regression. List materialization defeats the optimization intent. Close or revert to generators.

### email-security-pipeline #1066 — ESCALATE

Workflow automation: refactoring-agent pin bump + changelog checkout comment. All checks green. Trust-boundary — human review required.

### email-security-pipeline #1068 — PHASE1-HANDOFF

Palette: refactor ANSI string concatenations for non-TTY accessibility. CodeQL in progress; no substantive failures yet.

### Seatek_Analysis #273 — ESCALATE

Nine workflow YAML files with pin/version comment updates. All checks green. Trust-boundary — human review required.

### Seatek_Analysis #261 — DEFER

Salvage draft for scanner perf (#247). CodeScene now PASS, but diff **removes** `read_file_safe`, `MAX_FILE_SIZE`, and path-traversal/OOM tests. Do not merge; rebuild salvage preserving security helpers (Gate 2 failure despite green CodeScene).

## Security gate review

- **Trust-boundary (T2):** #1201, #1066, #273 — workflow action pin changes require maintainer approval.
- **Gate 2 regression:** #261 removes file-read security controls — blocks merge regardless of CodeScene.
- **Perf gate:** #881 benchmark failure is substantive, not flake (contrast Lesson 0dr when PR is unrelated).
