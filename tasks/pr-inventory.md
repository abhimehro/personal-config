# Automated PR inventory — backlog cleanup session (2026-05-09)

**Preflight:** `bash scripts/preflight-gh-pr-automation.sh --config tasks/pr-review-agent.config.yaml` — **passed** (read-only, six repos).

**Config:** `tasks/pr-review-agent.config.yaml` — `mode: review-and-merge`, `merge_strategy: squash`, `stale_threshold_days: 30`, `auto_fix_enabled: true`, `schedule: none`.

**Bot authors (explicit):** `dependabot[bot]`, `renovate[bot]`, `google-labs-jules[bot]`, `devin[bot]`, `copilot[bot]`, plus `app/copilot-swe-agent` where present.

**Scope expansion:** PRs whose GitHub author is `abhimehro` are included when **branch name**, **title**, or **PR body** matches automation heuristics (Jules/Bolt/Devin/Sentinel/Palette/Copilot/Renovate/Dependabot/daily QA patterns, `jules.google.com` links, etc.).

**Signal legend:** `A` = explicit bot author; `branch` / `title` / `body` = automation signal for human login; `C` / `U` / `P` / `?` = CI rollup clean / failing / pending / unknown from API.

**Repo alias:** Rows labeled **dotfiles** map to the maintainer dotfiles GitHub repository in this workspace (same remote as `git clone` for this IaC repo). Branch names are omitted for that repo in this table to satisfy Cloud secret-scan hooks.

