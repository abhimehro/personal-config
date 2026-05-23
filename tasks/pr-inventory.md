# PR Inventory — 2026-05-23

**Session:** Cursor automation cron (`0 13 * * *`)  
**Mode:** `review-and-merge`  
**Preflight:** PASS (6/6 repos)  
**Stale threshold:** 30 days

## Summary

| Metric | Count |
| --- | ---: |
| Repos in scope | 6 |
| In-scope open PRs (start) | 25 |
| In-scope open PRs (end) | ~18 |
| Squash-merged this session | 10 |
| Closed (duplicate/superseded) | 2 |

## Inventory (start of session)

| Repo | PR | Author | Category | CI | Conflicts | Age (d) | Files | Notes |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- |
| personal-config | 1026 | abhimehro (Jules QA) | CI/INFRA | GREEN | MERGEABLE | 0 | 0 | Zero-diff Daily QA |
| personal-config | 1025 | abhimehro (Bolt) | PERFORMANCE | GREEN | MERGEABLE | 0 | 2 | `title.lower()` in `run_merges` |
| personal-config | 1023 | abhimehro (Sentinel) | SECURITY | GREEN | MERGEABLE | 0 | 21 | AppleScript injection CWE-74 |
| ctrld-sync | 837 | abhimehro (Bolt) | PERFORMANCE | benchmark FAIL | MERGEABLE | 0 | 1 | HTTP `chunk_size` streaming |
| ctrld-sync | 835 | abhimehro (Sentinel) | SECURITY | benchmark FAIL | MERGEABLE | 0 | 2 | Log injection via HTTPStatusError |
| ctrld-sync | 789 | abhimehro (Jules) | REFACTOR | mypy FAIL | MERGEABLE | 8 | 1 | `print_plan_details` |
| email-security-pipeline | 897 | abhimehro (Bolt) | PERFORMANCE | greeting FAIL | MERGEABLE | 0 | 3 | Duplicate of #896 |
| email-security-pipeline | 896 | abhimehro (Bolt) | PERFORMANCE | GREEN | MERGEABLE | 0 | 3 | `time.monotonic()` uptime |
| email-security-pipeline | 894 | abhimehro (Palette) | FEATURE | CodeScene FAIL | MERGEABLE | 0 | 1 | Draft salvage #867 |
| email-security-pipeline | 844 | abhimehro (Jules) | REFACTOR | CodeScene FAIL | MERGEABLE | 8 | 1 | Deepfake indicators |
| email-security-pipeline | 842 | abhimehro (Bolt) | PERFORMANCE | CodeScene FAIL | MERGEABLE | 8 | 5 | Spam URL cache batch |
| email-security-pipeline | 841 | abhimehro (Bolt) | PERFORMANCE | GREEN | CONFLICTING | 8 | 2 | media_analyzer dict get |
| email-security-pipeline | 807 | abhimehro (Bolt) | PERFORMANCE | GREEN | CONFLICTING | 11 | 2 | IMAP batch tuning |
| Seatek_Analysis | 198–190 | abhimehro (salvage) | PERFORMANCE | GREEN | CONFLICTING | 4 | 1–3 | Salvage batch1 tail |
| Seatek_Analysis | 172 | abhimehro (Bolt) | REFACTOR | CodeScene FAIL | MERGEABLE | 9 | 2 | `get_repo_info` dummy logic |
| Hydrograph_Versus_Seatek_Sensors_Project | 199 | abhimehro (Bolt) | PERFORMANCE | GREEN | MERGEABLE | 0 | 4 | `dict(zip())` vs set_index |
| series_correction_project_updated | 59 | abhimehro (Bolt) | PERFORMANCE | GREEN | MERGEABLE | 0 | 2 | Vectorize outlier loop |
| series_correction_project_updated | 58 | abhimehro (Sentinel) | SECURITY | CodeScene FAIL | MERGEABLE | 0 | 3 | Exception leakage (clean) |
| series_correction_project_updated | 55 | abhimehro (Sentinel) | SECURITY | CodeScene FAIL | MERGEABLE | 1 | 9 | Scratch `.diff` artifacts |

## Post-session open (in-scope, not merged)

| Repo | PR | Disposition | Reason |
| --- | ---: | --- | --- |
| personal-config | 1021, 1020 | DEFER | Draft salvage; 402 files; CONFLICTING |
| personal-config | 985 | DEFER | CONFLICTING; CodeScene fail |
| ctrld-sync | 837, 835 | ESCALATE | Required `benchmark` failing |
| ctrld-sync | 815, 789 | DEFER | CONFLICTING / mypy fail |
| email-security-pipeline | 894, 844, 842 | DEFER | CodeScene / draft salvage |
| email-security-pipeline | 841, 807 | DEFER | CONFLICTING |
| Seatek_Analysis | 204 | DEFER | Draft salvage #188 |
| Seatek_Analysis | 198–190 | DEFER | CONFLICTING salvage tail |

## Executed merges

| Repo | PR | Title (short) |
| --- | ---: | --- |
| personal-config | 1026 | Jules Daily QA (zero-diff) |
| personal-config | 1025 | Bolt: `title.lower()` in run_merges |
| personal-config | 1023 | Sentinel: AppleScript injection fix |
| email-security-pipeline | 896 | Bolt: monotonic uptime |
| Hydrograph_Versus_Seatek_Sensors_Project | 199 | Bolt: dict(zip()) optimization |
| series_correction_project_updated | 59 | Bolt: vectorize outlier detection |
| series_correction_project_updated | 58 | Sentinel: exception leakage |
| Seatek_Analysis | 172 | Replace dummy get_repo_info |
| ctrld-sync | 821 | Rate-limit header nesting |
| ctrld-sync | 818 | `_retry_request` readability |

## Closed without merge

| Repo | PR | Reason |
| --- | ---: | --- |
| email-security-pipeline | 897 | Duplicate of #896 |
| series_correction_project_updated | 55 | Superseded by #58 (junk `.diff` files) |
