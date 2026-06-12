# PR Triage — 2026-06-12

**Preflight:** PASS (6/6)  
**Mode:** salvage-and-cleanup (Phase 2)  
**Disposition key:** MERGE · CLOSE-SUPERSEDED · DEFER · ESCALATE · PHASE1-HANDOFF · SALVAGE

## Duplicate & overlap analysis

| Group | Keeper | Action on others | Rationale |
| --- | --- | --- | --- |
| Seatek pytest import (#276 vs salvage #303) | **#303** (draft) | Close #276 | Intent-file rebuild from `main` |
| Seatek parallel tests (#291 vs salvage #302) | **#302** (draft) | Close #291 | Append-only R test salvage |
| ESP setup wizard test (#1075 vs #1088) | **#1088** (draft) | Close #1075 | Test-only salvage; omit conflicting utility churn |
| ctrld benchmark (#881 closed) | **#885** (merged) | — | Prior Bolt defer resolved by benchmark re-baseline on main |
| Session doc (#1228) | **This salvage branch** | — | Phase-1 morning draft; separate from code salvage |

No semantic duplicates among remaining open code PRs.

## Session dispositions (executed)

| Disposition | PRs | Count |
| --- | --- | ---: |
| **SALVAGE** (draft opened + original closed) | sa #276→#303; sa #291→#302; esp #1075→#1088 | 3 |
| **DEFER** | sa #283, #282, #278, #261; ctrld #882, #886; scpu #114 | 7 |
| **CLOSE-SUPERSEDED** | sa #276, #291; esp #1075 | 3 |
| **MERGE** | — | 0 |
| **ESCALATE** | — | 0 |

## Per-PR notes

### Seatek_Analysis #276 → SALVAGE #303

One-line hygiene: remove unused `pytest` import. Rebuilt from `main`; `py_compile` verified locally.

### Seatek_Analysis #291 → SALVAGE #302

Append-only `tests/testthat/test-execute_tasks_parallel.R` (+94 lines). Tripwire: 75→169 lines vs main.

### email-security-pipeline #1075 → SALVAGE #1088

Intent-file-only: `tests/test_setup_wizard.py`. Main already exposes `OUTLOOK_AUTH_ERROR_TIP` / `_test_connection`. Full suite: **628 passed** locally.

### Seatek_Analysis #283 — DEFER (T1)

15-file Sentinel `shell=False` hardening. Requires v2 intent-file salvage or human conflict resolution — too large for blind checkout.

### Seatek_Analysis #282, #278, #261 — DEFER

Bolt perf (#282, #278) and prior scanner salvage (#261) remain `CONFLICTING` after `main` automation landed. `/cs-agent` markers already present.

### ctrld-sync #882 — DEFER

MERGEABLE; benchmark-only failure (Lesson 0ch). Palette placeholder-leak fix is substantive but blocked on perf gate.

### ctrld-sync #886 — DEFER

MERGEABLE; **ruff/test fail on `repository_automation_common.py` undefined names** — same errors reproduce on local `main` (infra on main, not PR diff). PR touches only `main.py` + `.jules/palette.md`.

### series_correction_project_updated #114 — DEFER

MERGEABLE; CodeScene-only failure on Bolt vectorization. Advisory per Lesson 0ce contrast (not T1 security).

## Remaining conflict queue (EOD)

```yaml
open_followups:
  - repo: abhimehro/Seatek_Analysis
    pr: 283
    reason: T1 security — 15-file DIRTY; needs v2 intent-file salvage
  - repo: abhimehro/Seatek_Analysis
    prs: [282, 278, 261]
    reason: Bolt/salvage batch still CONFLICTING after main movement
  - repo: abhimehro/ctrld-sync
    prs: [882, 886]
    reason: benchmark (#882) + main infra ruff breakage affecting CI (#886)
  - repo: abhimehro/series_correction_project_updated
    pr: 114
    reason: CodeScene advisory on Bolt vectorization
```

## Human review priority

1. **T3 routine salvage:** #303, #302, #1088 (draft, CI pending)
2. **T1 deferred:** #283 when ready for security review
3. **Infra note:** ctrld `repository_automation_common.py` ruff F821 on `main` — fix before merging unrelated Palette PRs
