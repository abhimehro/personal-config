# PR Triage — 2026-05-27 (end of day)

**Preflight:** PASS (6/6)  
**Disposition key:** MERGE · CLOSE-SUPERSEDED · CLOSE-ZERO-DIFF · SALVAGE-DRAFT · ESCALATE

## Duplicate / overlap groups (resolved)

| Group | Keeper | Closed |
| --- | --- | --- |
| ESP spam/NLP | **#943** merged | #942 |
| series path security | **#78** merged | #80 |
| scratch_triage perf | **#1076** merged | #1065 (v2 salvage obsolete) |
| ESP TOCTOU | **#947** v4 draft | #939 v3 DIRTY |
| ESP IMAP | **#948** v4 draft | #940 v3 UNSTABLE |
| ctrld sync message | **#851** merged | — |

## Final dispositions (GitHub ground truth)

| Disposition | PRs |
| --- | --- |
| **MERGE** | pc #1073, #1076, #1078; esp #943–945; Seatek #227, #229; sc #76–78; cs **#851** |
| **CLOSE-ZERO-DIFF** | pc #1077 |
| **CLOSE-SUPERSEDED** | pc #1065; esp #939→947, #940→948; sc #80 |
| **SALVAGE-DRAFT** | esp #947, #948 |
| **ESCALATE** | sc #81 |

## Human merge queue (priority)

1. **ESP [#947](https://github.com/abhimehro/email-security-pipeline/pull/947)** (T1 TOCTOU)
2. **ESP [#948](https://github.com/abhimehro/email-security-pipeline/pull/948)** (IMAP perf)
3. **series [#81](https://github.com/abhimehro/series_correction_project_updated/pull/81)** (Sentinel `from None`)

## Escalations

- **series #81:** MEDIUM Sentinel — exception context suppression; CI fully green; salvage agent does not auto-merge security-class PRs.
