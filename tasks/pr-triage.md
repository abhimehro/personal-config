# PR Triage — 2026-06-05 (Salvage 17:00 UTC)

**Preflight:** PASS (6/6)  
**Disposition key:** MERGE · DEFER · CLOSE-SUPERSEDED · ESCALATE · SALVAGE-DRAFT · READY-FOR-REVIEW

## Duplicate & overlap analysis

| Group | Keeper | Action on others | Rationale |
| --- | --- | --- | --- |
| Palette perf-report WCAG | **Salvage #1172** | Close #1165 | #1165 CONFLICTING; #1171 is separate file (infuse-media-server ARIA) |
| ESP threat metrics #972 | **Salvage #1036** | Close #1030 | v3 branch removed `_set_secure_permissions`; tests failed |
| ESP import os #996 | **Salvage #1037** | Close #1021 | v2 CONFLICTING; v3 module-level import only |

## Session dispositions (executed)

| Disposition | PRs | Executed |
| --- | --- | --- |
| **MERGE** | pc #1169; sa #263 | Squash-merged (CLEAN required checks) |
| **SALVAGE-DRAFT** | pc #1172; esp #1036, #1037 | Opened draft; originals closed with cross-link |
| **CLOSE-SUPERSEDED** | pc #1165; esp #1030, #1021 | Closed with salvage comment |
| **READY-FOR-REVIEW** | esp #1023 | Marked ready (all required checks were green) |
| **DEFER** | pc #1154, #1171; esp #1006, #1008; sa #261; hg #227 | Human merge when CI green / fix bandit |

## Security notes

| PR | Tier | Assessment |
| --- | --- | --- |
| sa #263 | T1 | Subprocess env denylist — merged |
| esp #1008 | T1 | Zip Slip tarfile — draft, merge first in queue |
| esp #1023 | T1 | NLP eval false positive — ready for human merge |
| pc #1169 | T3 | Perf only — merged |

## Ready-to-execute human actions

1. **Merge T1:** [esp#1008](https://github.com/abhimehro/email-security-pipeline/pull/1008), then [esp#1023](https://github.com/abhimehro/email-security-pipeline/pull/1023) when CI stable.  
2. **Merge new salvages:** [esp#1036](https://github.com/abhimehro/email-security-pipeline/pull/1036), [esp#1037](https://github.com/abhimehro/email-security-pipeline/pull/1037), [pc#1172](https://github.com/abhimehro/personal-config/pull/1172).  
3. **Merge Palette:** [pc#1171](https://github.com/abhimehro/personal-config/pull/1171) when swift/analyze pending clears.  
4. **Fix then merge:** [esp#1006](https://github.com/abhimehro/email-security-pipeline/pull/1006) (bandit).  
5. **Merge session docs:** [pc#1170](https://github.com/abhimehro/personal-config/pull/1170) after this branch lands.
