# PR Triage — 2026-06-10

**Session:** review-and-merge  
**Stale threshold:** 30 days

## Classification

| PR | Category | Gates | Disposition | Rationale |
| --- | --- | --- | --- | --- |
| ESP #1062 | SECURITY | CI ✓ Sec ✓ Qual ✓ | MERGE | Sanitizes malicious paths in zip/tar warning logs |
| PC #1199 | SECURITY | CI ✓ Sec ✓ Qual ✓ | MERGE | Fixes AppleScript injection via argv-based osascript |
| ESP #1064 | PERFORMANCE | CI ✓ Sec ✓ Qual ✓ | MERGE | Hoists image count in spam analyzer; no logic risk |
| ESP #1065 | CI/INFRA | CI ✓ Sec ✓ Qual ✓ | MERGE | Daily QA notes; docs-only |
| ctrld-sync #881 | PERFORMANCE | CI ✗ Sec ✓ Qual ✓ | DEFER | Benchmark proves list comprehension is slower |
| PC #1201 | CI/INFRA | CI ✓ Sec ✓ Qual ✓ | ESCALATE | Third-party action pin change — supply-chain trust boundary |
| SA #261 | PERFORMANCE | CI ✓ Sec ✗ Qual ✓ | ESCALATE | Removes `read_file_safe` path traversal + OOM limits |

## Duplicate / overlap analysis

- **ESP #1062 vs #1064:** No file overlap (`media_analyzer.py` vs `spam_analyzer.py`). Safe to merge both.
- **PC #1201 vs prior #1193:** Both touch `refactoring-agent.yml` pin; #1193 was merged/closed in prior sessions — #1201 is a new pin target (`v1.0.1`).
- **SA #261 vs #247:** Salvage of closed perf PR; intent preserved but security helpers incorrectly dropped.

## Stale PR check

| PR | Age | Activity | Stale? |
| --- | ---: | --- | --- |
| SA #261 | 7d | CI refreshed 2026-06-09 | No (< 30d) |
| All others | ≤1d | Active today | No |

## Merge order executed

1. ESP #1062 (SECURITY)
2. PC #1199 (SECURITY)
3. ESP #1064 (PERFORMANCE)
4. ESP #1065 (CI/INFRA) — retried after base-branch-modified
