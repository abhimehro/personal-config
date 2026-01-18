## 2024-10-27 - [Idempotent Service Switching]
**Learning:** Shell scripts managing services should be idempotent. Restarting a service when the desired configuration is already active is wasteful (latency, CPU, potential downtime).
**Action:** Always check `pgrep` and current configuration state (e.g., via symlink targets or grep) before initiating a stop/start cycle.

## 2025-05-20 - Parallel Maintenance Script Execution
**Learning:** Maintenance scripts that perform network operations (like brew/npm updates) or independent system checks can be safely parallelized to significantly reduce total execution time, provided they don't lock the same resources (e.g. brew vs npm locks are separate).
**Action:** When optimizing orchestration scripts, look for independent blocking tasks (especially network I/O) and wrap them in background subshells with a wait barrier.

## 2025-05-21 - DNS Flapping in Network Managers
**Learning:** Resetting DNS to "Empty" (DHCP) before immediately setting it to a local resolver (127.0.0.1) causes a "DNS flap" where the OS might briefly query the router/ISP or trigger network stack reconfigurations. This creates a race condition and slows down profile switching.
**Action:** In state-switching scripts, skip the "teardown" step if the "setup" step handles cleanup and overwrites the target configuration anyway.

## 2025-12-28 - Shell Script Performance Optimization
**Learning:** In Bash scripts, spawning subshells (e.g., `$(date)`) and pipelines (e.g., `| tr`) inside frequently called functions (like logging) creates significant overhead. Using Bash built-ins like `printf %(...)T` and parameter expansion `${var##*/}` is much faster. Also, be careful with `set -e` and functions that return false (like conditional checks returning non-zero) - always ensure they return true or handle the exit code.
**Action:** When optimizing shell scripts, prioritize replacing external command calls with built-ins inside loops or hot paths.

## 2025-10-27 - State File Verification vs Service Query
**Learning:** Querying service status via CLI (e.g., `sudo ctrld status`) often incurs high overhead due to privilege escalation and process spawning. When a service is managed by a known controller that maintains state files (like symlinks), checking those files is orders of magnitude faster and doesn't require `sudo`.
**Action:** Prefer checking configuration artifacts (symlinks, pidfiles) for status reporting over invoking management binaries, especially in "status" commands.

## 2025-12-29 - Service Config Generation vs Execution
**Learning:** Some service managers (like `ctrld`) have distinct `start` (daemonize + system config) and `run` (foreground) modes. Using `start` just to generate a configuration file triggers unnecessary system-wide changes (like DNS resets) and overhead.
**Action:** Use `run` in the background (with proper cleanup) when you only need the service to perform an initialization task (like config generation) without fully activating its system integration.