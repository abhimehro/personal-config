# Automated PR inventory — 2026-03-27 (backlog cleanup, review-and-merge)

**Config:** `tasks/pr-review-agent.config.yaml`  
**Stale threshold:** 30 days (no in-scope PR exceeded this at inventory time)  
**Scope:** Listed repos + **expanded automation** (branch/title/body: `jules/*`, `sentinel-*`, `bolt/*`, `palette/*`, `automation-*`, daily QA, Jules footer), even when GitHub shows `abhimehro` as author.

**Configured bot logins (no open PRs from these at snapshot):** `dependabot[bot]`, `renovate[bot]`, `google-labs-jules[bot]` — inventory dominated by Jules-style branches on the human account.

| Repo                                     | PR # | Visible author | Automation signals            | Category    | CI (rollup) | Conflicts      | changedFiles | Notes                                     |
| ---------------------------------------- | ---: | -------------- | ----------------------------- | ----------- | ----------- | -------------- | -----------: | ----------------------------------------- |
| personal-config                          |  682 | abhimehro      | Jules branch + footer         | SECURITY    | Green       | CLEAN → merged |            3 | Trunk symlink fixed before merge          |
| personal-config                          |  681 | abhimehro      | `chore/jules-daily-*`         | CI/INFRA    | Green       | CONFLICTING    |            2 | Escalated — resolve conflicts             |
| personal-config                          |  678 | abhimehro      | `automation-workflow-*` draft | CI/INFRA    | Green       | CLEAN          |            1 | Escalated — draft workflow trust boundary |
| personal-config                          |  677 | abhimehro      | Sentinel branch               | SECURITY    | Green       | CONFLICTING    |            2 | **Closed** superseded by #682             |
| ctrld-sync                               |  672 | abhimehro      | Sentinel branch               | SECURITY    | Green       | CLEAN → merged |            2 | Preferred over #668                       |
| ctrld-sync                               |  669 | abhimehro      | `automation-workflow-*` draft | CI/INFRA    | Green       | CLEAN          |            2 | Escalated                                 |
| ctrld-sync                               |  668 | abhimehro      | Sentinel branch               | SECURITY    | Green       | CONFLICTING    |            3 | **Closed** superseded by #672             |
| email-security-pipeline                  |  597 | abhimehro      | Sentinel                      | SECURITY    | Green       | CLEAN → merged |            3 | Malware/attachment parsing                |
| email-security-pipeline                  |  596 | abhimehro      | Palette branch                | UI          | Green       | CLEAN → merged |            2 | Screen reader / CLI                       |
| email-security-pipeline                  |  594 | abhimehro      | `automation-workflow-*` draft | CI/INFRA    | Green       | CLEAN          |           14 | Escalated                                 |
| email-security-pipeline                  |  593 | abhimehro      | `daily-qa-review-*`           | CI/INFRA    | Green       | CLEAN          |            0 | **Closed** no-op diff                     |
| email-security-pipeline                  |  592 | abhimehro      | Bolt branch                   | PERFORMANCE | Green       | CLEAN → merged |            2 | Magic-byte fast path                      |
| email-security-pipeline                  |  587 | abhimehro      | fix pre-commit                | CI/INFRA    | Green       | CLEAN → merged |            1 | Valid pre-commit rev                      |
| email-security-pipeline                  |  585 | abhimehro      | Sentinel                      | SECURITY    | Green       | CONFLICTING    |            2 | **Closed** superseded post-#597           |
| Seatek_Analysis                          |  107 | abhimehro      | Bolt                          | PERFORMANCE | Green       | CLEAN → merged |            1 | Vectorized pandas                         |
| Seatek_Analysis                          |  106 | abhimehro      | Sentinel                      | SECURITY    | Green       | CLEAN → merged |            1 | Generic error leakage                     |
| Hydrograph_Versus_Seatek_Sensors_Project |   94 | abhimehro      | Sentinel                      | SECURITY    | Green       | CLEAN → merged |            3 | Shared sanitize_filename                  |
| Hydrograph_Versus_Seatek_Sensors_Project |   93 | abhimehro      | Bolt                          | PERFORMANCE | Green       | CLEAN → merged |            4 | `len(df)` vs `.empty`                     |

**Totals at snapshot:** 18 in-scope open PRs across 5 repos (Seatek + Hydro had none beyond the listed).
