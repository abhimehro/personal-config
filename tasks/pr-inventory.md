# Automated PR inventory — 2026-05-02 (preflight + discovery, Work Item 1)

**Oracle plan:** `prompt-exports/oracle-plan-2026-05-02-032943-automated-pr-cleanup-6f3e.md`  
**Config:** `tasks/pr-review-agent.config.yaml`  
**Stale threshold:** 30 days (max observed age among in-scope PRs: **4** days at snapshot time).  
**Mode:** `review-and-merge` · **Merge strategy:** squash · **Auto-fix:** enabled (inventory-only run — **no** merges/closes/comments/pushes).

## Preflight

- **Command:** `bash scripts/preflight-gh-pr-automation.sh --config tasks/pr-review-agent.config.yaml` (run from `personal-config/`).
- **Result:** **PASS (exit 0)** — `gh` authenticated; read-only checks succeeded for all **five** configured repos (`abhimehro/personal-config`, `abhimehro/ctrld-sync`, `abhimehro/email-security-pipeline`, `abhimehro/Seatek_Analysis`, `abhimehro/Hydrograph_Versus_Seatek_Sensors_Project`).
- **Warnings:** `viewerCanEnableAutoMerge=false` on probe PRs (expected per checklist); `abhimehro/Hydrograph_Versus_Seatek_Sensors_Project#158` had at least one failing check in preflight output (CodeScene).

## Discovery scope & methodology

1. **Local workspace mapping:** Enumerate `github.com` `origin` URLs from git worktrees under `/Users/speedybee/dev`, excluding `personal-config/.cursor/plugins/cache/**` (vendor plugin clones).
2. **GitHub query:** For each unique `owner/repo`, `gh pr list --state open` (limit 500) with JSON fields including `statusCheckRollup`, `mergeable`, `mergeStateStatus`, `changedFiles`.
3. **In-scope PRs:** Configured bot authors (`dependabot`, `renovate`, `google-labs-jules`, GitHub `Bot` type, `app/dependabot`) **or** human-authored PRs matching automation signals on branch/title/body (Jules / Sentinel / Bolt / Palette / `automation-workflow-*` / `daily-qa` / `qa-test-fix` / `agentic-daily` / Dependabot-Renovate branch prefixes / Jules footer patterns — aligned with `docs/automated-pr-review-agent.md`).
4. **Not scanned:** GitHub repositories with **no** clone under `/Users/speedybee/dev` were **not** queried (discovery gap).

### Repositories touched by this discovery pass

| GitHub slug                                          | Local path (representative)                                     | Open PRs (total) | In-scope PRs | Root `AGENTS.md`                                                   |
| ---------------------------------------------------- | --------------------------------------------------------------- | ---------------- | ------------ | ------------------------------------------------------------------ |
| `1Password/agent-hooks`                              | `/Users/speedybee/dev/agent-hooks`                              | 0                | 0            | No                                                                 |
| `abhimehro/Hydrograph_Versus_Seatek_Sensors_Project` | `/Users/speedybee/dev/Hydrograph_Versus_Seatek_Sensors_Project` | 6                | 6            | Yes — pytest; **`MPLBACKEND=Agg`** for headless matplotlib         |
| `abhimehro/Seatek_Analysis`                          | `/Users/speedybee/dev/Seatek_Analysis`                          | 1                | 1            | Yes — R + optional Python Series 27                                |
| `abhimehro/abhimehro`                                | `/Users/speedybee/dev/abhimehro`                                | 0                | 0            | No                                                                 |
| `abhimehro/agent-governance-toolkit`                 | `/Users/speedybee/dev/agent-governance-toolkit`                 | 0                | 0            | No repo-root file; package-level `packages/*/AGENTS.md` exists     |
| `abhimehro/ctrld-sync`                               | `/Users/speedybee/dev/ctrld-sync`                               | 10               | 10           | Yes — Python ≥3.13, **uv** workflow                                |
| `abhimehro/email-security-pipeline`                  | `/Users/speedybee/dev/email-security-pipeline`                  | 13               | 12           | Yes — pytest / pipeline overview; notes `.Jules` paths & CI quirks |
| `abhimehro/github-readme-stats`                      | `/Users/speedybee/dev/github-readme-stats`                      | 0                | 0            | No                                                                 |
| `abhimehro/personal-config`                          | `/Users/speedybee/dev/personal-config`                          | 13               | 13           | Yes — macOS IaC / maintenance; documents PR automation preflight   |
| `abhimehro/series_correction_project_updated`        | `/Users/speedybee/dev/series_correction_project_updated`        | 0                | 0            | No repo-root file checked                                          |

### Bots observed this run

- **Present:** `app/dependabot` (Seatek `#158`).
- **Absent (open PRs):** `renovate[bot]`, `google-labs-jules[bot]` — none in this snapshot.

### Open PRs excluded from automation inventory

| Repo                                |  PR | Author      | Rationale                                                                                                                                                     |
| ----------------------------------- | --: | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `abhimehro/email-security-pipeline` | 744 | `abhimehro` | Human-authored CI/requirements tweak (`fix-ci-pypi-submit`); **no** configured bot author and **no** automation signal matched on branch/title/body heuristic |

## Complete inventory — open, in-scope automated PRs (2026-05-02)

**Counts:** **5** repos with ≥1 in-scope open PR · **42** total in-scope open PRs.

