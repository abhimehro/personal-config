========== ELIR ==========
PURPOSE: Removed unused `concurrent.futures` import and `ThreadPoolExecutor` usage, converting to sequential execution via `map()`.
SECURITY: Reduces attack surface slightly by relying on sequential standard library execution over thread pools.
FAILS IF: Sequential PR fetching becomes a significant performance bottleneck at scale.
VERIFY: Review PR to ensure only the import and the thread executor logic was changed.
MAINTAIN: If fetching context for many PRs takes too long in the future, concurrent fetches could be re-added via `asyncio`.
