# PR Triage — 2026-08-11

## Merge queue (this pass)

| Repo | PR | Disposition | Rationale |
| ---- | -- | ----------- | --------- |
| ctrld-sync | 1153 | MERGE | Dependabot gh-aw/actions/setup pin; CI green |
| ctrld-sync | 1154 | MERGE | Dependabot gh-aw pin; CI green |
| ctrld-sync | 1135 | MERGE | ruff 0.16.1 (sole uv.lock this pass; 0fb) |
| ctrld-sync | 1150 | MERGE | Palette pluralize dry-run errors + complexity extract |
| ctrld-sync | 1157 | MERGE | Bolt hostname fast-path (keeps `%` / empty guards) |
| ctrld-sync | 1151 | MERGE | Bolt rate-limit parse + tests |
| email-security-pipeline | 1461 | MERGE | Palette fixed-width spinner timer |
| email-security-pipeline | 1463 | MERGE | Bolt attachment Content-Disposition early return |
| email-security-pipeline | 1464 | MERGE | Jules flake8 blanks + dedupe duplicate timeout tests |
| Seatek_Analysis | 641 | MERGE | Bolt mad() median precompute (clearest twin) |
| Seatek_Analysis | 648 | CLOSE | Zero-diff Jules Daily QA |
| personal-config | 1955 | MERGE | Palette empty-state polish |
| personal-config | 1959 | MERGE | Palette meter visualization |
| personal-config | 1962 | MERGE | Palette insights empty-state fallback |
| personal-config | 1964 | MERGE | Bolt GraphQL parse micro-opt |
| personal-config | 1958 | MERGE | Bolt list-comprehension sections |
| repoprompt-ce | 230 | MERGE | Palette a11y labels |
| repoprompt-ce | 231 | MERGE | Bolt DateFormatter cache |
| series_correction | 381 | MERGE | Repo-health: remove root junk + PR templates (undraft) |
| series_correction | 379 | MERGE | Lazy log.exception (ready salvage, trivial) |

## Close as duplicate / superseded

| Repo | PR | Keep | Reason |
| ---- | -- | ---- | ------ |
| ctrld-sync | 1155 | 1157 | Narrower hostname fast-path twin |
| Seatek_Analysis | 650 | 641 | mad() twin (assignment-in-expr) |
| Seatek_Analysis | 637 | 641 | mad() twin (older) |
| personal-config | 1953 | recovered | Docs cascade → this branch (0fk) |
| personal-config | 1954 | recovered | Docs cascade → this branch (0fk) |
| personal-config | 1960 | recovered | Docs cascade → this branch (0fk) |

## Escalate (security / major / failing)

| Repo | PR | Reason |
| ---- | -- | ------ |
| personal-config | 1907 | CORS trust boundary |
| Seatek_Analysis | 649 (head) + cluster | Path-hijack Sentinels |
| Hydrograph | 502 (head) + cluster | sanitize_filename Sentinels |
| series_correction | 378/365/364 | Auth timing / PBKDF2 |
| series_correction | 375 | Salvage draft (human) |
| ctrld-sync | 1136 | mypy 2.x major |
| ctrld-sync | 1156 / 1147 | TOCTOU / secrets.random |
| email-security-pipeline | 1444 | opencv 5.x + failing pytest |
| email-security-pipeline | 1421 | CONFLICTING aiohttp Bolt |
| email-security-pipeline | 1458 | Private `msg._headers` API |
| repoprompt-ce | 228/223/217/214/210/201/196 | TOCTOU cluster |
| repoprompt-ce | 227/224/218 | Salvage drafts |
| Seatek_Analysis | 643 | Repo-health draft + failing CodeQL |
| Hydrograph | 498 | Repo-health draft + CodeScene fail → trigger |

## Sentinel duplicate close policy

Keep newest MERGEABLE green head escalated; close older siblings as CLOSE-DUPLICATE with link to head.
