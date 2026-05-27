# PR Triage — 2026-05-26

**Preflight:** PASS (6/6)  
**Disposition key:** MERGE · CLOSE-DUPLICATE · CLOSE-SUPERSEDED · CLOSE-DEFERRED · CLOSE-CONFLICT · SALVAGE-DRAFT · ESCALATE · DEFER

## Conflict note (documentation only)

Morning review (`0 13 * * *`) and afternoon salvage (`0 17 * * *`) both wrote `tasks/pr-*` for the same date. Dispositions below are **reconciled to GitHub state**, not either snapshot alone.

## Duplicate / overlap groups

| Group | Keeper | Closed |
| --- | --- | --- |
| ESP spam perf | **#936** merged | #935 |
| ctrld dedup | **#849** merged | #847 |
| ESP TOCTOU | **#939** draft (v3) | #932 (v2 DIRTY) |
| ESP IMAP | **#940** draft (v3) | #933 (v2 DIRTY) |
| Seatek tests | **#227** draft (v3) | #223, #224 |
| series dead code | **#76** draft (v3) | #73; **#72** merged |
| Seatek Bolt cluster | **#226** merged | #209–#214 CONFLICTING |

## Final dispositions (ground truth)

| Disposition | PRs |
| --- | --- |
| **MERGE** | pc #1064, #1066, #1071, #1068, #1070, #1072; cs #849; esp #936; Seatek #226; Hydro #206; sc #72, #74 |
| **CLOSE-SUPERSEDED** | esp #932→939, #933→940; Seatek #223/#224→227; sc #73→76; cs #847; esp #935 |
| **CLOSE-DEFERRED** | esp #937 |
| **CLOSE-CONFLICT** | esp #905; Seatek #209–#214 |
| **SALVAGE-DRAFT** | esp #939, #940; Seatek #227; sc #76 |
| **DEFER** | pc #1065 |

## Morning vs afternoon on same PRs

| PR | Morning | Afternoon (actual) |
| --- | --- | --- |
| pc #1068, #1070 | ESCALATE (toolchain) | **MERGED** after full CI green |
| esp #932, #933 | ESCALATE / DEFER | **CLOSED** → v3 #939, #940 |
| sc #72, #73 | DEFER (CodeScene) | **#72 MERGED**; #73 → #76 |
| Seatek #223, #224 | ESCALATE | **CLOSED** → #227 |

## Human merge queue (priority)

1. **ESP #939** (T1 TOCTOU) → **#940** (IMAP)
2. **Seatek #227** → **series #76**
3. **personal-config #1065** after CodeScene review

## Escalations

No new security escalations. Morning session correctly flagged toolchain PRs; afternoon merged them after verification — document policy choice for future runs.
