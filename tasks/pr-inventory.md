# PR Inventory — 2026-07-23 (Phase 1 cron)

Preflight: **PASS 7/7**. Mode: `review-and-merge`. Stale threshold: 30d.
Branch: `cursor-agent/pr-workflow-automation-f2ab`.

In-scope: bot authors + automation-driven human PRs (Jules/Bolt/Palette/Sentinel/Dependabot/Cursor salvage/QA).

| Repo | PR | Author | Category | CI | Conflicts | Age | Draft | Files | Title |
|------|-----|--------|----------|----|-----------|-----|-------|-------|-------|
| personal-config | 1753 | dependabot | DEPENDENCY | OK | MERGEABLE | 0 | N | 1 | chore(deps): bump github/codeql-action 4.37.2→4.37.3 |
| personal-config | 1752 | abhimehro | UI | OK | MERGEABLE | 0 | N | 2 | 🎨 Palette: accessible data tables |
| personal-config | 1751 | abhimehro | CI/INFRA | OK | MERGEABLE | 0 | N | 0 | QA Check (zero-diff) |
| personal-config | 1749 | app/cursor | FEATURE | OK | MERGEABLE | 0 | Y | 6 | docs(pr-salvage): Phase 2 session 2026-07-22 |
| personal-config | 1748 | abhimehro | FEATURE | OK | MERGEABLE | 0 | Y | 7 | fix(visual-recap): salvage #1733 |
| personal-config | 1744 | abhimehro | CI/INFRA | OK | CONFLICTING | 1 | N | 13 | chore(actions): consolidate workflow automation |
| personal-config | 1721 | abhimehro | PERFORMANCE | OK | CONFLICTING | 2 | N | 2 | ⚡ Bolt: cache env vars in detect_duplicates.py |
| ctrld-sync | — | — | — | — | — | — | — | — | **no open PRs** |
| email-security-pipeline | 1344 | abhimehro | PERFORMANCE | OK | MERGEABLE | 0 | N | 2 | ⚡ Bolt: fast-path URL extraction regex |
| email-security-pipeline | 1342 | abhimehro | REFACTOR | OK | MERGEABLE | 0 | Y | 1 | refactor(ingestion): IMAPClient config (salvage #1330) |
| email-security-pipeline | 1341 | abhimehro | PERFORMANCE | OK | MERGEABLE | 0 | Y | 1 | perf(ingestion): extend+comprehension (salvage #1335) |
| email-security-pipeline | 1328 | abhimehro | SECURITY | OK | MERGEABLE | 2 | N | 1 | 🔒 Fix TOCTOU in config permission setup |
| email-security-pipeline | 1327 | abhimehro | PERFORMANCE | FAIL CS | CONFLICTING | 2 | N | 21 | ⚡ Bolt: Optimize SPF substring checks |
| email-security-pipeline | 1324 | abhimehro | SECURITY | OK | MERGEABLE | 2 | N | 2 | ⚡ Bolt: Optimize _check_auth_results |
| email-security-pipeline | 1320 | abhimehro | REFACTOR | OK | MERGEABLE | 2 | N | 2 | 🧹 Use validate_subject_length |
| email-security-pipeline | 1319 | abhimehro | PERFORMANCE | OK | MERGEABLE | 2 | N | 1 | ⚡ Bolt: Optimize gh_token_cli writes |
| Seatek_Analysis | 518 | abhimehro | SECURITY | OK | MERGEABLE | 0 | N | 2 | 🛡️ Sentinel: env denylist in subprocess wrappers |
| Seatek_Analysis | 517 | abhimehro | CI/INFRA | OK | MERGEABLE | 0 | N | 0 | Jules Daily QA — no issues (zero-diff) |
| Seatek_Analysis | 515 | dependabot | DEPENDENCY | OK | MERGEABLE | 0 | N | 1 | matplotlib floor ≥3.8→≥3.11.1 |
| Seatek_Analysis | 514 | dependabot | DEPENDENCY | OK | MERGEABLE | 0 | N | 1 | pandas 2.x→3.x major |
| Seatek_Analysis | 511 | abhimehro | REFACTOR | FAIL Trunk | MERGEABLE | 1 | N | 5 | path-traversal / IO refactor |
| Seatek_Analysis | 507 | abhimehro | SECURITY | OK | MERGEABLE | 1 | N | 2 | 🛡️ Sentinel: subprocess env exfiltration |
| Hydrograph… | 404 | abhimehro | PERFORMANCE | OK | MERGEABLE | 0 | N | 3 | ⚡ Bolt: dict instantiation in validation |
| Hydrograph… | 402 | dependabot | DEPENDENCY | OK | MERGEABLE | 0 | N | 1 | pre-commit upper bound →&lt;5 |
| series_correction… | 286 | dependabot | DEPENDENCY | OK | MERGEABLE | 0 | N | 1 | ruby/setup-ruby SHA pin bump |
| series_correction… | 285 | abhimehro | SECURITY | FAIL CS | MERGEABLE | 0 | N | 1 | 🔒 memory leak dummy_todos.py |
| series_correction… | 276 | abhimehro | SECURITY | OK | MERGEABLE | 2 | N | 2 | 🔒 DoS infinite loop dummy_todos |
| series_correction… | 275 | abhimehro | SECURITY | OK | CONFLICTING | 2 | N | 4 | 🔒 secure auth + DoS JSON |
| series_correction… | 268 | abhimehro | REFACTOR | OK | MERGEABLE | 2 | N | 1 | 🧹 infinite loop json parsing |
| repoprompt-ce | 138 | abhimehro | UI | OK | MERGEABLE | 0 | N | 1 | 🎨 Palette: a11y labels on icon buttons |
| repoprompt-ce | 127 | dependabot | DEPENDENCY | OK | MERGEABLE | 6 | N | 1 | upload-artifact 4→7 tip major |
| repoprompt-ce | 126 | dependabot | DEPENDENCY | OK | MERGEABLE | 6 | N | 1 | download-artifact 4→8 tip major |

**Total in-scope: 31** (ctrld-sync empty).
