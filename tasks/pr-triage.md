# PR Triage — 2026-07-29

| PR | Disposition | Rationale |
|----|-------------|-----------|
| ctrld #1075 | MERGE | Dependabot `actions/stale` 10→11 |
| ctrld #1074 | MERGE | Jules formatting-only `main.py` |
| esp #1380 | MERGE | Unused import removal |
| esp #1366 | MERGE | Checkout/first-interaction/download pins; 0er overturned (Lesson 0eu) |
| pc #1811 | MERGE | Equivalence-preserving `_SPACE_RE` + SC2148 shebang |
| pc #1808 | MERGE-AFTER-FIX | Secret isolation tests; merged main for shebang |
| esp #1381 | CLOSE-SUPERSEDED | Twin after #1366; two-dot regresses #1380 + CHANGELOG |
| hg #434 | ESCALATE | Python floor ^3.10→^3.12 + mypy blocking; docs/stub gaps |
| rpce #144 | REQUEST_CHANGES | a11y OK; Build shard 1 failing |

## Multi-model review synthesis

- **esp #1366 (opus):** approve — upload@v7/download@v8 intended; prior 0er block incorrect.
- **hg #434 (opus + gpt-5.5):** disagree on MERGE vs ESCALATE → **ESCALATE** (floor bump).
- **pc #1811/#1808 (opus):** both safe; merge order #1811→#1808.