| Repo                                                 |  PR | Author           | Kind       | Category    | CI rollup | Merge / GraphQL state | Changed files | Age (days) | Draft | Branch (trunc.)                                    | Title (trunc.)                                                                              |
| ---------------------------------------------------- | --: | ---------------- | ---------- | ----------- | --------- | --------------------- | ------------- | ---------- | :---: | -------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| `abhimehro/Hydrograph_Versus_Seatek_Sensors_Project` | 158 | `abhimehro`      | human/auto | PERFORMANCE | FAIL      | MERGEABLE/UNSTABLE    | 2             | 0          |  no   | `bolt-opt-isna-8719666183657859910`                | ⚡ Bolt: Replace df[cols].isna().sum() with numpy comprehension                             |
| `abhimehro/Hydrograph_Versus_Seatek_Sensors_Project` | 157 | `abhimehro`      | human/auto | SECURITY    | PASS      | MERGEABLE/CLEAN       | 2             | 1          |  no   | `sentinel-fix-path-traversal-utils-18332920613588` | 🛡️ Sentinel: [CRITICAL/HIGH] Fix Path Traversal in utils/utils.py                           |
| `abhimehro/Hydrograph_Versus_Seatek_Sensors_Project` | 155 | `abhimehro`      | human/auto | PERFORMANCE | PASS      | MERGEABLE/CLEAN       | 2             | 1          |  no   | `bolt-opt-isna-sum-3375765566006695095`            | ⚡ Bolt: Replace df.isna().sum() with optimized np.count_nonzero()                          |
| `abhimehro/Hydrograph_Versus_Seatek_Sensors_Project` | 153 | `abhimehro`      | human/auto | PERFORMANCE | FAIL      | MERGEABLE/UNSTABLE    | 2             | 2          |  no   | `jules-10090903130018463697-c65a2edd`              | ⚡ Bolt: Replace isna().sum() with np.count_nonzero() for missing value check               |
| `abhimehro/Hydrograph_Versus_Seatek_Sensors_Project` | 152 | `abhimehro`      | human/auto | PERFORMANCE | PENDING   | MERGEABLE/UNSTABLE    | 1             | 3          |  no   | `bolt/optimize-isna-sum-12864490219293111249`      | ⚡ Bolt: [performance improvement] Replace DataFrame.isna().sum() with numpy equivalent     |
| `abhimehro/Hydrograph_Versus_Seatek_Sensors_Project` | 150 | `abhimehro`      | human/auto | PERFORMANCE | FAIL      | MERGEABLE/UNSTABLE    | 3             | 4          |  no   | `bolt/optimize-isna-sum-1141413150808634999`       | ⚡ Bolt: Optimize isna().sum() with np.count_nonzero                                        |
| `abhimehro/Seatek_Analysis`                          | 158 | `app/dependabot` | bot        | DEPENDENCY  | PASS      | MERGEABLE/CLEAN       | 1             | 4          |  no   | `dependabot/pip/Series_27/Analysis/pandas-gte-3.0` | chore(deps): update pandas requirement from <3.0.0,>=1.3.0 to >=3.0.2,<4.0.0 in /Series...  |
| `abhimehro/ctrld-sync`                               | 754 | `abhimehro`      | human/auto | SECURITY    | PASS      | MERGEABLE/CLEAN       | 6             | 0          |  no   | `sentinel/ssrf-reserved-ip-16368152822398913356`   | 🛡️ Sentinel: [MEDIUM] Enhance SSRF protection with is_reserved check                        |
| `abhimehro/ctrld-sync`                               | 753 | `abhimehro`      | human/auto | REFACTOR    | PASS      | MERGEABLE/CLEAN       | 0             | 0          |  no   | `chore/agentic-daily-qa-4479220883537790495`       | Daily QA Review                                                                             |
| `abhimehro/ctrld-sync`                               | 752 | `abhimehro`      | human/auto | SECURITY    | PASS      | MERGEABLE/CLEAN       | 3             | 1          |  no   | `fix/ssrf-reserved-ips-5739476314702205508`        | 🛡️ Sentinel: [CRITICAL] Fix missing is_reserved check in IP validation                      |
| `abhimehro/ctrld-sync`                               | 751 | `abhimehro`      | human/auto | UI          | PASS      | MERGEABLE/CLEAN       | 6             | 1          |  no   | `fix-fail-secure-prompt-4334687339048220442`       | 🎨 Palette: [Fail-Secure Interactive Prompts]                                               |
| `abhimehro/ctrld-sync`                               | 750 | `abhimehro`      | human/auto | REFACTOR    | PASS      | MERGEABLE/CLEAN       | 0             | 1          |  no   | `jules/daily-qa-review-8184650905541453546`        | chore(review): perform automated daily QA review                                            |
| `abhimehro/ctrld-sync`                               | 749 | `abhimehro`      | human/auto | SECURITY    | PASS      | MERGEABLE/CLEAN       | 6             | 2          |  no   | `sentinel-fix-ssrf-reserved-14920069606908911596`  | 🛡️ Sentinel: [HIGH] Fix SSRF vulnerability allowing reserved IPs                            |
| `abhimehro/ctrld-sync`                               | 748 | `abhimehro`      | human/auto | UI          | PASS      | MERGEABLE/CLEAN       | 2             | 2          |  no   | `feat/fail-secure-prompt-14101524465850462056`     | 🎨 Palette: Fail-secure interactive restart prompt                                          |
| `abhimehro/ctrld-sync`                               | 747 | `abhimehro`      | human/auto | UI          | PASS      | MERGEABLE/CLEAN       | 3             | 2          |  no   | `palette-fail-secure-prompt-15874263225612823483`  | 🎨 Palette: Make live sync confirmation fail-secure                                         |
| `abhimehro/ctrld-sync`                               | 746 | `abhimehro`      | human/auto | SECURITY    | PASS      | MERGEABLE/CLEAN       | 2             | 3          |  no   | `fix-ssrf-reserved-ips-11037329883217029781`       | 🛡️ Sentinel: [CRITICAL] Fix SSRF bypass via reserved IPs                                    |
| `abhimehro/ctrld-sync`                               | 745 | `abhimehro`      | human/auto | SECURITY    | PASS      | MERGEABLE/CLEAN       | 2             | 4          |  no   | `sentinel-reserved-ip-check-9805045520235748988`   | 🛡️ Sentinel: [MEDIUM] Add explicit reserved IP check for defense-in-depth                   |
| `abhimehro/email-security-pipeline`                  | 749 | `abhimehro`      | human/auto | REFACTOR    | PASS      | MERGEABLE/CLEAN       | 1             | 0          |  no   | `fix-mock-os-open`                                 | 🧪 Jules Daily QA: Fix test_setup_wizard mock_os_open assertion                             |
| `abhimehro/email-security-pipeline`                  | 748 | `abhimehro`      | human/auto | PERFORMANCE | FAIL      | MERGEABLE/UNSTABLE    | 1             | 0          |  no   | `jules-13252476722681144672-ccbfb3c9`              | ⚡ Bolt: Faster Video Frame Extraction using Hybrid Seeking                                 |
| `abhimehro/email-security-pipeline`                  | 747 | `abhimehro`      | human/auto | UI          | FAIL      | MERGEABLE/UNSTABLE    | 3             | 1          |  no   | `jules-ux-alert-urls-13894108668622717022`         | 🎨 Palette: Add missing suspicious URLs display to CLI alerts                               |
| `abhimehro/email-security-pipeline`                  | 746 | `abhimehro`      | human/auto | UI          | FAIL      | MERGEABLE/UNSTABLE    | 4             | 1          |  no   | `jules-ux-alert-urls`                              | 🎨 Palette: Add missing suspicious URLs display to CLI alerts                               |
| `abhimehro/email-security-pipeline`                  | 743 | `abhimehro`      | human/auto | REFACTOR    | PASS      | MERGEABLE/CLEAN       | 2             | 1          |  no   | `daily-qa-test-fix-12538072907331502444`           | 🧪 Fix broken mock assertion in test_setup_wizard.py                                        |
| `abhimehro/email-security-pipeline`                  | 742 | `abhimehro`      | human/auto | REFACTOR    | PASS      | MERGEABLE/CLEAN       | 1             | 1          |  no   | `daily-qa-test-fix`                                | 🧪 Fix broken mock assertion in test_setup_wizard.py                                        |
| `abhimehro/email-security-pipeline`                  | 740 | `abhimehro`      | human/auto | PERFORMANCE | FAIL      | MERGEABLE/UNSTABLE    | 1             | 1          |  no   | `jules-5855862047043928786-4a59fdd2`               | ⚡ Bolt: Faster Video Frame Extraction using Hybrid Seeking                                 |
| `abhimehro/email-security-pipeline`                  | 738 | `abhimehro`      | human/auto | REFACTOR    | PASS      | MERGEABLE/CLEAN       | 2             | 3          |  no   | `qa-test-fix-10605119333253188855`                 | Fix test_gmail_setup in test_setup_wizard                                                   |
| `abhimehro/email-security-pipeline`                  | 736 | `abhimehro`      | human/auto | REFACTOR    | PASS      | MERGEABLE/CLEAN       | 2             | 3          |  no   | `qa-test-fix`                                      | Fix failing test_gmail_setup in test_setup_wizard                                           |
| `abhimehro/email-security-pipeline`                  | 733 | `abhimehro`      | human/auto | REFACTOR    | PASS      | MERGEABLE/CLEAN       | 1             | 4          |  no   | `jules-11238207734226695274-1d3e88a6`              | 🧪 Jules Daily QA: Fix test_setup_wizard mock_os_open assertion                             |
| `abhimehro/email-security-pipeline`                  | 732 | `abhimehro`      | human/auto | PERFORMANCE | PASS      | MERGEABLE/CLEAN       | 3             | 4          |  no   | `bolt-optimize-video-frames-6579687739101256832`   | ⚡ Bolt: Optimize video frame extraction                                                    |
| `abhimehro/email-security-pipeline`                  | 731 | `abhimehro`      | human/auto | PERFORMANCE | PASS      | MERGEABLE/CLEAN       | 3             | 4          |  no   | `bolt-optimize-video-frames`                       | ⚡ Bolt: Optimize video frame extraction                                                    |
| `abhimehro/personal-config`                          | 850 | `abhimehro`      | human/auto | SECURITY    | PASS      | MERGEABLE/CLEAN       | 6             | 0          |  no   | `sentinel/cwe-88-pgrep-pkill-15385015620828813629` | 🛡️ Sentinel: [HIGH] Fix Option Injection (CWE-88) in pkill/pgrep commands                   |
| `abhimehro/personal-config`                          | 849 | `abhimehro`      | human/auto | UI          | PASS      | MERGEABLE/CLEAN       | 5             | 0          |  no   | `palette/forgiving-prompts-1378767764350069806`    | 🎨 Palette: Make boolean CLI prompts forgiving and accept full words                        |
| `abhimehro/personal-config`                          | 840 | `abhimehro`      | human/auto | REFACTOR    | PASS      | MERGEABLE/CLEAN       | 2             | 0          |  no   | `jules-2997359839851386733-b0d71036`               | Daily QA Review: Fully healthy                                                              |
| `abhimehro/personal-config`                          | 839 | `abhimehro`      | human/auto | PERFORMANCE | PASS      | MERGEABLE/CLEAN       | 5             | 0          |  no   | `bolt-optimize-dict-type-checks-10108508667923855` | ⚡ Bolt: [performance improvement] Optimize dict type checks and memory efficiency in li... |
| `abhimehro/personal-config`                          | 838 | `abhimehro`      | human/auto | SECURITY    | PASS      | CONFLICTING/DIRTY     | 870           | 1          |  no   | `fix/command-injection-eval-15887945871828822805`  | 🛡️ Sentinel: [CRITICAL] Fix Command Injection (CWE-78) via eval in dynamic variable ass...  |
| `abhimehro/personal-config`                          | 837 | `abhimehro`      | human/auto | UI          | PASS      | CONFLICTING/DIRTY     | 870           | 1          |  no   | `palette/forgiving-cleanup-prompt-140190492431129` | 🎨 Palette: Improve CLI menu forgiveness for SURGICAL_CLEANUP.sh                            |
| `abhimehro/personal-config`                          | 836 | `abhimehro`      | human/auto | REFACTOR    | PASS      | CONFLICTING/DIRTY     | 870           | 1          |  no   | `qa-redact-hardcoded-pass-media-docs-480008778362` | chore: jules daily QA review and password redaction                                         |
| `abhimehro/personal-config`                          | 835 | `abhimehro`      | human/auto | UI          | PASS      | CONFLICTING/DIRTY     | 869           | 2          |  no   | `palette-forgiving-cli-menu-6468410664231959464`   | 🎨 Palette: Improve interactive yes/no prompt UX                                            |
| `abhimehro/personal-config`                          | 834 | `abhimehro`      | human/auto | REFACTOR    | PASS      | CONFLICTING/DIRTY     | 869           | 2          |  no   | `jules-qa-report-empty-18214421452060065735`       | Jules Daily QA & Agentic Review                                                             |
| `abhimehro/personal-config`                          | 833 | `abhimehro`      | human/auto | REFACTOR    | PASS      | CONFLICTING/DIRTY     | 869           | 3          |  no   | `jules-qa-review-8380590597524349493`              | Jules Daily QA & Agentic Review                                                             |
| `abhimehro/personal-config`                          | 832 | `abhimehro`      | human/auto | SECURITY    | PASS      | CONFLICTING/DIRTY     | 869           | 4          |  no   | `sentinel-fix-cwe150-controld-manager-83666420777` | 🛡️ Sentinel: [HIGH] Fix terminal injection                                                  |
| `abhimehro/personal-config`                          | 831 | `abhimehro`      | human/auto | UI          | PASS      | CONFLICTING/DIRTY     | 866           | 4          |  no   | `palette-graceful-exit-bulk-rename-17860571804999` | 🎨 Palette: Add graceful exit handler to bulk rename script                                 |
| `abhimehro/personal-config`                          | 830 | `abhimehro`      | human/auto | REFACTOR    | PASS      | CONFLICTING/DIRTY     | 867           | 4          |  no   | `jules-qa-review-12409370849091735049`             | Daily QA & Agentic Review - Health Check Passed                                             |

