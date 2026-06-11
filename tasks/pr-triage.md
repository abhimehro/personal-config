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
| DEFER | 10 | Seatek conflict batch + ctrld benchmark + doc overlap |
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
