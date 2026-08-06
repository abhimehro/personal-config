# PR Inventory — 2026-08-06

Phase 1 cron (`0 13 * * *`). Preflight PASS 7/7. Auth: `abhimehro` PAT
(squash-merge + close + comment OK; cannot self-request review).
Scope: automation-driven open PRs (bot authors + human-authored
Bolt/Jules/Sentinel/Palette/Cursor-docs/Dependabot/salvage).

Initial inventory: **56** open total → **45** in-scope automation (+11 ordinary
human skipped at discovery; several Jules-style test branches later included).

| Repo | PR | Author signal | Category | CI | Conflicts | Age | Disposition |
| ---- | -- | ------------- | -------- | -- | --------- | --- | ----------- |
| personal-config | 1928 | chore/actions | CI/INFRA | PASS | MERGEABLE | 0 | **MERGED** |
| personal-config | 1925 | cursor docs | CI/INFRA | PASS | MERGEABLE | 0 | DEFER (docs; superseded by this report) |
| personal-config | 1924 | Bolt | FEATURE | PASS | MERGEABLE | 1 | REQUEST_CHANGES (silent yaml) |
| personal-config | 1914 | cursor salvage docs | CI/INFRA | FAIL | MERGEABLE | 1 | DEFER (Trunk MQ fail) |
| personal-config | 1912 | cursor docs | CI/INFRA | PASS | MERGEABLE | 1 | DEFER (docs) |
| personal-config | 1909 | Jules test | FEATURE | PASS | MERGEABLE | 1 | **MERGED** |
| personal-config | 1907 | Sentinel CORS | SECURITY | PASS | MERGEABLE | 2 | ESCALATE |
| personal-config | 1904 | Code Health | REFACTOR | PASS | MERGEABLE | — | DEFER Phase 2 |
| personal-config | 1903 | Code Health | REFACTOR | PASS | MERGEABLE | — | DEFER Phase 2 |
| personal-config | 1902 | Jules test | FEATURE | PASS | MERGEABLE | — | REQUEST_CHANGES (0fg artifacts) |
| ctrld-sync | 1122 | Bolt | PERFORMANCE | PASS | MERGEABLE | 0 | **MERGED** |
| ctrld-sync | 1121 | Palette | FEATURE | PASS | MERGEABLE | 0 | **MERGED** |
| email-security-pipeline | 1433 | chore/actions | CI/INFRA | PASS | MERGEABLE | 0 | **MERGED** |
| email-security-pipeline | 1432 | security fix | SECURITY | PASS | MERGEABLE | 0 | ESCALATE |
| email-security-pipeline | 1431 | security fix | SECURITY | PASS | MERGEABLE | 0 | ESCALATE |
| email-security-pipeline | 1423 | Palette | FEATURE | PASS | MERGEABLE | 1 | **MERGED** (after autofix) |
| email-security-pipeline | 1421 | Bolt alerts | DEPENDENCY | PASS | MERGEABLE | 2 | ESCALATE (0fh) |
| email-security-pipeline | 1409 | Bolt | PERFORMANCE | PASS | CONFLICTING | 3 | DEFER Phase 2 |
| Seatek_Analysis | 613 | Bolt | PERFORMANCE | PASS | MERGEABLE | 0 | **MERGED** |
| Seatek_Analysis | 612–573 | Sentinel cluster | SECURITY | PASS | MERGEABLE | 0–5 | ESCALATE |
| Seatek_Analysis | 601/599/598/595 | Jules “tests” | FEATURE | PASS | MIXED | — | REQUEST_CHANGES (0ff) |
| Seatek_Analysis | 596 | Jules tests | FEATURE | PASS | MERGEABLE | — | **MERGED** |
| Hydrograph… | 476 | Dependabot | DEPENDENCY | PASS | MERGEABLE | 0 | **MERGED** |
| Hydrograph… | 478–459 | Sentinel sanitize | SECURITY | PASS | MERGEABLE | 0–2 | ESCALATE |
| series_correction… | 368 | Dependabot | DEPENDENCY | PASS | MERGEABLE | 0 | **MERGED** |
| series_correction… | 365 | Sentinel auth | SECURITY | PASS | MERGEABLE | 0 | ESCALATE |
| series_correction… | 364 | Sentinel PBKDF2 | SECURITY | FAIL CS | CONFLICTING | 1 | ESCALATE + CS trigger |
| series_correction… | 360 | salvage tests | FEATURE | PASS | CONFLICTING | 1 | DEFER Phase 2 |
| repoprompt-ce | 204 | Bolt DateFormatter | PERFORMANCE | PASS | MERGEABLE | 0 | **MERGED** |
| repoprompt-ce | 200 | Bolt twin | PERFORMANCE | PASS | CONFLICTING | 1 | **CLOSED** (superseded #204) |
| repoprompt-ce | 199 | Bolt keys.contains | PERFORMANCE | PASS | MERGEABLE | 1 | **MERGED** |
| repoprompt-ce | 198 | Palette a11y | FEATURE | PASS | MERGEABLE | 1 | **MERGED** |
| repoprompt-ce | 195 | salvage | PERFORMANCE | PASS | CONFLICTING* | 1 | HOLD salvage |
| repoprompt-ce | 192 | Sentinel Keychain | SECURITY | PASS | MERGEABLE | 2 | **CLOSED** (0fc + mass deletes) |
| repoprompt-ce | 203/201/196/194/186 | mixed | mixed | FAIL | MIXED | — | REQUEST_CHANGES / ESCALATE |
| repoprompt-ce | 193/187/184 | security/tests | mixed | MIXED | MIXED | — | DEFER / ESCALATE |

\* #195 became CONFLICTING after #204 landed.

**Post-session open (approx):** **42** (pc8 / cs0 / esp4 / Seatek12 / hg6 / sc3 / rpce9).
