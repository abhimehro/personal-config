# PR Triage — 2026-07-17

## Counts

| Disposition | Count |
|-------------|------:|
| MERGE (squash) | 24 |
| CLOSE | 6 |
| ESCALATE | 5 |
| DEFER | 7 |
| In-scope at start | 41 |
| In-scope open EOD | 12 |

## Overlap groups handled

- pc #1673 ≡ #1674 → merged #1673, closed #1674
- pc #1660 empty-state superseded by #1672 → closed
- Seatek #483 rollmean3 indexing superseded by #478 → closed
- hg #378 merged before #381 CodeScene defer
- sc salvages #239/#240 before Bolt #244

## Security gate notes

- Seatek #472: `subprocess.check_output(..., executable=git_bin)` prevents PATH hijack — merged
- sc #241: OSV floors for filelock/click — merged (draft→ready)
- sc #233: auth implementation — escalated (never auto-merge)
- rpce artifact majors: tip-release breaking changes — escalated
- pc #1670: gemini-review.yml toolchain — escalated
