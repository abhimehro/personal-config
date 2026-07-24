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
