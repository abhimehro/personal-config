# PR Triage — 2026-08-12

Phase 1 cron. Preflight PASS 7/7. Mode: review-and-merge.

## Disposition summary

| Disposition | Count | Notes |
| ----------- | ----: | ----- |
| MERGE | 7 | #388 #1967 #1467 #658 #655 #1974 #1976 |
| CLOSE | 3 | #652 twin, #653 incomplete, #1966 docs recovered |
| ESCALATE | 10+ | security / majors / CORS mismatch / TOCTOU |
| REQUEST_CHANGES | 2 | Seatek#657 fail-open; rpce#226 scope |
| DEFER / HOLD | 10+ | CodeScene, failing CI, conflicts, 0fm holds |

## Duplicate / overlap groups

| Group | Keep | Close / defer | Reason |
| ----- | ---- | ------------- | ------ |
| Seatek anyNA Bolt | #658 (merged) | #652 closed | Identical hot-path |
| Seatek path hijack | already on main via #649 | #653 closed | Journal-only / changelog churn |
| Docs tasks/* | session branch 90fd | #1966 closed | 0fk recover then close |
| rpce TOCTOU | human pick one | #232/#228 escalate | Contaminated twins |
| rpce a11y | prefer #235 when green | #226 REQUEST_CHANGES | Scope creep |
| series requirements | human after CI | #385/#386 escalate | Same file + majors/fail |

## Security escalations (do not auto-merge)

- personal-config#1907 — CORS title / unrelated files
- ctrld-sync#1156 — TOCTOU plan JSON (+ adversarial: silent write fail; scratch test_json.py)
- Hydro#504 — sanitize filename CONFLICTING
- series#378 — auth timing (dummy_todos) CONFLICTING
- Seatek#657 — REQUEST_CHANGES fail-open OSError→{}
- rpce#232/#228 — TOCTOU + huge unrelated diffs
- Majors: ctrld#1136 mypy2; esp#1444 opencv5; series#386 pandas3; series#385 numpy

## Adversarial multi-model (opus-4.8 + gpt-5.5)

Consensus: all 7 merges sound; escalations correct. Notes:
- #1467 `type is list` nit only
- #657 REQUEST_CHANGES upheld by gpt-5.5; opus found borderline — keep REQUEST_CHANGES (fail-secure)
- #1156 escalate reinforced (silent write failure / scratch `/etc/shadow` test)
