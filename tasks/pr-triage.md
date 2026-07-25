# PR Triage — 2026-07-24 (Phase 1)

**Preflight:** PASS 7/7 · **Mode:** review-and-merge · **Inventoried:** 41 in-scope

## MERGE (gates pass)

| PR | Reason |
|----|--------|
| pc #1763 | Regex hoist; CI green; no secrets |
| pc #1758 | Dependabot gh-aw SHA bump; checks green |
| cs #1058/#1057/#1056 | Dependabot action bumps |
| cs #1053 | clear-cache extract; CodeScene-friendly |
| esp #1355 | One blank-line lint fix |
| esp #1354 | Address-format micro-opt; tests green |
| esp #1352/#1351/#1350 | Dependabot bumps |
| esp #1347 | Subject validator reuse + test restore |
| esp #1346 | SPF helper extract (logic preserved) |
| esp #1341 | extend+comprehension collect |
| seatek #520 | ruby/setup-ruby patch |
| seatek #522 | pillow CVE floor (ready then merge) |
| hg #408/#407/#406 | Dependabot lock/workflow bumps |
| sc #288 | Jules QA typing/import hygiene |

## CLOSE

| PR | Reason |
|----|--------|
| cs #1055 | Zero-diff superseded (Lesson 0b) |
| seatek #524 | Zero-diff Jules QA all-clear |

## ESCALATE (human)

| PR | Reason |
|----|--------|
| pc #1744 | SHA→floating tag unpin (Lesson 0z/0eh) |
| pc #1721 | GH_TOKEN/`lru_cache` + CONFLICTING |
| pc #1748 | Toolchain visual-recap salvage (Tier says no auto-merge) |
| esp #1353/#1328 | TOCTOU/chmod secrets surface |
| esp #1324 | Auth-Results scoring trust boundary |
| esp #1319 | `gh_token_cli` token writes |
| esp #1342 | IMAPClient constructor/API change (attachment limits) |
| seatek #525/#518/#507 | Sibling Sentinel env-filter (Lesson 0ej) |
| seatek #521 | pandas major 2→3 (Lesson 0ek) |
| seatek #511 | Devin security refactor + Trunk FAIL |
| sc #285/#276/#275/#268 | `dummy_todos.py` auth/DoS cluster (0ef) |
| rpce #126/#127 | tip-release artifact majors (0dw) |

## DEFER

| PR | Reason |
|----|--------|
| pc #1756 | Draft Phase 2 salvage docs |
| esp #1348 | Draft AGENTS.md note |

## Overlap notes

- ESP `email_parser.py`: #1354 then #1347 (re-check after each merge).
- ESP `email_ingestion.py`: #1355 → #1341; leave #1342 escalated.
- ESP `spam_analyzer.py`: #1346 merge; #1324 stays escalated.
- Seatek `requirements.txt`: #522 (pillow) before any pandas decision on #521.
- bolt.md journal siblings: expect DIRTY journal-only after first merge (0cs).

## Final disposition (executed)

- **MERGED:** 20 (incl. #1346 after autofix)
- **CLOSED:** cs #1055, Seatek #524
- **ESCALATED:** 18 (comments posted)
- **DEFERRED:** pc #1756, esp #1348
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