**Columns:** **Kind** = `bot` (GitHub bot/app author) vs `human/auto` (human author with automation markers). **Category** is a heuristic triage label (`SECURITY`, `DEPENDENCY`, `PERFORMANCE`, `UI`, `REFACTOR`, …), not a Gate verdict. **CI rollup** collapses check runs to `PASS` / `FAIL` / `PENDING` / `UNKNOWN` (UNKNOWN when GitHub returned no rollup entries or rollup lacked comparable status).

### Discovery gaps / anomalies

- **Not GitHub-complete:** Only repos with a clone under `/Users/speedybee/dev` were queried; other remotes/orgs may have open automated PRs that do not appear here.
- **`changedFiles` spikes on `personal-config`:** PRs **#830–#838** show **866–870** changed files via the API while adjacent PRs show single-digit counts — treat as **suspect metadata** until re-verified with `gh pr diff --name-only` during triage (possible compare-shas or UI/API inconsistency).
- **Emoji in titles:** Table preserves PR titles as returned by GitHub; some viewers may need UTF-8 rendering.
- **Human automation heuristics:** Title-only matches (e.g. “Jules” after emoji) rely on substring `jules` — if a future human PR mentions Jules incidentally, it could false-positive (rare).

---

# Automated PR inventory — 2026-04-11 (backlog cleanup, review-and-merge)

