# PR Triage — 2026-07-27 (Phase 2)

Decision tree applied per `docs/automated-pr-salvage-agent.md` Step 4. **No autonomous merges (S1).**

## CLOSE-SUPERSEDED

### esp #1362 → main (#1353) + preferred twin #1370

- `src/app_runner.py` path-chmod fallback already removed on `main` via [#1353](https://github.com/abhimehro/email-security-pipeline/pull/1353).
- `setup_wizard.py` still needs fd-only fix; CLEAN sibling [#1370](https://github.com/abhimehro/email-security-pipeline/pull/1370) is the preferred carrier (narrower, no journal conflict).
- Unique residual in #1362 = journal append + stale tests against pre-#1353 API → not worth a salvage branch.

### hg #413 → preferred twin #418

- #413 bundles DoS fix with **numpy regression** (`<3` → `<2`), Bolt validator churn, CHANGELOG/bolt journal (Lesson 0cs risk).
- [#418](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/418) is CLEAN MERGEABLE with DoS-only (`utils/security.py` + tests + sentinel). Prefer #418 for human T1 merge.

## REQUEST_CHANGES

### esp #1366 (Lesson 0er)

Single tip-major bump: `actions/download-artifact` → **v8.0.1** while producers remain `upload-artifact@v7`. Fix: revert download pin to v7 **or** bump upload+download together. Do not squash-merge as-is.

## ESCALATE (human)

| PR | Tier | Why |
|----|------|-----|
| cs #1060 | T1 | Sentinel exception sanitization — security ack |
| Seatek #525/#518/#507 | T1 | Sibling env-filter orderings (0ej) — human picks one |
| hg #418 | T1 | Preferred DoS twin after closing #413 |
| esp #1370 | T1 | Preferred TOCTOU twin after closing #1362 |
| pc #1789/#1787/#1786/#1784 | T1/T2 | Security/trust-boundary — Phase 1 next cycle |
| series #295 | T1 | ABHI-1518 formula injection |

## DEFER / DROP

| PR | Disposition |
|----|-------------|
| Seatek #521 | DROP — merged since Phase 1 |
| ctrld #1066 | DEFER after `/cs-agent skill:fix-code-health-degradations` |
| Cursor repo-health drafts (#535/#422/#297) | DEFER — human draft review |
| Palette/Bolt CLEAN chore | Next Phase 1 |

## CodeScene

| PR | Action |
|----|--------|
| ctrld #1066 | Post `/cs-agent skill:fix-code-health-degradations` before disposition |
