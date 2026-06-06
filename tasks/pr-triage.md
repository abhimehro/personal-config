# PR Triage — 2026-06-06

**Preflight:** PASS (6/6)  
**Disposition key:** MERGE · DEFER · CLOSE-SUPERSEDED · ESCALATE

## Duplicate & overlap analysis

| Group | Keeper | Action on others | Rationale |
| --- | --- | --- | --- |
| Session doc artifacts (2026-06-05) | **This session branch** | Close #1170, #1173 | Overlapping `tasks/pr-*` files; consolidated into 2026-06-06 report |
| run_merges parallel salvage | **None (rebuild)** | Close #1154 | CONFLICTING (DIRTY) after #1147+ merges; v3 stale |
| ESP tarfile Zip Slip | **#1008** | (original #999 already closed) | T1 security salvage — merged |
| ESP refactor salvages | **#1036, #1037** | (originals #972, #996 closed) | Independent files; both merged |

No new semantic duplicates detected among open PRs at session start.

## Session dispositions (executed)

| Disposition | PRs | Count |
| --- | --- | ---: |
| **MERGE** | pc #1174, #1171, #1172; esp #1008, #1023, #1036, #1037; sa #266; ctrld #871 | 9 |
| **CLOSE-SUPERSEDED** | pc #1154, #1170, #1173 | 3 |
| **DEFER** | esp #1006; sa #261; hg #227 | 3 |
| **ESCALATE** | — | 0 |

## Security gate review

| PR | Tier | Gate 2 result | Notes |
| --- | --- | --- | --- |
| pc #1174 | T1 | PASS | `pgrep`/`pkill` `--` terminator prevents CWE-88 option injection |
| esp #1008 | T1 | PASS | PEP-706 data filter + explicit `..` / absolute path guards on tar members |
| esp #1023 | T2 | PASS | `model.eval()` → `model.train(False)` equivalent; test formatting only |
| esp #1006 | CI/INFRA | DEFER | Workflow trust boundary + bandit failure — human required |

## CodeScene advisory failures (not security blockers)

Merged #1008 despite CodeScene fail: pytest, bandit, CodeQL, Snyk, GitGuardian all green.  
Deferred #261, #227: salvage perf PRs where CodeScene is sole failure.

## Infra-broken main check (Lesson 0t)

Not triggered — no 4+ PRs sharing the same required-check failure pattern on `main`.

## Ready-to-execute human actions

1. **Fix bandit then merge:** [esp#1006](https://github.com/abhimehro/email-security-pipeline/pull/1006) (workflow consolidation).  
2. **Merge when CodeScene acceptable:** [sa#261](https://github.com/abhimehro/Seatek_Analysis/pull/261), [hg#227](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/227).  
3. **Rebuild if needed:** `run_merges.py` parallelization from current `main` (supersedes closed #1154).
