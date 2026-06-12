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
# PR Triage — 2026-06-11

**Mode:** salvage-and-cleanup (Phase 2)  
**Preflight:** PASS  
**Input:** Prior deferred tail from `tasks/pr-review-2026-06-09.md` + live GitHub state

## Triage matrix

| Disposition | Count | Action |
| --- | ---: | --- |
| SALVAGE (draft opened) | 5 | Human review required; originals closed |
| CLOSE-SUPERSEDED | 5 | Cross-linked to new draft PRs |
| PHASE1-HANDOFF | 5 | Re-run Phase 1 review-and-merge |
| DEFER | 13 | Seatek conflict batch (8) + ctrld benchmark (2) + ESP CodeScene (#1075) + session-doc overlap (#1205/#1216) |
| ESCALATE | 0 | — |
| MERGE (salvage policy) | 0 | Salvage never auto-merges |

## Conflict queue triage (priority order)

### Tier T1 — Security (deferred, needs v2 salvage)

| Repo | PR | Reason | Next step |
| --- | ---: | --- | --- |
| Seatek_Analysis | [#283](https://github.com/abhimehro/Seatek_Analysis/pull/283) | `shell=False` enforcement; 15-file Jules PR DIRTY | Rebuild v2 from `main` with security files only; cs-agent posted |

### Tier T2 — Trust-adjacent tooling (salvaged)

| Repo | Old | New draft | Status |
| --- | ---: | ---: | --- |
| personal-config | #1215 | [#1217](https://github.com/abhimehro/personal-config/pull/1217) | Closed #1215; 9 pytest pass |
| personal-config | #1211 | [#1218](https://github.com/abhimehro/personal-config/pull/1218) | Closed #1211; intent-file-only test salvage |

### Tier T3 — Routine perf/test (salvaged)

| Repo | Old | New draft | Verification |
| --- | ---: | ---: | --- |
| series_correction | #109 | [#112](https://github.com/abhimehro/series_correction_project_updated/pull/112) | 6 pytest (append, not replace) |
| Hydrograph | #245 | [#252](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/252) | 6 pytest |
| email-security-pipeline | #1071 | [#1081](https://github.com/abhimehro/email-security-pipeline/pull/1081) | 628 pytest |

### Tier DEFER — Seatek batch conflict cascade

All eight remaining `CONFLICTING`/`DIRTY` Seatek PRs share root cause: `main` moved under overlapping Jules/Bolt automation. Posted `/cs-agent skill:fix-code-health-degradations` on #276, #278, #282–#284, #286, #291 (#261 already had marker).

**Do not** use `update-branch` on these — rebuild v2 per Lesson 0cc / 0cg.

### Tier DEFER — ctrld-sync benchmark

| Repo | PR | Blocker |
| --- | ---: | --- |
| ctrld-sync | #881, #882 | `benchmark` check fail; all security gates green |

### Tier PHASE1 — CLEAN handoff

Merge candidates for next Phase 1 cycle (security-first order):

1. `email-security-pipeline#1066`, `Seatek#273`, `personal-config#1201` — workflow consolidation (trust boundary; human review)
2. `personal-config#1210` — Jules unit test
3. `Seatek#277` — Bolt perf (merge before conflicting siblings)

## Human follow-up (priority)

1. Review and merge draft salvages: [#112](https://github.com/abhimehro/series_correction_project_updated/pull/112), [#252](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/252), [#1081](https://github.com/abhimehro/email-security-pipeline/pull/1081)
2. Review T2 tooling salvages: [#1217](https://github.com/abhimehro/personal-config/pull/1217), [#1218](https://github.com/abhimehro/personal-config/pull/1218)
3. Plan Seatek #283 security v2 salvage (T1)
4. Phase 1 merge CLEAN handoffs listed above
5. Investigate ctrld-sync benchmark regression on #881/#882
