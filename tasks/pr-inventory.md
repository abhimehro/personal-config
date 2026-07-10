# PR Inventory — 2026-07-10

**Session:** Cron Phase 1 `0 13 * * *`  
**Agent branch:** `cursor-agent/automated-pr-workflow-b96a`  
**Mode:** review-and-merge  
**Preflight:** PASS 6/6 configured repos (+ repoprompt-ce scanned ad hoc)

## Summary

| Metric | Count |
|--------|------:|
| Repos scanned | 7 |
| Total open PRs | 27 |
| In-scope bot/automation PRs at start | 27 |
| In-scope at end | 8 |

## In-scope open at session start (27)

| Repo | # | Author | Age | CI | Mergeable | Branch | Title |
|------|--:|--------|----:|:---:|-----------|--------|-------|
| Hydrograph | 337 | abhimehro | 0d | GREEN | MERGEABLE | jules-qa-review-* | QA: Fix pre-commit CI failures |
| Seatek | 438 | abhimehro | 0d | GREEN | MERGEABLE | daily-qa-review-* | Jules Daily QA — All Clear |
| Seatek | 439 | abhimehro | 0d | GREEN | MERGEABLE | sentinel/bandit-* | Sentinel: bandit pre-commit |
| ctrld-sync | 990 | abhimehro | 4d | GREEN | MERGEABLE | fix/ssrf-domain-allowlist-* | SSRF domain allowlist |
| ctrld-sync | 997 | abhimehro | 1d | GREEN | MERGEABLE | palette-fix-summary-* | Palette: CLI table alignment |
| esp | 1245 | abhimehro | 0d | GREEN | MERGEABLE | palette-terminal-ux-* | Palette: terminal validation UX |
| esp | 1247 | dependabot | 0d | GREEN | MERGEABLE | dependabot/github_actions/actions/labeler-6.2.0 | bump actions/labeler |
| esp | 1248 | abhimehro | 0d | GREEN | MERGEABLE | main-* | Daily QA — Repository Healthy |
| pc | 1548 | cursor | 1d | GREEN | CONFLICTING | cursor-agent/pr-salvage-* | docs salvage 2026-07-08 |
| pc | 1557 | cursor | 0d | GREEN | CONFLICTING | cursor-agent/automated-pr-workflow-a965 | docs review 2026-07-09 |
| pc | 1558 | abhimehro | 0d | GREEN | MERGEABLE | palette-semantic-metrics-* | Palette: semantic metric cards |
| pc | 1559 | abhimehro | 0d | GREEN | MERGEABLE | cursor-agent/salvage-pc-1547-* | feat(a11y): empty state salvage |
| pc | 1560 | cursor | 0d | GREEN | CONFLICTING | cursor-agent/pr-salvage-* | docs salvage 2026-07-09 |
| pc | 1562 | abhimehro | 0d | GREEN | MERGEABLE | qa-review-complete-* | QA review complete |
| pc | 1563 | abhimehro | 0d | GREEN | MERGEABLE | palette/add-semantic-html-* | Palette: semantic HTML landmarks |
| pc | 1564 | dependabot | 0d | GREEN | MERGEABLE | dependabot/.../trufflehog-3.95.9 | bump trufflehog |
| pc | 1565 | dependabot | 0d | GREEN | MERGEABLE | dependabot/.../labeler-6.2.0 | bump actions/labeler |
| pc | 1567 | abhimehro | 0d | GREEN | MERGEABLE | bolt-optimize-date-parsing-* | Bolt: date parsing short-circuit |
| pc | 1568 | abhimehro | 0d | GREEN | MERGEABLE | bolt-threadpoolexecutor-* | Bolt: ThreadPoolExecutor latency |
| rpce | 102 | dependabot | 3d | GREEN | MERGEABLE | dependabot/github_actions/actions/cache-6 | bump actions/cache |
| rpce | 105 | abhimehro | 2d | GREEN | MERGEABLE | sentinel-fix-urlsession-* | Sentinel: URLSession config |
| rpce | 108 | dependabot | 1d | GREEN | MERGEABLE | dependabot/.../pr-refactoring-agent | bump codescene agent |
| rpce | 110 | abhimehro | 1d | GREEN | MERGEABLE | jules-palette-a11y-* | Palette: session action a11y |
| rpce | 112 | abhimehro | 0d | GREEN | MERGEABLE | fix/ephemeral-urlsession-* | Sentinel: token leak fix |
| rpce | 114 | abhimehro | 0d | GREEN | MERGEABLE | bolt-dateformatter-opt-* | Bolt: DateFormatter extraction |
| sc | 206 | abhimehro | 1d | GREEN | MERGEABLE | cursor-agent/salvage-sc-204-* | perf: rolling_median salvage |
| sc | 210 | abhimehro | 0d | GREEN | MERGEABLE | cursor-agent/salvage-sc-205-* | fix(security): CLI exception sanitize |

## In-scope open at session end (8)

| Repo | # | Disposition | Blocker |
|------|--:|-------------|---------|
| ctrld-sync | 990 | ESCALATE | SSRF allowlist trust boundary |
| Seatek | 439 | ESCALATE | Bandit pre-commit tooling |
| pc | 1559 | DEFER | Merge conflicts with main |
| pc | 1563 | DEFER | Merge conflicts with main |
| pc | 1568 | DEFER | Merge conflicts with main |
| rpce | 105 | ESCALATE | URLSession hardening |
| rpce | 112 | ESCALATE | Ephemeral URLSession / token leak |
| sc | 210 | ESCALATE | CLI exception sanitization |

## Repos at zero in-scope open (EOD)

- email-security-pipeline
- Hydrograph_Versus_Seatek_Sensors_Project
