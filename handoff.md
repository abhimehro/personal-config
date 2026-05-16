========== ELIR ==========
PURPOSE: Optimize the `categorize_ready.py` script by parallelizing independent network API calls (`gh pr view`) using `ThreadPoolExecutor`.
SECURITY: The `run_gh` sub-processes execute safely with strict input isolation and bounded worker counts limit memory consumption.
FAILS IF: GitHub API quota runs out due to parallel requests.
VERIFY: Ensure script executes successfully and output order of categorized PRs remains identical (enabled via `executor.map`).
MAINTAIN: Be aware of GitHub CLI rate-limits during concurrent requests if queue exceeds ~100 PRs.
