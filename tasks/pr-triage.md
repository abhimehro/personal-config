# PR Triage — 2026-06-03 (Salvage 17:00)

**Preflight:** PASS (6/6)  
**Disposition key:** MERGE · DEFER · CLOSE-SUPERSEDED · CLOSE-DUPLICATE · ESCALATE · SALVAGE-DRAFT

## Duplicate & overlap analysis

| Group | Keeper | Action on others | Rationale |
| --- | --- | --- | --- |
| ESP NLP eval false positive | **#1023** | Close #1024 | Same `nlp_analyzer.py` fix; #1024 is bloated Jules branch (Lesson 0dd) |
| Hydrograph Bolt perf | **Salvage #227** | Close #223, #224 | Combined src-only rebuild; #224 had 20+ junk paths |
| Seatek clean_vals tests | **Salvage #260** | Close #249 | Test file only; original had R/workflow churn |
| Seatek scanner perf | **Salvage #261** | Close #247 | 2-file rebuild; original dropped unrelated R edits |
| ESP threat metrics | **Salvage #1030** | Close #1022 | v3 from main; #1022 was DIRTY |
| Session doc artifacts | **#1160** | Close #1151 when merged | #1151 conflicted 2026-06-02 snapshot |

## Session dispositions (executed)

| Disposition | PRs | Executed |
| --- | --- | --- |
| **SALVAGE-DRAFT** | hg → #227; sa → #260, #261; esp → #1030 | Opened draft; originals closed with cross-link |
| **CLOSE-SUPERSEDED** | hg #223, #224; sa #247, #249; esp #1022 | Closed with salvage comment |
| **CLOSE-DUPLICATE** | esp #1024 | Closed; canonical #1023 |
| **DEFER** | pc #1154 | Shell Script Quality + CodeScene failing on salvage v3 |
| **MERGE (human)** | esp #1008, #1021, #1023 | Converted to draft; CLEAN salvages await human squash |
| **MERGE-AFTER-FIX** | esp #1006 | UNSTABLE; workflow/bandit |

## Security notes

| PR | Tier | Assessment |
| --- | --- | --- |
| esp #1008 | T1 | Zip Slip tarfile guard — draft; merge first |
| esp #1023 | T1 | NLP eval false positive — CLEAN draft |
| esp #1021, #1030 | T3 | Refactor only |
| hg #227, sa #261 | T3 | Perf / tooling |

## Ready-to-execute human actions

1. **Merge T1 drafts (CI green):** [esp#1008](https://github.com/abhimehro/email-security-pipeline/pull/1008), [esp#1023](https://github.com/abhimehro/email-security-pipeline/pull/1023).  
2. **Merge T3 CLEAN drafts:** [esp#1021](https://github.com/abhimehro/email-security-pipeline/pull/1021).  
3. **Merge new salvages when stable:** [hg#227](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/227), [sa#260](https://github.com/abhimehro/Seatek_Analysis/pull/260), [sa#261](https://github.com/abhimehro/Seatek_Analysis/pull/261), [esp#1030](https://github.com/abhimehro/email-security-pipeline/pull/1030).  
4. **Fix then merge:** [pc#1154](https://github.com/abhimehro/personal-config/pull/1154) (Shell Script Quality).  
5. **Merge doc drafts:** [pc#1160](https://github.com/abhimehro/personal-config/pull/1160), then close [pc#1151](https://github.com/abhimehro/personal-config/pull/1151).  
6. **Infra:** [esp#1006](https://github.com/abhimehro/email-security-pipeline/pull/1006) after bandit/advisory checks pass.
