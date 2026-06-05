# PR Triage — 2026-06-05

**Preflight:** PASS (6/6)  
**Disposition key:** MERGE · MERGE-AFTER-FIX · DEFER · CLOSE-SUPERSEDED · ESCALATE

## Duplicate & overlap analysis

| Group | Keeper | Action on others | Rationale |
| --- | --- | --- | --- |
| `run_merges.py` Bolt / parallel | **None (defer)** | #1169, #1154 | Overlapping hot file; #1154 is salvage draft with failing Shellcheck |
| Session `tasks/pr-*` docs | **This branch PR** (`cursor-agent/automated-pr-workflow-d2f3`) | Close #1160, #1161, #1164 | Superseded by 2026-06-05 review session artifacts |
| ESP threat-metrics salvage | **Rebuild queue** | #1030 | pytest failing on `main.py` flatten |
| ESP tarfile T1 | **#1008** (human) | — | CodeScene failing; security-sensitive — merge only when advisory green |

## Session dispositions

| Disposition | PRs | Notes |
| --- | --- | --- |
| **MERGE** | pc #1166; esp #1034 | T1 security; all required checks green |
| **ESCALATE** | pc #1169; sa #263 | Touches PR automation toolchain (`run_merges.py`, `scratch_triage.py`, `.github/scripts/repository_automation_common.py`) |
| **DEFER** | pc #1165, #1154; esp #1030, #1008, #1021, #1023; sa #261; hg #227 | Conflicts, failing CI, or draft salvage awaiting human |
| **MERGE-AFTER-FIX** | esp #1006 | bandit failure on workflow consolidation |
| **CLOSE-SUPERSEDED** | pc #1160, #1161, #1164 | Older session-doc drafts replaced by this run |

## Security notes

| PR | Tier | Assessment |
| --- | --- | --- |
| pc #1166 | T1 | Removes `eval` on trap restore strings via subshell — **merged** |
| esp #1034 | T1 | `0o600` on config fd before write — **merged** |
| esp #1008 | T1 | Zip Slip guard — draft; CodeScene blocked |
| sa #263 | T1 | Subprocess allowlist — **escalated** (`.github/scripts/` trust boundary) |
| pc #1169 | T3 | Performance only but edits merge automation scripts — **escalated** |

## Ready-to-execute human actions

1. **Review escalated:** [pc#1169](https://github.com/abhimehro/personal-config/pull/1169), [sa#263](https://github.com/abhimehro/Seatek_Analysis/pull/263).  
2. **Merge T1 draft when green:** [esp#1008](https://github.com/abhimehro/email-security-pipeline/pull/1008).  
3. **Fix bandit then merge:** [esp#1006](https://github.com/abhimehro/email-security-pipeline/pull/1006).  
4. **Rebase conflict:** [pc#1165](https://github.com/abhimehro/personal-config/pull/1165) after #1166 on `main`.  
5. **Rebuild ESP test salvages:** #1030 (pytest), then mark #1021/#1023 ready if still desired.  
6. **Salvage drafts (CodeScene advisory):** [sa#261](https://github.com/abhimehro/Seatek_Analysis/pull/261), [hg#227](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/227), [pc#1154](https://github.com/abhimehro/personal-config/pull/1154).