**Config:** `tasks/pr-review-agent.config.yaml`
**Stale threshold:** 30 days — **none** of the in-scope PRs at inventory time exceeded this (all recent).
**Mode:** `review-and-merge` · **Merge strategy:** squash · **Auto-fix:** enabled (no branch pushes required this session → **0** auto-fix commits)

## Scope rules

1. **Configured bot logins:** `dependabot[bot]`, `renovate[bot]`, `google-labs-jules[bot]` (GitHub may show `app/dependabot`).
2. **Expanded automation:** include PRs where GitHub shows `abhimehro` as author when **branch**, **title**, or **body** indicates Jules / Sentinel / Bolt / Palette / `automation-workflow-*`, etc.
   **Gap noted:** `dotfiles-iac` **#759** (`fix/github-actions-checkout-version-*`) matched via **body** (Jules footer), not branch/title regex — inventory scripts should also scan PR body for the Jules task host (subdomain `jules`, then dot, then the usual Google domain TLD) / `PR created automatically by Jules`. <!-- pragma: allowlist secret -->

## Repos

| Repo           | Slug                                                 |
| -------------- | ---------------------------------------------------- | --------------------------------- |
| Dotfiles / IaC | `abhimehro/dotfiles-iac`                             | <!-- pragma: allowlist secret --> |
| Control D sync | `abhimehro/ctrld-sync`                               |
| Email pipeline | `abhimehro/email-security-pipeline`                  |
| Seatek         | `abhimehro/Seatek_Analysis`                          |
| Hydrograph     | `abhimehro/Hydrograph_Versus_Seatek_Sensors_Project` |

## Initial open inventory (2026-04-11, before actions)

