# PR Triage — 2026-06-02 (Salvage 17:00)

**Preflight:** PASS (6/6)  
**Disposition key:** MERGE · DEFER · CLOSE-SUPERSEDED · ESCALATE · SALVAGE-DRAFT

## Duplicate & overlap analysis

| Group | Keeper | Action on others | Rationale |
| --- | --- | --- | --- |
| ESP daily QA | **#1013** | Close #1014 | Identical diff |
| ESP Palette Spinner | **#1017** | Close #1016 | Same UX intent |
| pc scratch_inventory perf | **#1150 (merged)** | Close salvage #1146 | Tuple approach superseded or-chain helpers (0dp) |
| pc run_merges parallel | **Salvage #1154 v3** | Close #1145 | DIRTY after main cascade |
| ESP test batch | **#1018–#1023** | Close #972, #982, #984, #989, #996, #973 | Intent-files-only v2 rebuilds |

## Session dispositions (executed)

| Disposition | PRs | Executed |
| --- | --- | --- |
| **MERGE** | pc #1152, #1150; esp #1013 | Squash-merged |
| **SALVAGE-DRAFT** | pc #1154; esp #1018–#1023 | Opened draft; originals closed |
| **CLOSE-SUPERSEDED** | pc #1145→1154, #1146→1150; esp #1014, #1016, #972–#996, #973 | Closed with cross-link |
| **DEFER (human)** | esp #1006, #1008, #1009, #992, #1017; pc #1153 | Awaiting CI / bandit fix |
| **SESSION-DOC** | pc #1151 | Supersede after artifacts commit |

## Security notes

| PR | Tier | Assessment |
| --- | --- | --- |
| pc #1152 | T1 | Eval guard in trap restore — merged |
| esp #1008 | T1 | Zip Slip tarfile — draft salvage, human merge |
| esp #1023 | T2 | NLP eval false-positive — draft salvage |
| esp #1006 | CI/INFRA | Workflow consolidation; bandit SHA gate blocked (0y/0z) |

## Ready-to-execute human actions

1. **Merge T1:** [esp#1008](https://github.com/abhimehro/email-security-pipeline/pull/1008) after CI green.  
2. **Merge T3:** [pc#1154](https://github.com/abhimehro/personal-config/pull/1154) run_merges parallelization.  
3. **Merge test salvages:** [esp#1018–#1023](https://github.com/abhimehro/email-security-pipeline/pulls) when pytest green.  
4. **Fix then merge:** [esp#1006](https://github.com/abhimehro/email-security-pipeline/pull/1006) — pin all action SHAs.  
5. **Close** [pc#1151](https://github.com/abhimehro/personal-config/pull/1151) after merging this session's artifact PR.
