# PR Triage — 2026-07-22 (Phase 2)

**Policy:** Draft-only salvages; never autonomous merge (S1). Security-classified: `email-security-pipeline`.

## Decision matrix

| Priority | PR | Disposition | Rationale |
|----------|-----|-------------|-----------|
| T3 salvage | pc #1733 → **#1748** | SALVAGE draft | Visual-recap reliability; token sanitize + recap-cli + MDX hardeners |
| T3 salvage | esp #1335 → **#1341** | RE-SALVAGE draft | Prior salvage conflicted; 3-line extend still off main |
| T3 salvage | esp #1330 → **#1342** | SALVAGE adapted | Config-object IMAPClient; adapted past FetchContext (#1311) |
| T2 escalate | pc #1744 | ESCALATE | Floating Action tags (supply-chain / 0eh) |
| T2 escalate | pc #1721 | ESCALATE | Env cache near GH_TOKEN path |
| T1 escalate | esp #1328/#1324/#1319 | ESCALATE | Secrets TOCTOU / Auth-Results / gh_token_cli |
| T1 escalate | sc #275/#276/#268 | ESCALATE | Auth in `dummy_todos.py` (0ef) |
| T1 escalate | Seatek #507/#511 | ESCALATE | Subprocess env / security refactor |
| T2 escalate | rpce #126/#127 | ESCALATE | Artifact tip majors (0dw) |
| Defer | esp #1327 | DEFER | CodeScene red + conflict + workflow churn |
| Defer | esp #1320 | DEFER | Restore assertion (request-changes) |

## Security gates applied

- No merges of salvage drafts
- No force-push
- Journal files: append-only on #1748 (`0ei`/`0ej`); no bolt checkout on ESP salvages
- #1748 intentionally includes `pr-visual-recap.yml` (that PR's purpose — not Lesson 0eh smuggling)
- ESP salvage PRs remain draft (S6)

## Human merge order (suggested)

1. pc [#1748](https://github.com/abhimehro/personal-config/pull/1748) (unblocks visual-recap)
2. esp [#1341](https://github.com/abhimehro/email-security-pipeline/pull/1341) then [#1342](https://github.com/abhimehro/email-security-pipeline/pull/1342)
3. T1 security escalations (esp/sc/Seatek)
4. Tip majors / SHA unpin last