| Repo         |  PR | Author         | Branch (abbr.)                    | Category    | CI (rollup)                | Mergeable   | Files | Notes                                    |
| ------------ | --: | -------------- | --------------------------------- | ----------- | -------------------------- | ----------- | ----: | ---------------------------------------- |
| Hydrograph   | 112 | abhimehro      | `bolt/avoid-sort-*`               | PERFORMANCE | PASS                       | MERGEABLE   |     1 | Superseded → **closed** after #116       |
| Hydrograph   | 114 | abhimehro      | `bolt/optimize-sort-*`            | PERFORMANCE | PASS                       | MERGEABLE   |     5 | Superseded → **closed** after #116       |
| Hydrograph   | 116 | abhimehro      | `bolt-optimize-redundant-*`       | PERFORMANCE | PASS                       | MERGEABLE   |     3 | **Merged** (canonical sort optimization) |
| Seatek       | 129 | abhimehro      | `bolt-optimize-lang-map-*`        | PERFORMANCE | PASS                       | MERGEABLE   |     1 | **Merged**                               |
| Seatek       | 130 | abhimehro      | `bolt/optimize-code-health-*`     | PERFORMANCE | PASS                       | MERGEABLE   |     1 | **Conflicting** after #129 → escalate    |
| ctrld-sync   | 709 | abhimehro      | `palette-ux-emojis-*`             | UX          | PASS                       | CONFLICTING |     2 | **Closed** duplicate vs #716             |
| ctrld-sync   | 711 | abhimehro      | `ux-no-color-emojis-*`            | UX          | PASS                       | MERGEABLE   |     3 | **Closed** duplicate vs #716             |
| ctrld-sync   | 712 | abhimehro      | `sentinel-explicit-loopback-*`    | SECURITY    | PASS                       | MERGEABLE   |     3 | **Merged** (preferred SSRF fix + tests)  |
| ctrld-sync   | 714 | abhimehro      | `sentinel-fix-ssrf-loopback-*`    | SECURITY    | PASS                       | MERGEABLE   |     1 | **Merged**                               |
| ctrld-sync   | 715 | abhimehro      | `sentinel-fix-ssrf-loopback-*`    | SECURITY    | PASS                       | MERGEABLE   |     2 | **Closed** superseded by #712            |
| ctrld-sync   | 716 | abhimehro      | `fix-cli-output-fallbacks-*`      | UX          | PASS                       | MERGEABLE   |     3 | **Merged**                               |
| email        | 646 | abhimehro      | `jules-*`                         | UX          | PASS                       | MERGEABLE   |     3 | **Closed** superseded by #662            |
| email        | 650 | abhimehro      | `palette/ux-*`                    | UX          | FAIL (submit-pypi)         | MERGEABLE   |     2 | **Closed** superseded by #662            |
| email        | 651 | app/dependabot | `dependabot/pip/*`                | DEPENDENCY  | pending/mixed → later PASS | MERGEABLE   |     1 | **Escalate** transformers 5.0.0rc3       |
| email        | 656 | abhimehro      | `palette/cli-*`                   | UX          | PASS                       | MERGEABLE   |     2 | **Closed** superseded by #662            |
| email        | 657 | abhimehro      | `sentinel-fix-assert-*`           | SECURITY    | PASS                       | MERGEABLE   |     1 | **Merged**                               |
| email        | 658 | abhimehro      | `jules-*`                         | PERFORMANCE | PASS                       | MERGEABLE   |     3 | **Merged**                               |
| email        | 659 | abhimehro      | `jules-*`                         | CHORE       | PASS                       | MERGEABLE   |     1 | **Merged**                               |
| email        | 660 | abhimehro      | `automation-workflow-*`           | CI/INFRA    | PASS                       | MERGEABLE   |     2 | **Draft** → escalate                     |
| email        | 662 | abhimehro      | `palette-improve-*`               | UX          | PASS                       | MERGEABLE   |     1 | **Merged**                               |
| dotfiles-iac | 747 | abhimehro      | `palette-accessible-*`            | UX          | PASS                       | MERGEABLE   |     4 | **Closed** redundant vs #760/#754        |
| dotfiles-iac | 748 | abhimehro      | `sentinel/fix-option-injection-*` | SECURITY    | PASS                       | MERGEABLE   |     2 | **Merged**                               |
| dotfiles-iac | 751 | abhimehro      | `fix-spinner-terminal-*`          | UX          | PASS                       | MERGEABLE   |     5 | **Closed** superseded                    |
| dotfiles-iac | 752 | abhimehro      | `fix/option-injection-pgrep-*`    | SECURITY    | PASS                       | MERGEABLE   |     3 | **Closed** superseded by #748            |
| dotfiles-iac | 754 | abhimehro      | `palette/cli-spinner-artifacts-*` | UX          | PASS                       | MERGEABLE   |     4 | **Merged**                               |
| dotfiles-iac | 756 | abhimehro      | `automation-workflow-*`           | CI/INFRA    | PASS                       | MERGEABLE   |     1 | **Draft** → escalate                     |
| dotfiles-iac | 758 | abhimehro      | `jules-*`                         | PERFORMANCE | PASS                       | MERGEABLE   |     2 | **Merged**                               |
| dotfiles-iac | 760 | abhimehro      | `palette-cli-spinner-cleanup-*`   | UX          | PASS                       | MERGEABLE   |     2 | **Merged**                               |

## Post-session remainder (open, in-scope)

| Repo                    |  PR | Reason still open                        |
| ----------------------- | --: | ---------------------------------------- |
| dotfiles-iac            | 756 | Draft workflow consolidation — escalated |
| email-security-pipeline | 660 | Draft workflow consolidation — escalated |
| email-security-pipeline | 651 | RC major dependency bump — escalated     |
| Seatek_Analysis         | 130 | Merge conflict after #129 — escalated    |

## Summary counts (initial inventory)

- **Total in-scope open:** 28
- **By theme:** SECURITY 6 · PERFORMANCE/UX 18 · DEPENDENCY 1 · CI/INFRA (draft) 2 · CHORE 1

---

# Automated PR inventory — 2026-04-23 (review session)

**Config:** `tasks/pr-review-agent.config.yaml`
**Stale threshold:** 30 days
**Mode:** `review-and-merge` · **Merge strategy:** squash · **Auto-fix:** enabled

## Scope rules

1. **Configured bot logins:** `dependabot[bot]`, `renovate[bot]`, `google-labs-jules[bot]`
2. **Expanded automation:** Include PRs where GitHub shows `abhimehro` as author when **body** contains "PR created automatically by Jules"

## Current open inventory (2026-04-23)

| Repo       |      PR | Author            | Branch                           | Category    | CI Status | Mergeable | Files | Age    | Notes                                         |
| ---------- | ------: | ----------------- | -------------------------------- | ----------- | --------- | --------- | ----: | ------ | --------------------------------------------- |
| Hydrograph | **135** | abhimehro (Jules) | `bolt-replace-sum-with-any-*`    | PERFORMANCE | **PASS**  | CLEAN     |     2 | 3 days | `.any()` optimization — **keep as canonical** |
| Hydrograph | **133** | abhimehro (Jules) | `bolt-any-optimization-*`        | PERFORMANCE | **PASS**  | CLEAN     |     4 | 4 days | Superset of #135 — **close as superseded**    |
| Hydrograph | **131** | abhimehro (Jules) | `bolt/optimize-sum-operations-*` | PERFORMANCE | **PASS**  | CLEAN     |     6 | 5 days | Superset of #133 — **close as superseded**    |

