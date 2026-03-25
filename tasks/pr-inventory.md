# Automated PR Inventory — 2026-03-24 (backlog cleanup test)

**Scope:** Repos in `tasks/pr-review-agent.config.yaml`, plus **expanded automation** when author is `abhimehro` but branch/title/body indicate Jules / repository automation / Dependabot-style work.

**Stale threshold:** 30 days (none of the below exceeded it at inventory time).

| Repo                                     | PR # | Visible author | Automation signals            | Category    | CI (summary)                                                         | Conflicts       | Age (approx) | Notes                                            |
| ---------------------------------------- | ---: | -------------- | ----------------------------- | ----------- | -------------------------------------------------------------------- | --------------- | ------------ | ------------------------------------------------ |
| personal-config                          |  675 | abhimehro      | Jules branch + footer         | UI          | UNSTABLE (`update_release_draft` fail — GitHub action tarball fetch) | CLEAN           | ~0.2d        | **Merged** (squash)                              |
| personal-config                          |  669 | abhimehro      | Jules footer                  | CI/INFRA    | Mostly green; CodeScene fail historically                            | **CONFLICTING** | ~1.4d        | Open — conflicts + high trust-boundary           |
| ctrld-sync                               |  663 | abhimehro      | Jules footer                  | CI/INFRA    | `label` fixed; **CodeScene fail**                                    | CLEAN           | ~1.4d        | Open — automation + external gate                |
| email-security-pipeline                  |  584 | abhimehro      | Jules footer                  | UI          | CLEAN                                                                | CLEAN           | ~0.2d        | **Merged**                                       |
| email-security-pipeline                  |  582 | abhimehro      | automation branch/body        | CI/INFRA    | CLEAN (draft)                                                        | CLEAN           | ~0.3d        | Open draft — **escalate** (unsafe proposed pins) |
| email-security-pipeline                  |  579 | abhimehro      | Jules footer                  | SECURITY    | CLEAN                                                                | CLEAN           | ~0.3d        | **Merged** (Bandit B615)                         |
| email-security-pipeline                  |  578 | abhimehro      | Jules footer                  | PERFORMANCE | CLEAN                                                                | CLEAN           | ~0.4d        | **Merged**                                       |
| email-security-pipeline                  |  576 | abhimehro      | Jules footer + security title | SECURITY    | **CodeQL fail**                                                      | CLEAN           | ~0.9d        | Open — **escalate** (TOCTOU / `.env`)            |
| Hydrograph_Versus_Seatek_Sensors_Project |   91 | abhimehro      | Jules footer                  | PERFORMANCE | CLEAN                                                                | CLEAN           | ~0.4d        | **Merged**                                       |
| Hydrograph_Versus_Seatek_Sensors_Project |   89 | abhimehro      | Jules branch + footer         | PERFORMANCE | CLEAN                                                                | CLEAN           | ~1.4d        | **Closed** superseded by #91                     |
| Seatek_Analysis                          |    — | —              | —                             | —           | —                                                                    | —               | —            | No open PRs                                      |

**Bots explicitly configured:** `dependabot[bot]`, `renovate[bot]`, `google-labs-jules[bot]` — none had open PRs in these repos at run time; inventory is dominated by **Jules-style human-account PRs** matching the expanded policy.