| Repo | PR | Author | Branch | Files | CI | Merge state | Age (d) | Scope |
| --- | ---: | --- | --- | ---: | --- | --- | ---: | --- |
| Hydrograph_Versus_Seatek_Sensors_Project | 172 | abhimehro | `bolt-optimize-pandas-evals-17531280884107084690` | 4 | C | CLEAN | 1 | branch |
| Hydrograph_Versus_Seatek_Sensors_Project | 171 | abhimehro | `bolt/optimize-notna-any-5478838913616562987` | 3 | U | UNSTABLE | 2 | branch |
| Hydrograph_Versus_Seatek_Sensors_Project | 170 | app/copilot-swe-agent | `copilot/address-reviewer-comments` | 3 | C | DIRTY | 3 | bot |
| Seatek_Analysis | 164 | abhimehro | `sentinel-fix-oom-seatek-94376729327045651` | 1 | C | CLEAN | 1 | branch |
| Seatek_Analysis | 163 | abhimehro | `optimize-get-language-6427219051321492677` | 2 | U | UNSTABLE | 1 | branch |
| Seatek_Analysis | 162 | abhimehro | `sentinel-oom-prevention-r-16693932677267020846` | 2 | C | CLEAN | 2 | branch |
| Seatek_Analysis | 161 | abhimehro | `bolt/optimize-r-loops-15192472221910519233` | 3 | C | CLEAN | 2 | branch |
| ctrld-sync | 775 | abhimehro | `fix-auth-log-leakage-16522109757379176870` | 2 | C | CLEAN | 0 | branch |
| ctrld-sync | 774 | abhimehro | `fix-log-sanitization-authorization-12438108016152085206` | 2 | C | CLEAN | 1 | branch |
| ctrld-sync | 773 | abhimehro | `palette-pluralization-2436042953806849834` | 1 | C | CLEAN | 1 | branch |
| ctrld-sync | 772 | abhimehro | `fix/sanitize-authorization-param-14814906865062264945` | 2 | C | CLEAN | 2 | branch |
| ctrld-sync | 771 | abhimehro | `chore/palette-pluralization-ux-1175540864641397211` | 1 | C | CLEAN | 2 | title |
| ctrld-sync | 770 | abhimehro | `fix-log-leak-authorization-4050145955284402317` | 2 | C | CLEAN | 3 | branch |
| ctrld-sync | 769 | abhimehro | `devin/1778007977-fix-summary-yml-injection` | 1 | C | CLEAN | 3 | branch |
| ctrld-sync | 763 | abhimehro | `fix-content-type-validation-4184539243305221398` | 2 | C | CLEAN | 5 | branch |
| email-security-pipeline | 796 | abhimehro | `fix/ux-no-color-fallback-15649092721049480732` | 6 | U | UNSTABLE | 0 | branch |
| email-security-pipeline | 795 | abhimehro | `fix/ux-no-color-fallback` | 7 | U | UNSTABLE | 0 | branch |
| email-security-pipeline | 793 | abhimehro | `bolt/cache-optimization-5529545646626598852` | 3 | C | CLEAN | 0 | branch |
| email-security-pipeline | 792 | abhimehro | `bolt/cache-optimization` | 3 | C | CLEAN | 0 | branch |
| email-security-pipeline | 791 | abhimehro | `palette-cli-color-ux-15979091891601376263` | 2 | C | CLEAN | 1 | branch |
| email-security-pipeline | 790 | abhimehro | `palette-cli-color-ux` | 2 | C | CLEAN | 1 | branch |
| email-security-pipeline | 788 | abhimehro | `jules-14488422955334350144-dd57f593` | 0 | C | CLEAN | 1 | branch |
| email-security-pipeline | 786 | abhimehro | `bolt/ttlcache-monotonic-12780262336598065075` | 3 | C | CLEAN | 1 | branch |
| email-security-pipeline | 785 | abhimehro | `bolt/ttlcache-monotonic` | 3 | C | CLEAN | 1 | branch |
| email-security-pipeline | 784 | abhimehro | `palette-color-fix` | 2 | C | CLEAN | 2 | branch |
| email-security-pipeline | 782 | abhimehro | `daily-qa-review-12409661141498693726` | 0 | C | CLEAN | 2 | branch |
| email-security-pipeline | 778 | abhimehro | `fix-ci-submit-pypi-new` | 3 | C | CLEAN | 3 | branch |
| dotfiles | 912 | abhimehro | `(omitted)` | 2 | C | CLEAN | 0 | branch |
| dotfiles | 911 | abhimehro | `(omitted)` | 8 | C | CLEAN | 0 | branch |
| dotfiles | 910 | abhimehro | `(omitted)` | 2 | C | CLEAN | 1 | branch |
| dotfiles | 909 | abhimehro | `(omitted)` | 4 | C | CLEAN | 1 | branch |
| dotfiles | 908 | abhimehro | `(omitted)` | 0 | C | CLEAN | 1 | branch |
| dotfiles | 907 | abhimehro | `(omitted)` | 1 | C | CLEAN | 1 | branch |
| dotfiles | 906 | abhimehro | `(omitted)` | 2 | C | CLEAN | 2 | branch |
| dotfiles | 905 | abhimehro | `(omitted)` | 4 | C | CLEAN | 2 | branch |
| dotfiles | 904 | abhimehro | `(omitted)` | 1 | C | CLEAN | 2 | branch |
| dotfiles | 903 | abhimehro | `(omitted)` | 6 | C | CLEAN | 2 | branch |
| dotfiles | 901 | app/copilot-swe-agent | `(omitted)` | 2 | C | DIRTY | 3 | bot |
| dotfiles | 893 | abhimehro | `(omitted)` | 1 | C | CLEAN | 4 | branch |
| dotfiles | 884 | abhimehro | `(omitted)` | 34 | C | DIRTY | 6 | branch |
| dotfiles | 880 | abhimehro | `(omitted)` | 34 | C | DIRTY | 6 | branch |
| dotfiles | 869 | abhimehro | `(omitted)` | 32 | C | DIRTY | 6 | branch |
| dotfiles | 867 | abhimehro | `(omitted)` | 34 | C | DIRTY | 6 | branch |
| dotfiles | 862 | abhimehro | `(omitted)` | 33 | C | DIRTY | 6 | branch |
| dotfiles | 858 | abhimehro | `(omitted)` | 1 | U | UNSTABLE | 6 | branch |
| dotfiles | 856 | abhimehro | `(omitted)` | 1 | U | DIRTY | 6 | branch |
| dotfiles | 851 | abhimehro | `(omitted)` | 33 | C | DIRTY | 6 | branch |
| dotfiles | 849 | abhimehro | `(omitted)` | 84 | C | DIRTY | 7 | branch |
| dotfiles | 840 | abhimehro | `(omitted)` | 83 | U | DIRTY | 7 | branch |
| dotfiles | 836 | abhimehro | `(omitted)` | 870 | U | DIRTY | 8 | branch |
| dotfiles | 831 | abhimehro | `(omitted)` | 867 | U | DIRTY | 11 | branch |
| series_correction_project_updated | 14 | abhimehro | `bolt/optimize-rolling-mad-13070011960302586380` | 3 | C | CLEAN | 0 | branch |
| series_correction_project_updated | 13 | abhimehro | `bolt-pandas-rolling-optimization-14903311665200800070` | 2 | C | CLEAN | 1 | branch |
| series_correction_project_updated | 12 | abhimehro | `bolt-optimize-mad-4553280272921602868` | 3 | C | CLEAN | 2 | branch |
| series_correction_project_updated | 11 | abhimehro | `refactor-main-blocks-6972017941182300254` | 5 | U | UNSTABLE | 2 | branch |

**Count (in-scope at start):** 55
