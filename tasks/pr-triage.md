# PR Triage — 2026-06-04 (Salvage 17:00)

**Preflight:** PASS (6/6)  
**Disposition key:** MERGE · DEFER · CLOSE-SUPERSEDED · CLOSE-NO-OP · SALVAGE-DRAFT

## Duplicate & overlap analysis

| Group | Keeper | Action on others | Rationale |
| --- | --- | --- | --- |
| ESP Zip Slip (Sentinel vs salvage) | **Draft #1008** | Close #1031 | Salvage includes journal entry + fuller guard; #1031 had pytest fail |
| Session doc artifacts (2026-06-02) | **#1160 / #1161** | Close #1151, #1155 | Newer session reports supersede conflicted/stale drafts |
| Jules zero-diff perf | — | Close #262 | Lesson 0b — no files changed |

## Session dispositions (executed)

| Disposition | PRs | Executed |
| --- | --- | --- |
| **MERGE** | sa #260; sc #97; pc #1163 | Squash-merged (all checks green) |
| **CLOSE-SUPERSEDED** | pc #1151, #1155; esp #1031 | Closed with cross-link comment |
| **CLOSE-NO-OP** | sa #262 | Zero-diff Jules PR closed |
| **DEFER** | esp #1030, #1006 | Comment posted; blocked on pytest / bandit |
| **SALVAGE-DRAFT (unchanged)** | pc #1154; esp #1008, #1021, #1023; sa #261; hg #227 | Awaiting human merge |

## Security notes

| PR | Tier | Assessment |
| --- | --- | --- |
| esp #1008 | T1 | Zip Slip tarfile guard — draft salvage; merge before T3 batch |
| esp #1023 | T1 | NLP eval false positive — draft, CI green |
| esp #1006 | CI/INFRA | Workflow consolidation; bandit blocked (Lesson 0z) |
| esp #1030 | DEFER | Refactor OK but tests stale vs main API |

## Ready-to-execute human actions

1. **Merge T1:** [esp#1008](https://github.com/abhimehro/email-security-pipeline/pull/1008), then [esp#1023](https://github.com/abhimehro/email-security-pipeline/pull/1023).  
2. **Merge T3 salvages:** [pc#1154](https://github.com/abhimehro/personal-config/pull/1154), [esp#1021](https://github.com/abhimehro/email-security-pipeline/pull/1021), [sa#261](https://github.com/abhimehro/Seatek_Analysis/pull/261), [hg#227](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/227).  
3. **Fix then merge:** [esp#1006](https://github.com/abhimehro/email-security-pipeline/pull/1006) (bandit), [esp#1030](https://github.com/abhimehro/email-security-pipeline/pull/1030) (adapt tests for removed `_set_secure_permissions`).  
4. **Merge session docs:** [pc#1160](https://github.com/abhimehro/personal-config/pull/1160), [#1161](https://github.com/abhimehro/personal-config/pull/1161), then this cycle's artifact PR.
