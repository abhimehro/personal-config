## 2025-05-20 - Parallel Maintenance Script Execution
**Learning:** Maintenance scripts that perform network operations (like brew/npm updates) or independent system checks can be safely parallelized to significantly reduce total execution time, provided they don't lock the same resources (e.g. brew vs npm locks are separate).
**Action:** When optimizing orchestration scripts, look for independent blocking tasks (especially network I/O) and wrap them in background subshells with a wait barrier.
