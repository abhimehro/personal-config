# Automated PR Inventory — 2026-03-29 (backlog cleanup test)

**Scope:** Repos in `tasks/pr-review-agent.config.yaml`, plus **expanded automation** when author is `abhimehro` but branch/title/body indicate Jules / repository automation / Dependabot-style work.

**Stale threshold:** 30 days (none of the below exceeded it at inventory time).

**CI Architecture:** Repos use **GitHub App reviews** (CodeScene, Gemini Code Assist/LiveReview, GitHub Advanced Security) rather than traditional status checks. The `get_pull_request_status` API returns empty, but automated reviews are operational and visible on GitHub.

| Repo                                     | PR # | Visible author | Automation signals                      | Category    | CI (summary)              | Conflicts  | Age (approx) | Draft? | Notes                                                   |
| ---------------------------------------- | ---: | -------------- | --------------------------------------- | ----------- | ------------------------- | ---------- | ------------ | ------ | ------------------------------------------------------- |
| personal-config                          |  691 | abhimehro      | Jules branch `jules-*`                  | UI          | CodeScene✓ Gemini⚠️       | Clean      | <1d          | No     | Cursor hiding; Gemini: signal handling regression      |
| personal-config                          |  686 | abhimehro      | `automation-workflow-updates-*` branch  | CI/INFRA    | Review pending            | Unknown    | ~2d          | Yes    | Workflow action version bumps (v4→v6, v5→v6, etc)      |
| personal-config                          |  681 | abhimehro      | `chore/jules-daily-qa-*` branch         | REFACTOR    | Review pending            | Unknown    | ~4d          | No     | QA fixes (TOML quotes, shellcheck)                      |
| ctrld-sync                               |  682 | abhimehro      | `security-dos-url-length-*` branch      | SECURITY    | CodeScene✓ Gemini⚠️ GHAS  | Clean      | <1d          | No     | DoS: URL length; Gemini: improve test coverage          |
| ctrld-sync                               |  679 | abhimehro      | `automation-workflow-updates-*` branch  | CI/INFRA    | Review pending            | Unknown    | ~1d          | Yes    | Workflow updates, major bump warning (v4→v6)            |
| ctrld-sync                               |  678 | abhimehro      | `sentinel-fix-dos-*` branch             | SECURITY    | Review pending            | Unknown    | ~2d          | No     | DoS: regex evaluation via unrestricted lengths (MEDIUM) |
| email-security-pipeline                  |  604 | abhimehro      | `bolt/optimize-*` branch                | PERFORMANCE | Review pending            | Unknown    | <1d          | No     | Email header parsing optimization (~44x faster)         |
| email-security-pipeline                  |  600 | abhimehro      | `automation-workflow-updates-*` branch  | CI/INFRA    | Review pending            | Unknown    | ~2d          | Yes    | Workflow action version bumps (v4→v6, v5→v6, v7→v8)     |
| Seatek_Analysis                          |  111 | abhimehro      | `sentinel-fix-pandas-oom-*` branch      | SECURITY    | CodeScene✓ Gemini⚠️ GHAS  | Clean      | <1d          | No     | OOM DoS + CI workflow; Gemini: TOCTOU race condition    |
| Seatek_Analysis                          |  110 | abhimehro      | `bolt-optimize-excel-*` branch          | PERFORMANCE | Review pending            | Unknown    | <1d          | No     | Vectorize column-wise updates                           |
| Seatek_Analysis                          |  109 | abhimehro      | `sentinel-fix-exception-*` branch       | SECURITY    | Review pending            | Unknown    | ~2d          | No     | Exception leakage in automation scripts (MEDIUM)        |
| Seatek_Analysis                          |  108 | abhimehro      | `bolt-performance-*` branch             | PERFORMANCE | Review pending            | Unknown    | ~2d          | No     | Pandas string parsing optimization (~30% faster)        |
| Hydrograph_Versus_Seatek_Sensors_Project |   95 | abhimehro      | `sentinel/file-size-*` branch           | SECURITY    | Review pending            | Unknown    | <1d          | No     | Centralize file size checks (LOW severity)              |

**Bots explicitly configured:** `dependabot[bot]`, `renovate[bot]`, `google-labs-jules[bot]` — none had open PRs in these repos at run time; inventory is dominated by **Jules-style human-account PRs** matching the expanded automation policy.
