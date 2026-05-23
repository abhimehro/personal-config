# PR Triage — 2026-05-23 (combined)

**Disposition key:** MERGE · CLOSE-DUPLICATE · CLOSE-SCOPE-CREEP · DEFER · ESCALATE · SALVAGE-DRAFT

**Sessions:** Review-and-merge (13:00) + salvage cleanup (17:00). Preflight **passed** both runs.

## Review session (13:00) — merged

| Repo | PR | Disposition |
| --- | ---: | --- |
| personal-config | 1026, 1025, 1023 | **MERGE** |
| email-security-pipeline | 896 | **MERGE** |
| email-security-pipeline | 897 | **CLOSE-DUPLICATE** (#896) |
| Hydrograph | 199 | **MERGE** |
| series_correction | 59, 58 | **MERGE** |
| series_correction | 55 | **CLOSE-DUPLICATE** (#58) |
| Seatek_Analysis | 172 | **MERGE** |
| ctrld-sync | 821, 818 | **MERGE** |

## Salvage session (17:00) — merged / closed / new draft

| Repo | PR | Disposition |
| --- | ---: | --- |
| personal-config | 1027 | **MERGE** (session artifacts) |
| Seatek_Analysis | 206 | **MERGE** |
| personal-config | 1019, 1022 | **CLOSE-SUPERSEDED** (#1027) |
| personal-config | 1020, 1021 | **CLOSE-SCOPE-CREEP** |
| personal-config | 985 | **CLOSE-SUPERSEDED** (rebuild needed) |
| Seatek_Analysis | 190–198 | **CLOSE-SUPERSEDED** |
| personal-config | 1028 | **SALVAGE-DRAFT** (salvages #992) |

## Still open (end of day)

| Repo | PR | Disposition | Notes |
| --- | ---: | --- | --- |
| personal-config | 1028 | **SALVAGE-DRAFT** | Human merge when CI green |
| Seatek_Analysis | 204 | **SALVAGE-DRAFT** | #188 perf |
| email-security-pipeline | 894 | **SALVAGE-DRAFT** | CodeScene fail |
| ctrld-sync | 837, 835 | **ESCALATE** | `benchmark` required check |
| ctrld-sync | 815, 789 | **DEFER** | CONFLICT / mypy |
| email-security-pipeline | 807, 823, 841, 842, 844 | **DEFER** | CONFLICT or CodeScene |

## Duplicate / overlap groups

| Group | Keep | Close / defer others |
| --- | --- | --- |
| ESP monotonic uptime | #896 | #897 closed |
| Series exception leakage | #58 | #55 closed |
| Session docs | #1027 merged | #1019, #1022 closed |
| ctrld benchmark lane | — | #837 + #835 blocked until `main` benchmark fixed |

## Human next steps

1. Fix **ctrld-sync** `benchmark` on `main`, then merge **#837** / **#835**.
2. Human-merge salvage drafts **#1028**, **#204**, **#894** after review.
3. v2-rebuild ESP DIRTY PRs (#807, #823, #841) from `/tmp` clones per Lesson **0gg**.
