# PR Triage — 2026-07-22

## Duplicate / overlap groups

| Group | Keep | Close | Reason |
|-------|------|-------|--------|
| ctrld Bolt inline validation | #1050 | #1051 | Same `main.py` + `.jules/bolt.md`; near-identical intent |
| sc dummy_todos auth/DoS cohort | — | — | #268/#275/#276 all escalate (Lesson 0ef); #275 DIRTY |

## Disposition plan

### MERGE (squash) — safe deps / QA / salvage / perf

- **Deps:** ctrld #1047,#1048; esp #1337,#1338; hg #398; sc #283; Seatek #504,#510
- **Zero-diff QA:** pc #1741; sc #282; Seatek #506
- **Docs/salvage/tests:** pc #1737,#1734,#1735,#1736,#1740; Seatek #509
- **Perf/refactor (non-security):** pc #1724,#1746; ctrld #1049,#1050; esp #1334,#1335,#1339,#1340; Seatek #512
- **Hardening (reviewed):** hg #400 (logger path sanitize via existing helpers); pc #1733 (visual-recap/gitleaks hardeners, CI green)

### CLOSE

- ctrld #1051 — duplicate of #1050

### ESCALATE

| PR | Reason |
|----|--------|
| sc #268/#275/#276 | `dummy_todos.py` auth/DoS (Lesson 0ef) |
| esp #1324 | Auth-Results scoring behavior change |
| esp #1319 | `gh_token_cli` token export surface |
| pc #1721 | CONFLICTING + env-cache near GH_TOKEN |
| pc #1744 | Unpins Actions SHAs → floating tags (supply-chain regression) |
| Seatek #507 | Subprocess env filter order (trust boundary) |
| Seatek #511 | Security-titled path/IO refactor across analysis + automation |
| rpce #126/#127 | Artifact action tip majors (Lesson 0dw) |

### DEFER

| PR | Reason |
|----|--------|
| esp #1327 | CodeScene failing (`/cs-agent` if not already posted) |
| pc #1742/#1743 | Gate CANCELLED — re-run then reassess |

## Merge order (within repo)

deps → zero-diff → tests/docs → perf → shared refactors; re-check mergeable after each merge.
