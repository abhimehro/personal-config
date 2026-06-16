# PR Triage — 2026-06-16

**Mode:** review-and-merge (Phase 1)  
**Preflight:** PASS (6/6)  
**Input:** Live GitHub state + deferred tail from 2026-06-15 session

## Triage matrix

| Disposition | Count | Action |
| --- | ---: | --- |
| MERGE | 16 | Squash-merge with green functional + CodeScene CI |
| CLOSE-DUPLICATE | 1 | #1253 superseded by #1255 |
| DEFER | 5 | CodeScene fail or post-merge DIRTY |
| ESCALATE | 1 | #1249 workflow action pin |

## Duplicate & overlap analysis

| Group | Keeper | Closed | Rationale |
| --- | --- | --- | --- |
| PC session docs (2026-06-15) | **#1255** | #1253 | Identical task files; #1255 adds `salvage-session-reports.md` |
| PC Palette a11y | **#1254 + #1259** | — | Non-overlapping files (`morning-brief.py` vs `performance_optimizer.sh`) |
| ctrld Bolt journal | — | — | #904 journal-only; became DIRTY after #905/#906/#902 merges |

## Gate outcomes

### Gate 1 — CI health

- **Merge:** 16 PRs with green required functional checks (pytest, bandit, shell tests, CodeScene where required).
- **Defer:** #1261, #901, #121, #262 — CodeScene Code Health Review failing.
- **Advisory only:** Devin Review fail on #904, #1249, #10 did not block merge when all other checks green.

### Gate 2 — Security

- **#1258 (Sentinel CWE-88):** Option injection hardening in shell scripts — merged first.
- **#905 (Sentinel):** Exception log sanitization in rate-limit parser — merged.
- **#1249:** Workflow action version pin — **ESCALATE** (trust boundary; no autonomous merge).

### Post-merge conflict cascade (Lesson 0)

After merging ctrld #905, #906, #902, sibling **#904** flipped to **DIRTY**. **#901** also became **CONFLICTING** (was MERGEABLE at session start). Both deferred with PR comments; no force-push.

## Per-PR notes

### personal-config #1249 — ESCALATE

Pins `codescene-oss/pr-refactoring-agent` to `v1.0.1`. Functional CI green. Requires human approval per CI/INFRA policy.

### personal-config #1261 — DEFER

Bolt dictionary fallback optimization. CodeScene reports hotspot decline. `/cs-agent skill:fix-code-health-degradations` posted 2026-06-16.

### ctrld-sync #901 / #904 — DEFER

#901: longstanding CodeScene fail on Content-Type `any()` unroll; now DIRTY.  
#904: anti-micro-optimization journal entry; DIRTY after sibling merges.

### series_correction #121 — DEFER

Vectorized Z-score/jump detection. CodeScene hotspot rules fail. `/cs-agent` posted.

### Hydrograph #262 — DEFER (Phase 2 salvage)

Draft salvage for #257 test coverage. CodeScene code duplication advisory fail. Awaiting salvage agent or human review.

## Merge ordering applied

1. Security (pc#1258, sa#318 dependabot, ctrld#905)
2. QA / autofix / routine green
3. Performance / UI / docs
4. Close duplicate session doc before merging superset (#1255)
