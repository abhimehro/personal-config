# PR Inventory — 2026-07-31 (Phase 2 Salvage)

Source: Phase 1 draft [#1855](https://github.com/abhimehro/personal-config/pull/1855) remainder + live re-fetch.

## Open automation / bot-ish PRs (post Phase 1)

| Repo | Open remainder | CONFLICTING | Notes |
|------|---------------:|------------:|-------|
| personal-config | 5 → salvage/close | 5 → 0 | Salvaged palette + micro-opts; closed #1830 |
| ctrld-sync | 3 | 0 | REQUEST_CHANGES / DEFER |
| email-security-pipeline | 1 | 0 | DEFER large split |
| Seatek_Analysis | 4 | 3 → 1 | #552 salvaged → #571; #554/#560 remain |
| Hydrograph… | 4 | 0 | #443/#442 auto-resolved CLEAN |
| series_correction… | 3 | 2 | #336 escalate broken auth; #322/#337 hold |
| repoprompt-ce | 8 | 4 | All DEFER/ESCALATE (CI/huge) |

## Salvage drafts opened this session

| Draft | Salvages |
|-------|----------|
| [pc #1856](https://github.com/abhimehro/personal-config/pull/1856) | #1840/#1835 skip-link |
| [pc #1857](https://github.com/abhimehro/personal-config/pull/1857) | #1824/#1823 parse opts |
| [seatek #571](https://github.com/abhimehro/Seatek_Analysis/pull/571) | #552 list-only shell |

## Closed this session

pc #1840, #1835, #1824, #1823, #1830; Seatek #552
# PR Inventory — 2026-07-31

Generated: 2026-07-31T13:11Z UTC
Total open: **61** (all matched automation signals)

| Repo | PR | Author | CI | Mergeable | Files | Title |
| --- | ---: | --- | --- | --- | ---: | --- |
| Hydrograph_Versus_Seatek_Sensors_Project | [446](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/446) | abhimehro | PASS | MERGEABLE | 2 | ⚡ Bolt: Remove redundant dropna to avoid intermediate allocation |
| Hydrograph_Versus_Seatek_Sensors_Project | [445](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/445) | abhimehro | PASS | MERGEABLE | 2 | 🛡️ Sentinel: [CRITICAL] Fix path traversal in CLI output flag |
| Hydrograph_Versus_Seatek_Sensors_Project | [443](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/443) | app/dependabot | PASS | MERGEABLE | 2 | chore(deps-dev): bump scipy from 1.15.3 to 1.18.0 |
| Hydrograph_Versus_Seatek_Sensors_Project | [442](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/442) | app/dependabot | PASS | MERGEABLE | 2 | chore(deps): bump matplotlib from 3.10.9 to 3.11.1 |
| Hydrograph_Versus_Seatek_Sensors_Project | [441](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/441) | app/dependabot | PASS | MERGEABLE | 2 | chore(deps): bump numpy from 2.2.6 to 2.4.6 |
| Hydrograph_Versus_Seatek_Sensors_Project | [440](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/440) | app/dependabot | PASS | MERGEABLE | 2 | chore(deps): bump pandas-stubs from 2.3.3.260113 to 3.0.3.260530 |
| Seatek_Analysis | [569](https://github.com/abhimehro/Seatek_Analysis/pull/569) | abhimehro | PASS | MERGEABLE | 2 | ⚡ Bolt: Optimize compute_sensor_metrics with native loops |
| Seatek_Analysis | [568](https://github.com/abhimehro/Seatek_Analysis/pull/568) | abhimehro | PASS | MERGEABLE | 1 | 🛡️ Sentinel: [CRITICAL/HIGH] Fix path hijacking vulnerability in repos |
| Seatek_Analysis | [567](https://github.com/abhimehro/Seatek_Analysis/pull/567) | abhimehro | PASS | MERGEABLE | 0 | chore(automation): Daily QA & Agentic Review — 2026-07-30 |
| Seatek_Analysis | [563](https://github.com/abhimehro/Seatek_Analysis/pull/563) | abhimehro | PASS | MERGEABLE | 0 | 🧪 [testing improvement] Add unit tests for classify_entries |
| Seatek_Analysis | [561](https://github.com/abhimehro/Seatek_Analysis/pull/561) | abhimehro | PASS | MERGEABLE | 2 | ⚡ Extract anonymous function in lapply to reduce instantiation overhea |
| Seatek_Analysis | [560](https://github.com/abhimehro/Seatek_Analysis/pull/560) | abhimehro | PASS | MERGEABLE | 3 | ⚡ Parallelize sequential loop in process_all_data |
| Seatek_Analysis | [555](https://github.com/abhimehro/Seatek_Analysis/pull/555) | abhimehro | PASS | MERGEABLE | 2 | 🧹 [Support multi-root workspaces for Copilot] |
| Seatek_Analysis | [554](https://github.com/abhimehro/Seatek_Analysis/pull/554) | abhimehro | PASS | CONFLICTING | 2 | 🧪 Add comprehensive unit tests for warn_on_default |
| Seatek_Analysis | [552](https://github.com/abhimehro/Seatek_Analysis/pull/552) | abhimehro | PASS | CONFLICTING | 2 | 🔒 Fix potential command injection in run_shell_command |
| ctrld-sync | [1089](https://github.com/abhimehro/ctrld-sync/pull/1089) | abhimehro | PASS | MERGEABLE | 6 | ⚡ Bolt: Optimize domain allowlist checking |
| ctrld-sync | [1088](https://github.com/abhimehro/ctrld-sync/pull/1088) | abhimehro | FAIL | MERGEABLE | 21 | refactor: extract helpers out of main.py into focused modules |
| ctrld-sync | [1087](https://github.com/abhimehro/ctrld-sync/pull/1087) | abhimehro | PASS | MERGEABLE | 1 | ⚡ Bolt: Optimize domain blocklist checking with str.find() |
| ctrld-sync | [1086](https://github.com/abhimehro/ctrld-sync/pull/1086) | abhimehro | PASS | MERGEABLE | 5 | style: apply ruff formatting to test files |
| ctrld-sync | [1083](https://github.com/abhimehro/ctrld-sync/pull/1083) | abhimehro | PASS | MERGEABLE | 1 | 🎨 Palette: Add Partial status for batch rule pushes |
| ctrld-sync | [1081](https://github.com/abhimehro/ctrld-sync/pull/1081) | app/cursor | FAIL | MERGEABLE | 10 | chore(repo-health): remove scratch files and align CI/docs |
| email-security-pipeline | [1394](https://github.com/abhimehro/email-security-pipeline/pull/1394) | abhimehro | PASS | MERGEABLE | 10 | refactor(repo-health): split media_analyzer and alert_system god modul |
| personal-config | [1854](https://github.com/abhimehro/personal-config/pull/1854) | abhimehro | PASS | MERGEABLE | 2 | ⚡ Bolt: [performance improvement] Pre-compile regex for ready PR extra |
| personal-config | [1853](https://github.com/abhimehro/personal-config/pull/1853) | abhimehro | PASS | MERGEABLE | 2 | ⚡ Bolt: Optimize PR extraction with pre-compiled regex |
| personal-config | [1852](https://github.com/abhimehro/personal-config/pull/1852) | abhimehro | PASS | MERGEABLE | 15 | [repo-health] Consolidate or document maintenance orchestrator wrapper |
| personal-config | [1850](https://github.com/abhimehro/personal-config/pull/1850) | abhimehro | PASS | MERGEABLE | 1 | chore(actions): consolidate workflow automation |
| personal-config | [1848](https://github.com/abhimehro/personal-config/pull/1848) | abhimehro | PASS | MERGEABLE | 2 | Wire CLI tooling bootstrap into setup.sh (stack layer 3) |
| personal-config | [1847](https://github.com/abhimehro/personal-config/pull/1847) | abhimehro | PASS | MERGEABLE | 1 | Add idempotent gh extensions installer (stack layer 2) |
| personal-config | [1846](https://github.com/abhimehro/personal-config/pull/1846) | abhimehro | PASS | MERGEABLE | 1 | Add macos/Brewfile with gh CLI dependency (stack layer 1) |
| personal-config | [1844](https://github.com/abhimehro/personal-config/pull/1844) | abhimehro | PASS | MERGEABLE | 1 | Add minimal nvim starter config (stack layer 3) |
| personal-config | [1843](https://github.com/abhimehro/personal-config/pull/1843) | abhimehro | PASS | MERGEABLE | 1 | Add minimal git starter config (stack layer 2) |
| personal-config | [1842](https://github.com/abhimehro/personal-config/pull/1842) | abhimehro | PASS | MERGEABLE | 1 | Add minimal zsh starter config (stack layer 1) |
| personal-config | [1841](https://github.com/abhimehro/personal-config/pull/1841) | abhimehro | PASS | MERGEABLE | 2 | 🛡️ Sentinel: [MEDIUM] Add timeout and auth env to subprocess in get_pr |
| personal-config | [1840](https://github.com/abhimehro/personal-config/pull/1840) | abhimehro | PASS | CONFLICTING | 2 | 🎨 Palette: Add skip-link and semantic HTML to Media Server |
| personal-config | [1839](https://github.com/abhimehro/personal-config/pull/1839) | abhimehro | PASS | MERGEABLE | 0 | chore(qa): Daily Agentic Review |
| personal-config | [1835](https://github.com/abhimehro/personal-config/pull/1835) | abhimehro | PASS | CONFLICTING | 2 | 🎨 Palette: Add skip-to-content link and main landmark |
| personal-config | [1831](https://github.com/abhimehro/personal-config/pull/1831) | abhimehro | PASS | MERGEABLE | 2 | ⚡ Bolt: Replace .setdefault with defaultdict(list) inside loops |
| personal-config | [1830](https://github.com/abhimehro/personal-config/pull/1830) | abhimehro | PASS | CONFLICTING | 11 | ⚡ Bolt: [performance improvement] optimize ready PR extraction using r |
| personal-config | [1826](https://github.com/abhimehro/personal-config/pull/1826) | abhimehro | PASS | MERGEABLE | 3 | ⚡ Bolt Optimization: Inline substring keyword matching |
| personal-config | [1825](https://github.com/abhimehro/personal-config/pull/1825) | abhimehro | PASS | MERGEABLE | 4 | ⚡ [Performance] Replace synchronous subprocess pool with asyncio |
| personal-config | [1824](https://github.com/abhimehro/personal-config/pull/1824) | abhimehro | PASS | CONFLICTING | 2 | ⚡ Limit string split in parse_inventory.py |
| personal-config | [1823](https://github.com/abhimehro/personal-config/pull/1823) | abhimehro | PASS | CONFLICTING | 2 | ⚡ perf: optimize env parsing |
| personal-config | [1822](https://github.com/abhimehro/personal-config/pull/1822) | abhimehro | PASS | MERGEABLE | 2 | 🛡️ Sentinel: [HIGH] Fix Insecure CORS Policy |
| personal-config | [1818](https://github.com/abhimehro/personal-config/pull/1818) | abhimehro | PASS | MERGEABLE | 2 | ⚡ [performance] Optimize PR extraction substring search |
| repoprompt-ce | [162](https://github.com/abhimehro/repoprompt-ce/pull/162) | abhimehro | PASS | MERGEABLE | 2 | ⚡ Bolt: Extract ISO8601DateFormatter to static property in Changelog |
| repoprompt-ce | [161](https://github.com/abhimehro/repoprompt-ce/pull/161) | abhimehro | FAIL | MERGEABLE | 369 | 🎨 Palette: Add accessibility labels and hover tooltips to code block c |
| repoprompt-ce | [159](https://github.com/abhimehro/repoprompt-ce/pull/159) | app/cursor | FAIL | MERGEABLE | 357 | fix(ci): restore Style/RC health after merge-marker and checksum drift |
| repoprompt-ce | [158](https://github.com/abhimehro/repoprompt-ce/pull/158) | abhimehro | FAIL | MERGEABLE | 395 | 🛡️ Sentinel: [CRITICAL/HIGH] Fix TOCTOU vulnerability in file creation |
| repoprompt-ce | [157](https://github.com/abhimehro/repoprompt-ce/pull/157) | abhimehro | FAIL | MERGEABLE | 364 | perf(swift): micro-opts salvaging #146/#149/#150 |
| repoprompt-ce | [156](https://github.com/abhimehro/repoprompt-ce/pull/156) | abhimehro | FAIL | MERGEABLE | 396 | ⚡ Bolt: Extract DateFormatter to static properties |
| repoprompt-ce | [152](https://github.com/abhimehro/repoprompt-ce/pull/152) | abhimehro | FAIL | MERGEABLE | 17 | 🧹 [FSEvents] Migrate debug logging to OSLog |
| repoprompt-ce | [148](https://github.com/abhimehro/repoprompt-ce/pull/148) | abhimehro | FAIL | MERGEABLE | 17 | Validate ChatPreset model reference against ModelPresetsManager |
| repoprompt-ce | [147](https://github.com/abhimehro/repoprompt-ce/pull/147) | abhimehro | PASS | MERGEABLE | 49 | 🧹 [Code Health] Remove commented out print statements in PromptViewMod |
| repoprompt-ce | [144](https://github.com/abhimehro/repoprompt-ce/pull/144) | abhimehro | PASS | MERGEABLE | 204 | 🎨 Palette: [UX improvement] Add missing accessibility labels and toolt |
| series_correction_project_updated | [337](https://github.com/abhimehro/series_correction_project_updated/pull/337) | abhimehro | PASS | MERGEABLE | 3 | ⚡ Bolt: Remove redundant NaN masking before np.median |
| series_correction_project_updated | [336](https://github.com/abhimehro/series_correction_project_updated/pull/336) | abhimehro | FAIL | CONFLICTING | 12 | 🧹 Fix redundant exceptions and silent failures |
| series_correction_project_updated | [331](https://github.com/abhimehro/series_correction_project_updated/pull/331) | abhimehro | PASS | MERGEABLE | 1 | 🧪 Add fallback test for parse_large_json |
| series_correction_project_updated | [326](https://github.com/abhimehro/series_correction_project_updated/pull/326) | abhimehro | PASS | MERGEABLE | 1 | ⚡ [Performance] Avoid heavy DataFrame instantiation in exception handl |
| series_correction_project_updated | [323](https://github.com/abhimehro/series_correction_project_updated/pull/323) | abhimehro | PASS | MERGEABLE | 1 | ⚡ Fix memory leak and infinite loops in JSON parsing |
| series_correction_project_updated | [322](https://github.com/abhimehro/series_correction_project_updated/pull/322) | abhimehro | FAIL | CONFLICTING | 20 | ⚡ Optimize config dict creation in batch fallback |
| series_correction_project_updated | [321](https://github.com/abhimehro/series_correction_project_updated/pull/321) | abhimehro | PASS | MERGEABLE | 2 | 🧹 [code health improvement] Flatten complex _get_data_directory logic |
