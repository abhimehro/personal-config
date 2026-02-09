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

## 2026-01-24 - Bash Built-ins vs External Commands
**Learning:** In frequently executed monitoring scripts, replacing external command pipelines (like `basename | sed` or `cmd | wc -l`) with Bash parameter expansion and built-in tests (e.g., `${var##*/}`, `[[ -n $var ]]`) significantly reduces process forking overhead.
**Action:** Always prefer Bash built-ins for string manipulation and emptiness checks over piping to external utilities like `sed`, `awk`, or `wc`.

## 2026-02-15 - Minimizing Service Downtime during Handover
**Learning:** When stopping a critical network service (like a DNS proxy) that the OS depends on, the order of operations matters significantly for perceived downtime. Stopping the service first leaves the OS querying a dead port until the fallback configuration is applied.
**Action:** Always restore the fallback network configuration (e.g., reset DNS to DHCP) *before* stopping the service that was handling the traffic. This ensures continuity of service during the shutdown process.

## 2026-02-08 - Robust parsing of network interface blocks
**Learning:** Using `grep -A` to parse network interface blocks (like `ifconfig`) is fragile because the number of lines per interface varies. It can also lead to false positives if it bleeds into the next interface definition.
**Action:** Use state-machine logic in `awk` (e.g. `/^iface/ {s=1} s && /prop/ {match} /^[^ \t]/ {s=0}`) to reliably parse blocks and avoid process overhead from multiple pipes.

## 2026-02-18 - Small File Parsing with Bash vs Grep
**Learning:** For small configuration files (like TOML/INI), a pure Bash `while read` loop with regex matching is faster than `grep | sed` pipelines because it avoids forking external processes. It also allows for more flexible parsing logic (e.g. handling mixed quote styles) without complex sed expressions.
**Action:** Parse small, structured files using Bash loops and regex/parameter expansion instead of external tools when performance is a concern.

## 2026-02-03 - Service Startup Polling Latency
**Learning:** Polling a service startup using `dig` (or application-level tools) creates significant latency because the tool waits for a timeout (often 1s+) if the port is closed. Using a fast TCP port check (e.g., `/dev/tcp` or `nc -z`) allows catching the "port open" event immediately, reducing wait times significantly (e.g., from ~6s to ~2s).
**Action:** Always wait for the TCP port to be open using a low-timeout check loop before verifying the application-level protocol (HTTP/DNS).

## 2026-05-23 - Service Verification Performance Trade-offs
**Learning:** `lsof` on macOS is extremely slow (seconds) for checking port bindings. For high-frequency verification scripts, combining `pgrep` (process exists) with functional tests (e.g., `dig`) is a valid performance optimization, even if it theoretically sacrifices the strict "process owns port" check.
**Action:** When optimizing service verifiers, replace `lsof` with `pgrep` + functional checks, documenting the "hijack" risk trade-off.
