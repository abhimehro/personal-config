# PR Triage — 2026-05-24 (combined)

**Disposition key:** MERGE · CLOSE-DUPLICATE · CLOSE-SUPERSEDED · DEFER · ESCALATE · SALVAGE-DRAFT

**Sessions:** Review (13:00) + salvage (17:00). Preflight **passed** both runs.

## Review session (13:00)

| Repo | PR | Disposition |
| --- | ---: | --- |
| personal-config | 1037, 1038, 1040, 1041, 1045, 1046 | **MERGE** |
| personal-config | 1042, 1043, 1044 | **CLOSE-DUPLICATE** |
| personal-config | 1039, 1047 | **ESCALATE** → salvage |
| personal-config | 1036, 1048 | **DEFER** → salvage |
| email-security-pipeline | 901 | **MERGE** |

## Salvage session (17:00)

| Repo | PR | Disposition |
| --- | ---: | --- |
| personal-config | 1049 | **MERGE** (session report artifacts) |
| series_correction | 64 | **MERGE** (CLEAN + green CI) |
| personal-config | 1036 | **CLOSE-SUPERSEDED** → **#1050** draft |
| personal-config | 1048 | **CLOSE-SUPERSEDED** → **#1051** draft |
| personal-config | 1039 | **CLOSE-SUPERSEDED** → **#1052** draft |
| personal-config | 1047 | **CLOSE-DUPLICATE** (#1052 lane) |

## Still open (human merge queue)

| Repo | PR | Tier | Notes |
| --- | ---: | --- | --- |
| personal-config | 1050 | T1 | Security tracker + formula injection |
| personal-config | 1051 | T3 | scratch_triage refactor |
| personal-config | 1052 | T2 | PAT runbook; wire `parse_inventory` separately |
| ctrld-sync | 844 | T3 | Palette UX — not in Phase 1 tail; triage next review |

## Human next steps

1. Review and merge draft salvages **#1050** → **#1052** after CI green (squash).
2. Open a **separate** human-reviewed PR to adopt `gh_token_env` in `parse_inventory.py` / `run_merges.py` (not included in #1052).
3. Triage **ctrld-sync#844** on next review cron if still open.
