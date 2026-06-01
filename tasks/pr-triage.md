# PR Triage — 2026-06-01 (Salvage 17:00)

**Preflight:** PASS (6/6)  
**Disposition key:** MERGE · DEFER · CLOSE-SUPERSEDED · ESCALATE · SALVAGE-DRAFT

## Duplicate & overlap analysis

| Group | Keeper | Action on others | Rationale |
| --- | --- | --- | --- |
| run_merges Bolt parallel | **Salvage #1145** | Close #1132, #1125 | Same `run_merges.py` intent; #1125 subset of #1132 |
| scratch_triage Bolt | **Salvage #1147** | Close #1117 | Rebuilt from main |
| scratch_inventory Bolt | **Salvage #1146** | Close #1142 | Rebuilt from main |
| ESP tarfile Zip Slip | **Salvage #1008** | Close #999 | T1 security; conflicted original |
| Seatek TODO scanner | **Salvage #239** | Close #237 | Single-file salvage; omitted workflow-only churn |
| Session doc artifacts | **Salvage branch commit** | Supersede #1143 | Same-day `tasks/pr-*` on conflicted draft |

## Session dispositions (executed)

| Disposition | PRs | Executed |
| --- | --- | --- |
| **MERGE** | pc #1139, #1113, #1144; sc #92, #90; sa #238 | Squash-merged |
| **SALVAGE-DRAFT** | pc #1145–#1147; esp #1008; sa #239 | Opened draft; originals closed with cross-link |
| **CLOSE-SUPERSEDED** | pc #1132, #1125, #1117, #1142; esp #999; sa #237 | Closed with salvage comment |
| **DEFER** | esp #972, #973, #982, #984, #989, #996 | Comment posted; rebuild-from-main queue |
| **MERGE-AFTER-FIX** | esp #1006 | bandit failing — human + Lesson 0z |
| **MERGE when CLEAN** | esp #992, #1003 | UNSTABLE advisory checks |

## Security notes

| PR | Tier | Assessment |
| --- | --- | --- |
| pc #1139, #1113 | T1 | Eval/injection hardening — merged |
| sc #92 | T1 | CSV injection — merged |
| esp #1008 | T1 | Zip Slip tarfile guard — draft salvage |
| esp #1006 | CI/INFRA | Workflow consolidation; bandit gate blocked |

## Ready-to-execute human actions

1. **Merge T1:** [esp#1008](https://github.com/abhimehro/email-security-pipeline/pull/1008) after CI green.  
2. **Merge T3 salvages:** [pc#1145](https://github.com/abhimehro/personal-config/pull/1145), [#1146](https://github.com/abhimehro/personal-config/pull/1146), [#1147](https://github.com/abhimehro/personal-config/pull/1147), [sa#239](https://github.com/abhimehro/Seatek_Analysis/pull/239).  
3. **Fix then merge:** [esp#1006](https://github.com/abhimehro/email-security-pipeline/pull/1006) (bandit).  
4. **ESP test batch:** Rebuild #972–#996 from `main` in a follow-up salvage cycle (do not use Update branch).  
5. **Close** [pc#1143](https://github.com/abhimehro/personal-config/pull/1143) after merging session doc commit from salvage branch.
