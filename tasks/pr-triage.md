# PR Triage — 2026-07-23 (Phase 2 Salvage)

## SALVAGE (draft opened; original closed)

| Repo | Old → New | Notes |
|------|-----------|-------|
| email-security-pipeline | #1327 → [#1346](https://github.com/abhimehro/email-security-pipeline/pull/1346) | SPF `_evaluate_spf_headers` only; bolt append-only; `/cs-agent` posted |
| email-security-pipeline | #1320 → [#1347](https://github.com/abhimehro/email-security-pipeline/pull/1347) | `validate_subject_length` + restored warning assert (Lesson 0en) |

## CLOSE

| Repo | PR | Reason |
|------|-----|--------|
| email-security-pipeline | 1345 | No-op single blank-line between dataclasses |

## ESCALATE (left open; comments refreshed)

| Repo | PRs | Reason |
|------|-----|--------|
| personal-config | 1721, 1744 | GH_TOKEN/env cache DIRTY; Action SHA unpin |
| email-security-pipeline | 1328, 1324, 1319 | secrets TOCTOU / auth-results / token CLI |
| Seatek_Analysis | 518, 507, 511, 514 | env filter cluster / path-IO / pandas major |
| series_correction… | 285, 276, 275, 268 | dummy_todos auth cluster (0ef) |
| repoprompt-ce | 126, 127 | tip artifact majors (0dw) |

## DEFER (human merge of prior drafts / docs)

| Repo | PRs | Reason |
|------|-----|--------|
| personal-config | 1748, 1749, 1755 | Prior salvages + Phase 1/2 docs drafts |
| email-security-pipeline | 1341, 1342 | Prior Phase 2 salvages still awaiting human |

## Maintainer priority

1. **T3 drafts:** esp #1346 → #1347 → #1341 → #1342; pc #1748  
2. **T1 security:** esp #1328/#1324/#1319; sc cluster; Seatek #518/#507/#511  
3. **T2 trust/deps:** pc #1721/#1744; Seatek #514; rpce #126/#127  
