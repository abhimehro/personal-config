# PR Inventory — 2026-08-06

> **Phase 2 update (17:00 UTC):** CONFLICTING salvages re-rolled; see `pr-triage.md` / `salvage-session-reports.md`.

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
| personal-config | 1904 | Code Health | REFACTOR | — | CONFLICTING | — | **CLOSED** (0fc scope collapse) |
| personal-config | 1903 | Code Health | REFACTOR | PASS | MERGEABLE | — | DEFER Phase 2 |
| personal-config | 1902 | Jules test | FEATURE | PASS | MERGEABLE | — | REQUEST_CHANGES (0fg artifacts) |
| ctrld-sync | 1122 | Bolt | PERFORMANCE | PASS | MERGEABLE | 0 | **MERGED** |
| ctrld-sync | 1121 | Palette | FEATURE | PASS | MERGEABLE | 0 | **MERGED** |
| email-security-pipeline | 1433 | chore/actions | CI/INFRA | PASS | MERGEABLE | 0 | **MERGED** |
| email-security-pipeline | 1432 | security fix | SECURITY | PASS | MERGEABLE | 0 | ESCALATE |
| email-security-pipeline | 1431 | security fix | SECURITY | PASS | MERGEABLE | 0 | ESCALATE |
| email-security-pipeline | 1423 | Palette | FEATURE | PASS | MERGEABLE | 1 | **MERGED** (after autofix) |
| email-security-pipeline | 1421 | Bolt alerts | DEPENDENCY | PASS | MERGEABLE | 2 | ESCALATE (0fh) |
| email-security-pipeline | 1409 | Bolt | PERFORMANCE | — | CONFLICTING | 3 | **CLOSED** → salvage [#1437](https://github.com/abhimehro/email-security-pipeline/pull/1437) |
| Seatek_Analysis | 613 | Bolt | PERFORMANCE | PASS | MERGEABLE | 0 | **MERGED** |
| Seatek_Analysis | 612–573 | Sentinel cluster | SECURITY | PASS | MERGEABLE | 0–5 | ESCALATE |
| Seatek_Analysis | 601/599/598/595 | Jules “tests” | FEATURE | — | CONFLICTING | — | **CLOSED** (0ff) |
| Seatek_Analysis | 596 | Jules tests | FEATURE | PASS | MERGEABLE | — | **MERGED** |
| Hydrograph… | 476 | Dependabot | DEPENDENCY | PASS | MERGEABLE | 0 | **MERGED** |
| Hydrograph… | 478–459 | Sentinel sanitize | SECURITY | PASS | MERGEABLE | 0–2 | ESCALATE |
| series_correction… | 368 | Dependabot | DEPENDENCY | PASS | MERGEABLE | 0 | **MERGED** |
| series_correction… | 365 | Sentinel auth | SECURITY | PASS | MERGEABLE | 0 | ESCALATE |
| series_correction… | 364 | Sentinel PBKDF2 | SECURITY | FAIL CS | CONFLICTING | 1 | ESCALATE + CS trigger |
| series_correction… | 360 | salvage tests | FEATURE | — | CONFLICTING | 1 | **CLOSED** → salvage [#369](https://github.com/abhimehro/series_correction_project_updated/pull/369) |
| repoprompt-ce | 204 | Bolt DateFormatter | PERFORMANCE | PASS | MERGEABLE | 0 | **MERGED** |
| repoprompt-ce | 200 | Bolt twin | PERFORMANCE | PASS | CONFLICTING | 1 | **CLOSED** (superseded #204) |
| repoprompt-ce | 199 | Bolt keys.contains | PERFORMANCE | PASS | MERGEABLE | 1 | **MERGED** |
| repoprompt-ce | 198 | Palette a11y | FEATURE | PASS | MERGEABLE | 1 | **MERGED** |
| repoprompt-ce | 195 | salvage | PERFORMANCE | — | CONFLICTING | 1 | **CLOSED** → salvage [#206](https://github.com/abhimehro/repoprompt-ce/pull/206) |
| repoprompt-ce | 192 | Sentinel Keychain | SECURITY | PASS | MERGEABLE | 2 | **CLOSED** (0fc + mass deletes) |
| repoprompt-ce | 203/201/196/194/186 | mixed | mixed | FAIL | MIXED | — | REQUEST_CHANGES / ESCALATE |
| repoprompt-ce | 193/187/184 | security/tests | mixed | MIXED | MIXED | — | DEFER / ESCALATE |

\* #195 became CONFLICTING after #204 landed.

| series_correction… | 369 | salvage draft | FEATURE | — | MERGEABLE | 0 | **DRAFT** (S1) re-salvage #360 |
| email-security-pipeline | 1437 | salvage draft | PERFORMANCE | — | MERGEABLE | 0 | **DRAFT** (S1) from #1409 |
| repoprompt-ce | 206 | salvage draft | PERFORMANCE | — | MERGEABLE | 0 | **DRAFT** (S1) from #195 |
| repoprompt-ce | 207 | salvage draft | SECURITY | — | MERGEABLE | 0 | **DRAFT** (S1) from #193 |
| repoprompt-ce | 193 | security/stderr | SECURITY | — | CONFLICTING | — | **CLOSED** → salvage #207 |

**Post-Phase-2 open (approx):** ~35 (security clusters + CI-red + docs; 4 new salvage drafts awaiting human).
