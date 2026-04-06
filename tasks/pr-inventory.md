# Automated PR inventory — 2026-04-03 (backlog cleanup, review-and-merge)

**Config:** `tasks/pr-review-agent.config.yaml`
**Stale threshold:** 30 days (no in-scope open PR exceeded this at inventory time)
**Mode:** `review-and-merge` · **Merge strategy:** squash · **Auto-fix:** enabled

**Repo note:** Use `abhimehro/personal-config` in config and URLs; some environments redact the slug as `personal-config` in CLI or logs. Same repository.

## Scope rules

1. **Configured bot logins:** `dependabot[bot]`, `renovate[bot]`, `google-labs-jules[bot]` (GitHub may surface Dependabot as `app/dependabot`).
2. **Expanded automation:** include PRs where GitHub shows `abhimehro` as author when **branch**, **title**, **labels**, or **comments** indicate Jules / Sentinel / Bolt / Palette / daily QA / `automation-workflow-*`, etc.

## Historical inventory — 2026-03-27 (archived snapshot)

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

## Inventory validated — 2026-04-03 19:45 UTC (current open PRs)

### personal-config (10 open, 2 recently merged)

| PR # | Status | Title | Category | Created | Changed Files | Notes |
|------|--------|-------|----------|---------|---------------|-------|
| **728** | **MERGED** | 🎨 Palette: Graceful TTY Degradation for spinners | UX | 2026-04-03 | 2 | Merged 19:38:59 |
| **727** | **MERGED** | ⚡ Bolt: fnmatch→regex optimization | PERFORMANCE | 2026-04-03 | 1 | Merged 19:38:43 |
| 726 | OPEN | ⚡ Bolt: optimize matches_any with compiled regex | PERFORMANCE | 2026-04-03 | 1 | **DUPLICATE of #727** |
| 725 | OPEN | ⚡ Bolt: rglob→os.walk hotspot discovery | PERFORMANCE | 2026-04-03 | 1 | — |
| 724 | OPEN | ⚡ Bolt: optimize datetime parsing in Linear issue | PERFORMANCE | 2026-04-03 | 1 | — |
| 723 | OPEN | ⚡ Bolt: Optimize dictionary access in AdGuard | PERFORMANCE | 2026-04-03 | 2 | — |
| 722 | OPEN | ⚡ Bolt: optimize matches_any with cached regex | PERFORMANCE | 2026-04-03 | 1 | **DUPLICATE of #727** |
| 719 | OPEN | chore: Jules Daily QA domain injection | CI/INFRA | 2026-04-02 | 1 | — |
| 710 | OPEN | chore: Jules Daily QA & Agentic Review | CI/INFRA | 2026-04-02 | 0 | **ZERO-DIFF** |
| 708 | OPEN | ⚡ Bolt: basename→parameter expansion in test runner | PERFORMANCE | 2026-04-02 | 1 | — |

### ctrld-sync (1 open)

| PR # | Status | Title | Category | Created | Changed Files | Notes |
|------|--------|-------|----------|---------|---------------|-------|
| 697 | OPEN | fix: Update ruff configuration schema | FIX | 2026-04-03 | 1 | Ruff deprecation warning |

### email-security-pipeline (3 open)

| PR # | Status | Title | Category | Created | Changed Files | Notes |
|------|--------|-------|----------|---------|---------------|-------|
| 629 | OPEN | chore: update AGENTS.md test count/dev setup | CHORE | 2026-04-03 | 1 | Documentation |
| 626 | OPEN | chore(actions): consolidate workflow automation | CI/INFRA | 2026-04-03 | 14 | **DRAFT** - workflow updates |
| 625 | OPEN | Jules Daily QA & Agentic Review | CI/INFRA | 2026-04-03 | 0 | **ZERO-DIFF** |

### Seatek_Analysis (3 open)

| PR # | Status | Title | Category | Created | Changed Files | Notes |
|------|--------|-------|----------|---------|---------------|-------|
| 122 | OPEN | 🛡️ Sentinel: [CRITICAL] Fix TOCTOU vulnerability | SECURITY | 2026-04-02 | 2 | File reading race condition |
| 121 | OPEN | ⚡ Bolt: Optimize hotspot discovery (os.walk) | PERFORMANCE | 2026-04-02 | 1 | **SIMILAR to personal-config#725** |
| 120 | OPEN | 🛡️ Sentinel: [CRITICAL] Fix TOCTOU/OOM DoS | SECURITY | 2026-04-01 | 1 | code_health_scanner.py |

### Hydrograph_Versus_Seatek_Sensors_Project (2 open)

| PR # | Status | Title | Category | Created | Changed Files | Notes |
|------|--------|-------|----------|---------|---------------|-------|
| 100 | OPEN | 🛡️ Sentinel: Reject symlinks in file validation | SECURITY | 2026-04-02 | 2 | Symlink attack prevention |
| 99 | OPEN | 🛡️ Sentinel: [MEDIUM] Fix Symlink processing | SECURITY | 2026-04-01 | 2 | **DUPLICATE of #100** |

## Validated Summary (2026-04-03 session)

- **Total open PRs**: 19 (down from 38 in stale inventory)
- **Recently merged**: 2 (personal-config #728, #727)
- **By category**:
  - **SECURITY**: 4 (all Seatek/Hydro - CRITICAL TOCTOU, symlink fixes)
  - **PERFORMANCE**: 7 (Bolt optimizations across repos)
  - **CI/INFRA**: 3 (workflow updates, Jules QA)
  - **CHORE/FIX**: 3 (documentation, ruff config)
  - **UX**: 0 (recent Palette PRs already merged)
- **Zero-diff PRs to close**: 2 (personal-config #710, email-security-pipeline #625)
- **Clear duplicates**: 4 (personal-config #726/#722 duplicate #727; Hydro #99 duplicate #100)
- **No stale PRs** (all created within last 3 days)

## Inventory after session — 2026-04-01 (remaining open)

| Repo                    | PR # | State | Reason still open                                                    |
| ----------------------- | ---: | ----- | -------------------------------------------------------------------- |
| personal-config         |  697 | DRAFT | Escalated — workflow consolidation / trust boundary                  |
| ctrld-sync              |  687 | DRAFT | Escalated — failing CI + workflow consolidation                      |
| email-security-pipeline |  612 | DRAFT | Escalated — workflow consolidation                                   |
| email-security-pipeline |  614 | OPEN  | Merge conflicts with `main`; human rebase + CodeScene hotspot review |