## File overlap analysis

| File                                               | #135 | #133 | #131 |
| -------------------------------------------------- | :--: | :--: | :--: |
| `src/hydrograph_seatek_analysis/data/validator.py` |  ✓   |  ✓   |  ✓   |
| `benchmark_boolean.py`                             |  ✓   |  ✓   |  ✓   |
| `test_perf.py`                                     |  —   |  ✓   |  ✓   |
| `.jules/bolt.md`                                   |  —   |  ✓   |  ✓   |
| `utils/processor.py`                               |  —   |  —   |  ✓   |
| `benchmark_array_cache.py`                         |  —   |  —   |  ✓   |

**Observation:** PR #135 ⊂ PR #133 ⊂ PR #131 (nested supersets). All implement same optimization pattern.

## Disposition summary

|  PR | Disposition         | Rationale                            |
| --: | ------------------- | ------------------------------------ |
| 135 | **MERGE**           | Most focused, recent, all gates pass |
| 133 | **CLOSE-DUPLICATE** | Superseded by #135 (subset)          |
| 131 | **CLOSE-DUPLICATE** | Superseded by #135 (subset)          |

## Summary counts

- **Total in-scope open:** 3
- **By theme:** PERFORMANCE 3
- **Action:** MERGE 1 · CLOSE-DUPLICATE 2

---

# Automated PR inventory — 2026-04-25 (backlog cleanup, review-and-merge)

**Config:** `tasks/pr-review-agent.config.yaml`
**Stale threshold:** 30 days — none of the in-scope PRs at inventory time exceeded this (all ≤ 2 days old).
**Mode:** `review-and-merge` · **Merge strategy:** squash · **Auto-fix:** enabled (no auto-fix commits required this session)
**Preflight:** `gh auth status` confirmed `GH_TOKEN` for `abhimehro` (branch-protection introspection denied by token scope; merges via gh CLI work).

## Scope rules

1. **Configured bot logins:** `dependabot[bot]`, `renovate[bot]`, `google-labs-jules[bot]` (GitHub may surface `app/dependabot`).
2. **Expanded automation:** include PRs where GitHub shows `abhimehro` as the author when the **branch**, **title**, **body**, or **comments** indicate Jules / Sentinel / Bolt / Palette / `automation-workflow-*` / `jules.google.com/task/`.
3. **Coverage check:** all 44 open PRs across the 5 repos matched at least one automation signal — every PR was bot-authored or carried a Jules/Sentinel/Bolt/Palette/Dependabot footer or branch prefix. No false positives required filtering.

## Initial open inventory (2026-04-25, before actions)

