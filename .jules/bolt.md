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

## 2025-12-30 - Parallel Hardware Queries
**Learning:** macOS tools like `networksetup` are often blocking and slow (several hundred milliseconds). When multiple independent properties (e.g., DNS and IPv6 status) need to be queried from the same or different hardware interfaces, executing them in parallel subshells significantly improves responsiveness.
**Action:** Group independent blocking hardware queries and run them in parallel using `command &` and `wait`, capturing output to temporary files if necessary.

## 2026-01-19 - Arithmetic Evaluation in set -e Scripts
**Learning:** In scripts with `set -e`, using `((i++))` where `i` starts at 0 causes the script to exit immediately because the arithmetic evaluation result is 0 (which Bash treats as a "false" exit code 1), even though the increment happens.
**Action:** Use `((i+=1))` or `i=$((i+1))` instead of `((i++))` when the variable might be zero, or append `|| true` to the arithmetic command.

## 2026-01-19 - Safe Parallel Loop Execution
**Learning:** When using `while read ... done < <(...)` to feed a loop that spawns background jobs, blindly trusting the loop's stdin/stdout context can lead to race conditions or "hanging" behavior if the background jobs inherit the file descriptors.
**Action:** Read the input into an array first (synchronously), then iterate over the array to spawn background jobs. This isolates the data collection from the parallel execution context.

## 2026-01-20 - Shell Script Error Checking Fragility
**Learning:** Relying on `grep` to match specific error strings in a pipeline (e.g., `cmd | grep "fail"`) creates a "success by default" trap. If `cmd` fails with an unexpected error message that isn't in the grep list, the check fails (grep returns 1), leading the script to assume success.
**Action:** Always check the command's exit code first. Only parse the output for specific reasons if the exit code indicates failure, and ensure there is a catch-all `else` block for unexpected errors.

## 2026-02-15 - Grep Memory Optimization and Regex Precision
**Learning:** Reading a file into a variable (`$(grep ...)`) just to pipe it into another `grep` is inefficient (memory usage, subshell overhead) and error-prone with regex. A single `grep` with a precise Extended Regex (e.g., `type = 'doh[^3]`) is faster and safer.
**Action:** Replace `var=$(grep ...); if echo "$var" | grep ...` patterns with direct `if grep -E "pattern" file; then ...`.
