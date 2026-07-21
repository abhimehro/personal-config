# PR Triage — 2026-07-21

**Preflight:** PASS 7/7 · **Mode:** review-and-merge (squash) · **Start open:** 96

## Duplicate / supersede groups

| Keep | Close | Reason |
|------|-------|--------|
| esp #1333 | #1312 | Identical `_is_ip_safe` short-circuit |
| sc #270 | #267, #259 | Same `run_analysis.py` absolute-path fix |
| sc #271 | #261 | Stronger unused `data_loader` cleanup |
| sc #262 | #260 | Same `detect_outliers_series` split (+ junk file on #260) |
| sc #272 | #266 | Same O(1) year-index loop; #272 extracts helper |
| rpce #133 | #135 | Salvage supersedes Bolt DateFormatter PR |
| pc #1720 | #1725 | Todo-scanner fix without visual-recap `tsx` smuggle |

## Zero-diff closes

- Seatek #501, sc #255, esp #1321

## Escalate (auth / secrets / majors / tip-release)

| PR | Reason |
|----|--------|
| sc #275/#276/#268 | `dummy_todos.py` authenticate/PBKDF2 surface |
| esp #1328 | TOCTOU/chmod config secrets |
| esp #1324 | Auth-Results scoring |
| esp #1319 | `gh_token_cli.py` token writes |
| pc #1721 | `GH_TOKEN.env` cache + workflow rewrite |
| hg #374 | numpy 2.x major |
| rpce #126/#127 | artifact tip majors (Lesson 0dw) |

## Defer

| PR | Reason |
|----|--------|
| pc #1724/#1723 | CodeScene FAIL (`/cs-agent` posted) |
| pc #1717/#1716/#1718/#1726 | Conflicts after sibling merges |
| pc #1706 | DIRTY salvage docs |
| esp #1327 | CodeScene (`/cs-agent` posted) |
| esp #1330/#1311/#1320/#1331/#1314 | Ingestion/parser hotspots or DIRTY |

## Conflict hotspots observed

- `pr-visual-recap.yml` + `test_repository_automation_*.py` (personal-config)
- `email_ingestion.py` / `email_parser.py` / `.jules/bolt.md` (esp)
- `dummy_todos.py` (sc auth cluster)