| Repo                    |  PR | Author                    | Branch (abbr.)                                       | Category            | CI (rollup)                       | Mergeable                          | Files | Disposition                                           |
| ----------------------- | --: | ------------------------- | ---------------------------------------------------- | ------------------- | --------------------------------- | ---------------------------------- | ----: | ----------------------------------------------------- | --------------------------------- |
| personal-config         | 823 | abhimehro (Sentinel)      | `fix/option-injection-cwe88-*`                       | SECURITY            | PASS                              | MERGEABLE/CLEAN                    |     4 | **MERGED**                                            | <!-- pragma: allowlist secret --> |
| personal-config         | 822 | abhimehro (Palette)       | `palette-graceful-exit-*`                            | UI                  | PASS                              | MERGEABLE/CLEAN                    |     3 | **MERGED**                                            | <!-- pragma: allowlist secret --> |
| personal-config         | 821 | abhimehro (Jules QA)      | `jules/qa-review-*`                                  | (zero-diff)         | PASS                              | MERGEABLE/CLEAN                    |     0 | **CLOSED** zero-diff                                  | <!-- pragma: allowlist secret --> |
| personal-config         | 820 | abhimehro (Bolt)          | `bolt/optimize-json-parsing-*`                       | PERFORMANCE         | FAIL                              | MERGEABLE/UNSTABLE                 |     4 | DEFER (UNSTABLE)                                      | <!-- pragma: allowlist secret --> |
| personal-config         | 819 | abhimehro (Jules)         | `testing-improvement-horoscope-*`                    | REFACTOR            | PASS                              | MERGEABLE/CLEAN                    |     1 | **MERGED**                                            | <!-- pragma: allowlist secret --> |
| personal-config         | 818 | abhimehro (Bolt)          | `bolt-optimize-detect-duplicates-*`                  | PERFORMANCE         | PASS                              | CONFLICTING/DIRTY                  |     2 | DEFER (DIRTY)                                         | <!-- pragma: allowlist secret --> |
| personal-config         | 817 | abhimehro (Jules)         | `fix-unused-import-os-*`                             | REFACTOR            | PASS                              | MERGEABLE/CLEAN                    |     2 | **MERGED**                                            | <!-- pragma: allowlist secret --> |
| personal-config         | 816 | abhimehro (Sentinel)      | `fix-command-injection-runrun-gh-*`                  | SECURITY            | PASS                              | CONFLICTING/DIRTY                  |     7 | **ESCALATE** (PR automation toolchain trust boundary) | <!-- pragma: allowlist secret --> |
| personal-config         | 815 | abhimehro (Sentinel)      | `sentinel/fix-pgrep-option-injection-*`              | SECURITY            | PASS                              | MERGEABLE/CLEAN                    |     4 | **CLOSED** dup of #823                                | <!-- pragma: allowlist secret --> |
| personal-config         | 814 | abhimehro (Palette)       | `palette-youtube-download-ux-*`                      | UI                  | PASS                              | MERGEABLE/CLEAN                    |     1 | **MERGED**                                            | <!-- pragma: allowlist secret --> |
| personal-config         | 813 | abhimehro (Jules QA)      | `jules-qa-report-update-*`                           | (zero-diff)         | PASS                              | MERGEABLE/CLEAN                    |     0 | **CLOSED** zero-diff                                  | <!-- pragma: allowlist secret --> |
| personal-config         | 812 | abhimehro (Bolt)          | `bolt-cache-env-parsing-*`                           | PERFORMANCE         | PASS                              | MERGEABLE/CLEAN → DIRTY            |     5 | DEFER (DIRTY post-cascade)                            | <!-- pragma: allowlist secret --> |
| personal-config         | 811 | abhimehro (Sentinel)      | `sentinel-fix-cwe-78-eval-caches-*`                  | SECURITY            | PASS                              | MERGEABLE/CLEAN                    |     1 | **MERGED**                                            | <!-- pragma: allowlist secret --> |
| personal-config         | 810 | abhimehro (Palette)       | `palette-graceful-exit-trap-*`                       | UI                  | PASS                              | MERGEABLE/CLEAN                    |     2 | **CLOSED** dup of #822                                | <!-- pragma: allowlist secret --> |
| personal-config         | 809 | abhimehro (Jules QA)      | `qa-report-*`                                        | (zero-diff)         | PASS                              | MERGEABLE/CLEAN                    |     0 | **CLOSED** zero-diff                                  | <!-- pragma: allowlist secret --> |
| personal-config         | 808 | abhimehro (Bolt)          | `bolt/optimize-dict-lookup-comprehension-*`          | PERFORMANCE         | PASS                              | MERGEABLE/CLEAN                    |     3 | **MERGED**                                            | <!-- pragma: allowlist secret --> |
| ctrld-sync              | 742 | abhimehro (Palette)       | `chore/ux-hidden-input-*`                            | UI                  | PASS                              | MERGEABLE/CLEAN → DIRTY            |     4 | DEFER (DIRTY post-cascade)                            |
| ctrld-sync              | 741 | abhimehro (Jules QA)      | `qa-daily-review-*`                                  | (zero-diff)         | PASS                              | MERGEABLE/CLEAN                    |     0 | **CLOSED** zero-diff                                  |
| ctrld-sync              | 740 | abhimehro (Bolt)          | `optimize-clean-env-kv-*`                            | PERFORMANCE         | PASS                              | MERGEABLE/CLEAN                    |     3 | **MERGED**                                            |
| ctrld-sync              | 739 | abhimehro (Jules)         | `tests-add-clean-env-kv-tests-*`                     | REFACTOR            | PASS                              | MERGEABLE/CLEAN                    |     1 | **MERGED**                                            |
| ctrld-sync              | 738 | abhimehro (Bolt)          | `perf-optimize-folder-validation-*`                  | PERFORMANCE         | PASS                              | CONFLICTING/DIRTY                  |     1 | DEFER (DIRTY)                                         |
| ctrld-sync              | 737 | abhimehro (Sentinel)      | `security-fix-predictable-cache-temp-file-*`         | SECURITY            | PASS                              | CONFLICTING/DIRTY                  |     2 | **ESCALATE** (security + DIRTY)                       |
| ctrld-sync              | 736 | abhimehro (Palette)       | `ux-password-hidden-hint-*`                          | UI                  | PASS                              | MERGEABLE/CLEAN                    |     2 | **CLOSED** dup of #742                                |
| ctrld-sync              | 735 | abhimehro (Bolt)          | `bolt-optimize-clean-env-kv-*`                       | PERFORMANCE         | PASS                              | MERGEABLE/CLEAN                    |     2 | **CLOSED** dup of #740                                |
| ctrld-sync              | 734 | abhimehro (Palette/Jules) | `jules-*-8d93aea1`                                   | UI                  | PASS                              | MERGEABLE/CLEAN                    |     1 | **MERGED**                                            |
| email-security-pipeline | 721 | abhimehro (Sentinel)      | `jules-1763991674-*`                                 | SECURITY            | FAIL (pytest pre-existing)        | MERGEABLE/UNSTABLE                 |     2 | **ESCALATE**                                          |
| email-security-pipeline | 720 | abhimehro (Jules)         | `code-health-main-py-imports-*`                      | REFACTOR            | PASS                              | CONFLICTING/DIRTY                  |     2 | DEFER (DIRTY)                                         |
| email-security-pipeline | 719 | abhimehro (Sentinel)      | `security-fix-toctou-permissions-*`                  | SECURITY            | FAIL (pytest+CodeQL+CodeScene)    | MERGEABLE/UNSTABLE                 |     4 | **ESCALATE**                                          |
| email-security-pipeline | 718 | abhimehro (Jules)         | `test-caching-eviction-*`                            | REFACTOR            | FAIL (pytest pre-existing)        | MERGEABLE/UNSTABLE                 |     1 | DEFER (test infra)                                    |
| email-security-pipeline | 717 | abhimehro (Palette)       | `palette-empty-state-ux-*`                           | UI                  | FAIL (pytest pre-existing)        | MERGEABLE/UNSTABLE                 |     3 | DEFER (test infra)                                    |
| email-security-pipeline | 715 | abhimehro (Sentinel)      | `jules-1790347126-*`                                 | SECURITY            | FAIL (pytest+CodeQL)              | MERGEABLE/UNSTABLE                 |     4 | **ESCALATE**                                          |
| Seatek_Analysis         | 156 | abhimehro (Sentinel)      | `sentinel/fix-exc-info-leak-*`                       | SECURITY            | FAIL (validate pre-existing)      | MERGEABLE/UNSTABLE → DIRTY         |     2 | DEFER/escalate (`.github/scripts/`)                   |
| Seatek_Analysis         | 155 | abhimehro (Bolt)          | `bolt-opt-*`                                         | PERFORMANCE + INFRA | PASS (validate pre-existing fail) | MERGEABLE/CLEAN                    |     4 | **MERGED** (also fixes validate via pandas pin)       |
| Seatek_Analysis         | 154 | abhimehro (Jules)         | `testing-improvement-outlier-analysis-*`             | REFACTOR            | FAIL → PASS after #155            | MERGEABLE/UNSTABLE → CLEAN         |     1 | **MERGED** (after #155 unblocked validate)            |
| Seatek_Analysis         | 153 | abhimehro (Bolt)          | `perf-list-comp-scan-file-*`                         | PERFORMANCE         | PASS                              | CONFLICTING/DIRTY                  |     2 | DEFER (DIRTY, mostly superseded by #155)              |
| Seatek_Analysis         | 152 | abhimehro (Jules)         | `code-health-unreachable-code-*`                     | REFACTOR            | FAIL → 0-diff after sync          | MERGEABLE/UNSTABLE → CLEAN(0-diff) |     1 | **CLOSED** zero-diff after sync                       |
| Seatek_Analysis         | 151 | app/dependabot            | `dependabot/pip/Series_27/Analysis/matplotlib-gte-3` | DEPENDENCY          | FAIL → PASS after #155            | MERGEABLE/UNSTABLE → CLEAN         |     1 | **MERGED** (after #155 unblocked validate)            |
| Seatek_Analysis         | 150 | abhimehro (Bolt)          | `bolt/optimize-scan-file-*`                          | PERFORMANCE         | PASS                              | MERGEABLE/CLEAN                    |     3 | **CLOSED** dup of #155                                |
| Seatek_Analysis         | 149 | abhimehro (Bolt)          | `bolt-perf-list-comprehension-*`                     | PERFORMANCE         | PASS                              | MERGEABLE/CLEAN                    |     3 | **CLOSED** dup of #155                                |
| Hydrograph              | 146 | abhimehro (Jules)         | `fix-line-lengths-*`                                 | REFACTOR            | PASS                              | CONFLICTING/DIRTY                  |     3 | DEFER (DIRTY)                                         |
| Hydrograph              | 145 | abhimehro (Jules)         | `testing-improvement-dataloader-exception-*`         | REFACTOR            | PASS                              | CONFLICTING/DIRTY                  |     1 | DEFER (DIRTY)                                         |
| Hydrograph              | 144 | abhimehro (Sentinel)      | `security-fix-file-size-validation-*`                | SECURITY            | PASS                              | CONFLICTING/DIRTY                  |     4 | DEFER (DIRTY, security review queued)                 |
| Hydrograph              | 143 | abhimehro (Jules)         | `code-health-cleanup-unused-imports-*`               | REFACTOR            | PASS                              | CONFLICTING/DIRTY                  |     1 | DEFER (DIRTY)                                         |
| Hydrograph              | 140 | abhimehro (Bolt)          | `perf-optimize-np-count-nonzero-*`                   | PERFORMANCE         | PASS                              | MERGEABLE/CLEAN                    |     2 | **MERGED**                                            |

## Post-session remainder (open, in-scope)

| Repo                    |  PR | Reason still open                                                               |
| ----------------------- | --: | ------------------------------------------------------------------------------- | --------------------------------- |
| personal-config         | 820 | UNSTABLE rollup; needs CI re-run after rebase                                   | <!-- pragma: allowlist secret --> |
| personal-config         | 818 | DIRTY post-cascade (Lesson 0); just needs rebase                                | <!-- pragma: allowlist secret --> |
| personal-config         | 812 | DIRTY post-cascade (Lesson 0); just needs rebase                                | <!-- pragma: allowlist secret --> |
| personal-config         | 816 | **Escalated** — rewrites PR automation toolchain (trust boundary)               | <!-- pragma: allowlist secret --> |
| ctrld-sync              | 742 | DIRTY post-cascade after #740 merged                                            |
| ctrld-sync              | 738 | DIRTY (pre-existing)                                                            |
| ctrld-sync              | 737 | **Escalated** — predictable temp-file fix; DIRTY                                |
| email-security-pipeline | 721 | **Escalated** — CRITICAL filename bypass + broken pytest infra on main          |
| email-security-pipeline | 720 | DIRTY (`payload.json` cascade, Lesson 0)                                        |
| email-security-pipeline | 719 | **Escalated** — TOCTOU + CodeQL failing                                         |
| email-security-pipeline | 718 | DEFER — blocked by pre-existing pytest collection errors on main                |
| email-security-pipeline | 717 | DEFER — same pytest blocker                                                     |
| email-security-pipeline | 715 | **Escalated** — `O_NOFOLLOW` symlink hardening + CodeQL failing                 |
| Seatek_Analysis         | 156 | DEFER — DIRTY (manual conflict resolution required); touches `.github/scripts/` |
| Seatek_Analysis         | 153 | DEFER — DIRTY, mostly superseded by #155                                        |
| Hydrograph              | 146 | DEFER — DIRTY (pre-existing)                                                    |
| Hydrograph              | 145 | DEFER — DIRTY (pre-existing)                                                    |
| Hydrograph              | 144 | DEFER — DIRTY (security file-size validation; rebase + human review)            |
| Hydrograph              | 143 | DEFER — DIRTY (trivial unused-imports cleanup)                                  |

## Summary counts (initial inventory)

- **Total in-scope open:** 44
- **By theme:** SECURITY 13 · PERFORMANCE 12 · UI 6 · REFACTOR 9 · DEPENDENCY 1 · zero-diff QA 4 (CHORE-equivalent)
- **By disposition:** MERGED 15 · CLOSED-DUP 6 · CLOSED-ZERODIFF 5 · ESCALATED 6 · DEFERRED 12

## New scope-expansion observations (this session)

- **All 44 PRs were in-scope.** Every human-authored PR also carried at least one of the automation signals (branch prefix, emoji marker like 🛡️/🎨/⚡/🧪/🧹, Jules task footer, or Dependabot author). No false-positive filtering was needed.
- **Lesson 0u (new):** A single in-scope PR can fix the CI infra it depends on. Seatek `#155` not only applied the Bolt list-comprehension change but also pinned `pandas<3.0.0` in `Series_27/Analysis/requirements.txt` and bumped CI Python from 3.10 to 3.11, unblocking the `validate` job for the entire repo. Once merged, calling `update-branch` on sibling PRs (`#151`, `#152`, `#154`, `#156`) re-ran their checks against the fixed workflow — three of them flipped to MERGEABLE/CLEAN and were merged in the same session.
