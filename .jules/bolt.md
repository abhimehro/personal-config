## 2024-10-27 - [Idempotent Service Switching]
**Learning:** Shell scripts managing services should be idempotent. Restarting a service when the desired configuration is already active is wasteful (latency, CPU, potential downtime).
**Action:** Always check `pgrep` and current configuration state (e.g., via symlink targets or grep) before initiating a stop/start cycle.

## 2025-12-28 - Shell Script Performance Optimization
**Learning:** In Bash scripts, spawning subshells (e.g., `$(date)`) and pipelines (e.g., `| tr`) inside frequently called functions (like logging) creates significant overhead. Using Bash built-ins like `printf %(...)T` and parameter expansion `${var##*/}` is much faster. Also, be careful with `set -e` and functions that return false (like conditional checks returning non-zero) - always ensure they return true or handle the exit code.
**Action:** When optimizing shell scripts, prioritize replacing external command calls with built-ins inside loops or hot paths.