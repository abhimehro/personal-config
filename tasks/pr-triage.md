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
# PR Triage — 2026-07-28 (Phase 1)

## Duplicate / overlap groups

| Group | PRs | Keep | Action |
|-------|-----|------|--------|
| Hydrograph Bolt NumPy scalar | #428, #427, #420 | #428 (superset; #427 byte-identical; #420 subset) | Merged #428; recommend close #427/#420 |
| ctrld Palette partial-success | #1069, #1067, #1066 | #1067 (tests) | Merged #1067; recommend close #1069/#1066 |
| series_correction QA/lint | #299, #293 | #299 (superset) | Merged #299; recommend close #293 |
| personal-config Bolt + bolt.md | #1801, #1800, #1791 | #1801 first | Merged #1801; #1800/#1791 CONFLICTING → DEFER rebase |
| personal-config Sentinel pkill CWE-88 | #1796, #1784 | human pick | ESCALATE both |
| esp Sentinel TOCTOU | #1375, #1370, #1362 | human pick (+ salvage #1362) | ESCALATE |
| Seatek Sentinel env-filter (0ej) | #525, #518, #507 | human pick | ESCALATE |

## Stale (>30d)

None in this inventory (oldest ~6d).

## Capability notes

- Squash-merge works with Cursor hosts.yml token.
- `closePullRequest` / REST issue close / `gh pr comment` GraphQL **denied** → CLOSE dispositions recorded via MCP reviews only; Phase 2 must close.
- `request_reviewers` fails when `abhimehro` is already the PR author (expected).

## Merge order executed

1. Zero-diff QA: cs #1068, esp #1376, Seatek #537, Seatek #533
2. Dependabot patches: cs #1070, cs #1071, esp #1373, sc #294
3. Safe CI/UI/Perf: pc #1798, pc #1795, cs #1067, esp #1372, hg #428, hg #422, sc #299, pc #1801
