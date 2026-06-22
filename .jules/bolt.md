## 2024-10-27 - [Idempotent Service Switching]

**Learning:** Shell scripts managing services should be idempotent. Restarting a
service when the desired configuration is already active is wasteful (latency,
CPU, potential downtime). **Action:** Always check `pgrep` and current
configuration state (e.g., via symlink targets or grep) before initiating a
stop/start cycle.

## 2025-05-20 - Parallel Maintenance Script Execution

**Learning:** Maintenance scripts that perform network operations (like brew/npm
updates) or independent system checks can be safely parallelized to
significantly reduce total execution time, provided they don't lock the same
resources (e.g. brew vs npm locks are separate). **Action:** When optimizing
orchestration scripts, look for independent blocking tasks (especially network
I/O) and wrap them in background subshells with a wait barrier.

## 2025-05-21 - DNS Flapping in Network Managers

**Learning:** Resetting DNS to "Empty" (DHCP) before immediately setting it to a
local resolver (127.0.0.1) causes a "DNS flap" where the OS might briefly query
the router/ISP or trigger network stack reconfigurations. This creates a race
condition and slows down profile switching. **Action:** In state-switching
scripts, skip the "teardown" step if the "setup" step handles cleanup and
overwrites the target configuration anyway.

## 2025-12-28 - Shell Script Performance Optimization

**Learning:** In Bash scripts, spawning subshells (e.g., `$(date)`) and
pipelines (e.g., `| tr`) inside frequently called functions (like logging)
creates significant overhead. Using Bash built-ins like `printf %(...)T` and
parameter expansion `${var##*/}` is much faster. Also, be careful with `set -e`
and functions that return false (like conditional checks returning non-zero) -
always ensure they return true or handle the exit code. **Action:** When
optimizing shell scripts, prioritize replacing external command calls with
built-ins inside loops or hot paths.

## 2025-10-27 - State File Verification vs Service Query

**Learning:** Querying service status via CLI (e.g., `sudo ctrld status`) often
incurs high overhead due to privilege escalation and process spawning. When a
service is managed by a known controller that maintains state files (like
symlinks), checking those files is orders of magnitude faster and doesn't
require `sudo`. **Action:** Prefer checking configuration artifacts (symlinks,
pidfiles) for status reporting over invoking management binaries, especially in
"status" commands.

## 2025-12-29 - Service Config Generation vs Execution

**Learning:** Some service managers (like `ctrld`) have distinct `start`
(daemonize + system config) and `run` (foreground) modes. Using `start` just to
generate a configuration file triggers unnecessary system-wide changes (like DNS
resets) and overhead. **Action:** Use `run` in the background (with proper
cleanup) when you only need the service to perform an initialization task (like
config generation) without fully activating its system integration.

## 2025-12-30 - Parallel Hardware Queries

**Learning:** macOS tools like `networksetup` are often blocking and slow
(several hundred milliseconds). When multiple independent properties (e.g., DNS
and IPv6 status) need to be queried from the same or different hardware
interfaces, executing them in parallel subshells significantly improves
responsiveness. **Action:** Group independent blocking hardware queries and run
them in parallel using `command &` and `wait`, capturing output to temporary
files if necessary.

## 2026-01-19 - Arithmetic Evaluation in set -e Scripts

**Learning:** In scripts with `set -e`, using `((i++))` where `i` starts at 0
causes the script to exit immediately because the arithmetic evaluation result
is 0 (which Bash treats as a "false" exit code 1), even though the increment
happens. **Action:** Use `((i+=1))` or `i=$((i+1))` instead of `((i++))` when
the variable might be zero, or append `|| true` to the arithmetic command.

## 2026-01-19 - Safe Parallel Loop Execution

**Learning:** When using `while read ... done < <(...)` to feed a loop that
spawns background jobs, blindly trusting the loop's stdin/stdout context can
lead to race conditions or "hanging" behavior if the background jobs inherit the
file descriptors. **Action:** Read the input into an array first
(synchronously), then iterate over the array to spawn background jobs. This
isolates the data collection from the parallel execution context.

## 2026-01-20 - Shell Script Error Checking Fragility

**Learning:** Relying on `grep` to match specific error strings in a pipeline
(e.g., `cmd | grep "fail"`) creates a "success by default" trap. If `cmd` fails
with an unexpected error message that isn't in the grep list, the check fails
(grep returns 1), leading the script to assume success. **Action:** Always check
the command's exit code first. Only parse the output for specific reasons if the
exit code indicates failure, and ensure there is a catch-all `else` block for
unexpected errors.

## 2026-01-24 - Bash Built-ins vs External Commands

**Learning:** In frequently executed monitoring scripts, replacing external
command pipelines (like `basename | sed` or `cmd | wc -l`) with Bash parameter
expansion and built-in tests (e.g., `${var##*/}`, `[[ -n $var ]]`) significantly
reduces process forking overhead. **Action:** Always prefer Bash built-ins for
string manipulation and emptiness checks over piping to external utilities like
`sed`, `awk`, or `wc`.

## 2026-02-15 - Minimizing Service Downtime during Handover

**Learning:** When stopping a critical network service (like a DNS proxy) that
the OS depends on, the order of operations matters significantly for perceived
downtime. Stopping the service first leaves the OS querying a dead port until
the fallback configuration is applied. **Action:** Always restore the fallback
network configuration (e.g., reset DNS to DHCP) _before_ stopping the service
that was handling the traffic. This ensures continuity of service during the
shutdown process.

## 2026-02-08 - Robust parsing of network interface blocks

**Learning:** Using `grep -A` to parse network interface blocks (like
`ifconfig`) is fragile because the number of lines per interface varies. It can
also lead to false positives if it bleeds into the next interface definition.
**Action:** Use state-machine logic in `awk` (e.g.
`/^iface/ {s=1} s && /prop/ {match} /^[^ \t]/ {s=0}`) to reliably parse blocks
and avoid process overhead from multiple pipes.

## 2026-02-28 - [Python List/Generator Comprehensions vs For Loops]

**Learning:** In Python data parsing scripts, replacing `for` loops with
`.append()` calls with list comprehensions provides a small but consistent
performance boost (~5-7%). Further, when doing dictionary lookups in tight
loops, using `'key' in dict` checks is more efficient than nested `.get().get()`
calls due to avoiding function overhead. **Action:** When extracting data from
large JSON arrays, default to list or set comprehensions and use explicit `in`
checks for nested dictionaries instead of `.get()` chains.

## 2026-03-05 - [Parameter Expansion vs basename]

**Learning:** Using `basename` in a subshell creates significant performance
overhead due to process spawning (e.g., `$(basename "$file")`). The built-in
shell parameter expansion `${file##*/}` avoids this overhead and is ~300x faster
in tight loops, but it does not strip trailing slashes the way `basename` does
(e.g., `/a/b/`), so inputs may need to be normalized first (for example with
`${file%/}`). **Action:** Where path inputs are normalized to not end with `/`
(or after first stripping any trailing `/` with `${var%/}`), prefer `${var##*/}`
over `$(basename "$var")` in shell scripts to improve performance and reduce
system calls.

## 2026-05-24 - Basic Auth Decoding Overhead

**Learning:** Python's `http.server` handler methods (`do_HEAD`, `do_GET`)
execute the `check_auth` logic entirely on the main thread for every incoming
HTTP request. In custom implementations (like `infuse-media-server.py` and
`alldebrid-server.py`), decoding the base64 `Authorization` header and splitting
the string (`base64.b64decode(auth_data).decode('utf-8').split(':', 1)`) on
every single request adds significant unnecessary overhead (up to a ~9x slowdown
in microbenchmarks) compared to directly comparing the base64 token. **Action:**
Always pre-compute expected static tokens (like Basic Auth base64 strings) at
server startup and use a single `secrets.compare_digest` against the incoming
request header to avoid repeated decoding and allocations on every request.

## 2026-05-24 - [Avoid N+1 Filesystem Queries in Loops]

**Learning:** In Bash scripts, using `find` inside a loop that iterates over the
results of another `find` command creates an N+1 query problem, leading to
massive overhead for large directories. We can combine checks (like `-mtime` or
`-size`) directly into the initial `find` command to avoid spawning
sub-processes and filesystem lookups. Using `while read ... done < <(find ...)`
allows us to efficiently parse results and avoid subshell variable isolation
issues. **Action:** Always combine file criteria into a single `find` query
instead of querying the filesystem again inside the loop.

## 2026-05-29 - [Path Filtering Optimization: isdisjoint vs any]

**Learning:** When filtering paths or tuples against a set of excluded strings
in Python (e.g., `any(part in EXCLUDES for part in path.parts)`), iterating with
a generator expression introduces significant overhead, especially in deep
recursive directory walks like `rglob`. Using the built-in C-level set operation
`not EXCLUDES.isdisjoint(path.parts)` is ~7x faster for hits and ~4x faster for
misses. **Action:** When checking if any element of an iterable exists in a
`set`, prefer `not your_set.isdisjoint(iterable)` over using `any()` with a
generator expression for optimal performance.

## 2026-06-12 - [os.walk vs Path.rglob Directory Pruning]

**Learning:** `Path.rglob()` always traverses the entire directory tree before
yielding results. When skipping large directories (like `node_modules` or
`.venv`), checking the path parts (e.g., `isdisjoint(path.parts)`) still
requires the OS to read all those underlying files and directories first,
resulting in massive I/O overhead. **Action:** When searching a directory tree
where large subdirectories should be entirely ignored, use `os.walk()` and
modify the `dirs` list in-place
(`dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]`). This prunes the tree
traversal early and completely bypasses the ignored directories.

## 2026-06-03 - [Path Pattern Matching Optimization]

**Learning:** When matching file paths against multiple glob patterns in Python
(e.g., `any(fnmatch.fnmatch(path, p) for p in patterns)`), iterative
`fnmatch.fnmatch` evaluation introduces significant overhead. Replacing this
with a single pre-compiled regex generated from `fnmatch.translate()` and cached
with `@functools.lru_cache` provides a ~3x performance boost on path matching,
avoiding repetitive function calls and parsing. **Action:** When filtering paths
against a static list of multiple glob patterns, compile the translated patterns
into a single combined regex instead of iterating with
`any(fnmatch.fnmatch(...))`. Be sure to explicitly use `os.path.normcase` on the
input patterns and path string to replicate the internal behavior of `fnmatch`.

## 2026-06-03 - [Avoid Redundant ISO String Parsing]

**Learning:** Passing an ISO string and parsing it with
`dt.date.fromisoformat()` repeatedly within tight loops (e.g., inside the
scoring loop for Linear issues) creates unnecessary CPU overhead. By parsing the
date once and passing the `datetime.date` object down to the utility functions,
we save ~30% parsing overhead per issue without impacting functionality.
**Action:** When a function requires a date for calculations and is called
repeatedly in a loop, parse the date outside the loop and pass the
`datetime.date` object as an argument instead of the raw string.

## 2026-04-04 - strptime vs fromisoformat overhead

**Learning:** In Python, parsing ISO-8601 timestamp strings using
`datetime.strptime` involves format string processing overhead that can be
significantly slow inside loops. `datetime.fromisoformat()` is implemented in C
and optimized for ISO strings, executing 20x-40x faster. **Action:** When
parsing standard ISO timestamps (e.g., from APIs or configuration files), use
`datetime.fromisoformat()` instead of `strptime`. For strings ending with `"Z"`
(UTC), use `.replace("Z", "+00:00")` before parsing to maintain compatibility
with Python versions older than 3.11.

## 2026-06-25 - [Cache Helper Functions to Avoid Repeated Normalization]

**Learning:** In Python automation scripts calling functions like `matches_any`
or `numeric_version` inside loops, using an `@functools.lru_cache` helper
function at the module scope caches both regex application and normalisation
overhead (e.g. `tuple()` casts and `os.path.normcase` internally), yielding ~50%
performance gains on repeated inputs compared to just caching the regex
compilation. **Action:** When repeatedly calling string matching logic inside
loop comprehensions, write a lightweight module-scoped helper decorated with
`lru_cache(maxsize=512)` that delegates to the target function to bypass
duplicate internal processing logic safely.

## 2026-06-25 - [Avoid N+1 Filesystem Queries in Find Patterns]

**Learning:** Running `find` repeatedly inside a loop over an array of filename
patterns creates an N+1 query problem, leading to massive redundant filesystem
scanning overhead. **Action:** Combine all `-name` patterns dynamically into an
array with the `-o` (OR) operator and pass them to a single `find` command.
Guard the `find` execution to ensure the pattern array isn't empty, as `find`
throws a syntax error on empty parentheses `\( \)`.

## 2026-06-25 - [macOS BSD Find Limitations]

**Learning:** macOS uses BSD `find`, which does not support the GNU-specific
`-quit` flag. Using `-quit` on macOS causes silent script failures if `stderr`
is redirected, which can break conditional logic (e.g. `grep -q .` succeeding
falsely or failing falsely). **Action:** Do not use the `-quit` flag in `find`
commands within macOS-specific scripts. If early exit behavior is needed on the
first match, use `find ... | head -n 1` or `grep -q .`.

## 2024-05-18 - Fast String Searching for PR Exclusions

**Learning:** In PR automation scripts like `detect_duplicates.py`, repeatedly
evaluating `lines[: index]` and slicing lists inside a generator expression for
exclusion filtering (`if not any(pr in l for l in lines[: index])`) introduces
O(N*M) overhead. **Action:** When filtering a list of substrings against a
prefix/slice of file lines, `"".join()` the target slice into a single string
*once\* outside the loop, and use the fast C-level `in` operator
(`pr not in pre_joined_string`). This simple hoist-and-join strategy eliminates
list slicing and Python loop overhead, yielding ~88% performance improvement on
medium-sized lists.

## 2026-06-25 - [List Comprehensions with Direct Dict Lookups]

**Learning:** In Python data parsing scripts, combining list comprehensions with
`type(dict) is dict` and direct dictionary lookups
(`"key" in dict and dict["key"] == val`) provides a ~15-20% performance boost
over using generator expressions with `isinstance()` and `.get()` calls by
avoiding function overhead. **Action:** When extracting data from large JSON
arrays based on nested conditions, prefer list comprehensions over generator
expressions and use direct `in` checks combined with `type() is dict` instead of
`.get()` and `isinstance()`.

## 2026-04-25 - Direct Dict Lookups for Adblock Rule Filtering

**Learning:** In Python data parsing scripts, replacing `.get()` calls inside
generator expressions with explicit `key in dict` + direct `dict[key]` lookups
gives a small but consistent speedup (~10-15%) when iterating over large lists
of dicts (e.g. AdGuard rule lists with thousands of entries). The win comes from
avoiding `.get()`'s default-value branching and the small per-call overhead of
method dispatch. **Action:** When extracting fields from large JSON arrays
inside a list comprehension, prefer `if "key" in d and d["key"] == val` over
`if d.get("key") == val`, and use `[ ... for d in data ]` (list comprehension)
instead of `( ... for d in data )` (generator) when the result is immediately
materialized (e.g. passed to `set.update` or returned from a function).

## 2026-03-10 - Cached Environment parsing in iterative scripts

**Learning:** Repetitive file IO (e.g., parsing `.env` files) inside helper
functions that are called in loops (like API wrappers across a large queue)
creates a massive performance bottleneck. **Action:** Use Python's
`functools.lru_cache` to cache environment or configuration file parsing that
runs repeatedly but remains static during execution.

## 2026-03-10 - [Memory Efficiency and PEP-8 in Data Extraction]

**Learning:** Using `type() is dict` violates PEP-8 conventions. Furthermore,
passing list comprehensions (e.g., `[x for x in data]`) to aggregate functions
like `set.update()` forces the entire filtered sequence into memory at once,
creating unnecessary memory spikes during large JSON extractions. **Action:**
When extracting data based on type, always use `isinstance()`. When passing
filtered sequences to aggregate functions that accept iterables (like
`.update()`), preserve memory efficiency by using generator expressions `(...)`
instead of list comprehensions `[...]`.

## 2026-05-24 - [Avoid re.match and split overhead for simple parsing]

**Learning:** Using `re.match` for simple prefix string extractions (like
`## repo/name`) is up to ~3x slower than `str.startswith()` combined with list
slicing. Similarly, breaking strings on a single character using
`str.split("=", 1)` or extracting suffix/prefix with `split("/")[-1]` introduces
unnecessary list allocation overhead. The `str.partition()` and
`str.rpartition()` methods are implemented in C and provide ~30-40% faster
string splitting without allocating new lists. **Action:** For simple string
prefix extractions, prefer `startswith` + slicing over regular expressions. When
splitting a string on a single separator, use `partition` or `rpartition`
instead of `split`.

## 2026-05-14 - [Optimize N+1 API Calls with ThreadPoolExecutor]

**Learning:** Making independent network API requests sequentially inside a loop
creates an N+1 performance bottleneck. By utilizing Python's
`concurrent.futures.ThreadPoolExecutor`, these independent IO-bound tasks can be
executed concurrently, achieving significant speedups (e.g., ~8.9x reduction in
execution time for 100ms latency simulated API requests). **Action:** Identify
loops executing sequential independent network or IO-bound operations and
refactor them using `concurrent.futures.ThreadPoolExecutor` to execute the
operations in parallel. Ensure shared state (like appending to a dictionary or
list) is handled safely outside the parallel execution or by using thread-safe
data structures.

## 2026-11-20 - [Avoid unnecessary .split() list allocation in simple string formatting]

**Learning:** When extracting substrings from a string separated by a known
delimiter inside a loop or comprehension (e.g. `pr.split()[0]`), repeatedly
calling `.split()` allocates new lists each time, causing a performance
overhead. **Action:** When you only need to split once on the first delimiter
and want to avoid unnecessary list allocation, use `str.partition()` instead of
`str.split()`. It returns a tuple directly in C and doesn't allocate an
arbitrary-length list. If doing inline formatting or transformations inside
comprehensions, prefer doing the partition/split once and binding the results
rather than repeating `.split()` multiple times on the same item.

## 2026-11-20 - [Avoid Repeated String Lowering in List Comprehensions]

**Learning:** When evaluating nested loop conditions like
`all(kw.lower() in p["title"].lower() for kw in keywords)` inside a list
comprehension, Python repeatedly evaluates `.lower()` on both the keyword and
the title for every iteration. This redundant string conversion overhead
significantly slows down list filtering. **Action:** Pre-calculate `kw.lower()`
outside the comprehension. To avoid repeatedly evaluating `p["title"].lower()`
for each keyword during the `all()` check, use a single-element tuple in a `for`
clause (e.g., `for title_lower in (p["title"].lower(),)`) to bind the value once
per item.

## 2026-11-20 - [Avoid Redundant title.lower() in Security Audits]

**Learning:** Checking a series of hardcoded substrings sequentially against
`.lower()` of a string (`"auth" in title.lower() or "payment" in title.lower()`)
inside loops creates unnecessary CPU overhead when the keyword doesn't match and
the `or` falls through. In Python, doing `title.lower()` redundantly repeatedly
inside an `if` block executes the C-level lowercase string allocation `N` times.
**Action:** When performing `in` checks against multiple strings using an `or`
operation, declare a temporary lowercase string variable
(`title_lower = title.lower()`) before the `if` block and compare against it
directly to halve the overhead.

## 2026-05-24 - Optimize duplicate lookup array algorithm in `_generate_ready_section`

**Learning:** Checking for list membership (`item not in list`) within a loop
creates an O(N^2) time complexity which causes massive delays for lists
containing thousands of items. **Action:** When filtering one list based on
membership in another, convert the filter list to a set
(`filter_set = set(filter_list)`) before the loop to reduce lookup complexity to
O(1), making the overall algorithm O(N).

## 2026-05-26 - [Avoid N+1 CLI invocations using ThreadPoolExecutor in Python Scripts]

**Learning:** Sequential execution of CLI commands like `gh` over a list of
items causes significant N+1 performance bottlenecks due to network latency and
subprocess startup overhead. **Action:** When a script needs to run independent
read-only CLI commands in a loop, refactor the logic into a pure function and
use `concurrent.futures.ThreadPoolExecutor` with `executor.map()` to parallelize
the calls safely. Ensure results are returned to the main thread to avoid
mutating shared state from worker threads.

## 2024-05-27 - [Avoid N+1 CLI invocations using ThreadPoolExecutor in scratch automation scripts]

**Learning:** In sequential read-only data fetching scripts like
`scratch_inventory.py` and `scratch_triage.py`, running `gh` CLI commands
sequentially for a list of repositories creates massive N+1 performance
bottlenecks due to network latency and subprocess startup overhead. **Action:**
Always parallelize independent read-only IO-bound operations by extracting the
subprocess loop body into a helper function and using
`concurrent.futures.ThreadPoolExecutor().map()`. This pattern safely preserves
list order while dramatically improving execution time.

## 2026-03-10 - [Avoid N+1 CLI invocations using ThreadPoolExecutor in review summarization scripts]

**Learning:** In PR summarization scripts like `scripts/get_prs_summarize.py`,
executing sequential `gh` CLI commands to fetch details for a list of PRs
creates a severe N+1 performance bottleneck due to network latency. **Action:**
Use `concurrent.futures.ThreadPoolExecutor().map()` to parallelize these
independent read-only IO-bound API calls. This preserves the original
presentation order while dramatically reducing execution time.

## 2026-05-29 - [GitHub Actions Dependency Pinning]

**Learning:** CI linters or repository policies may enforce pinning GitHub
Actions to full-length commit SHAs instead of tags (e.g.,
`actions/setup-python@v6.2.0` -> `actions/setup-python@<sha> # v6.2.0`) to
prevent supply chain attacks via mutable tags. **Action:** Always pin GitHub
Actions to full commit SHAs, even for official actions. Use `git ls-remote` to
quickly find the commit hash for a specific tag.

## 2026-05-31 - [Avoid Redundant title.lower() in conditionals]

**Learning:** Checking a series of hardcoded substrings sequentially against
`.lower()` of a string (`"auth" in title.lower() or "payment" in title.lower()`)
inside loops creates unnecessary CPU overhead when the keyword doesn't match and
the `or` falls through. In Python, doing `title.lower()` redundantly repeatedly
inside an `if` block executes the C-level lowercase string allocation `N` times.
**Action:** When performing `in` checks against multiple strings using an `or`
operation, declare a temporary lowercase string variable
(`title_lower = title.lower()`) before the `if` block and compare against it
directly to halve the overhead.

## 2024-05-24 - Parallelize Independent Network API Calls

**Learning:** Sequential network calls inside a loop (like executing GitHub CLI
commands iteratively) cause significant latency due to blocking I/O overhead.
**Action:** Use `concurrent.futures.ThreadPoolExecutor` to map network-bound
functions across iterations simultaneously, which can yield N-fold speedups
based on network latency and worker count.

## 2026-05-31 - [Optimize single-character lookups using string membership]

**Learning:** When checking if a single character belongs to a set of allowed
characters (e.g., `char in allowed_chars`), using a string for `allowed_chars`
(e.g., `"=+-@\t\r"`) is approximately 5x faster than using a tuple of strings
(e.g., `("=", "+", "-", "@", "\t", "\r")`). The string `in` operation performs
an O(1)-like C-level character lookup without the iterator allocation and
pointer indirection overhead of a tuple. **Action:** When validating single
characters against a small, fixed set of choices, define the collection as a
single string instead of a tuple or list.

## 2026-06-05 - [Avoid long 'or' condition chains and all() generators]

**Learning:** Checking a long series of hardcoded substrings sequentially using
`or` operations (e.g., `kw in string or kw2 in string`), or using `all()` with a
generator expression inside a loop, negatively impacts Code Health (cyclomatic
complexity) and incurs iterator allocation overhead in CPython. However, simply
replacing it with a nested loop can cause "Deep, Nested Complexity" issues in
static analysis. **Action:** Replace long chained `or` substring checks and
`all()` generator expressions with explicit `for` loops iterating over a defined
tuple of strings. To avoid deep nesting, extract the loop into a separate helper
function (e.g., `_contains_all_keywords`) or use guard clauses
(`if condition: continue`) to flatten the structure. This balances performance
by avoiding iterator allocation while simultaneously reducing nested conditional
complexity.

## 2026-11-20 - [Avoid redundant datetime.date.today().isoformat() parsing overhead]

**Learning:** When calculating the current date string
`datetime.date.today().isoformat()` inside a loop or comprehension, Python
repeatedly calls the method, generating a new object each time. This creates
unnecessary CPU overhead when the output is a constant for the duration of the
loop. **Action:** Always hoist method calls that generate static strings (like
`today().isoformat()`) outside of tight loops to evaluate them once and reuse
the value.

## 2026-06-14 - [Avoid eager evaluation in `.get()` fallbacks]

**Learning:** When using Python's `dict.get(key, default)` method, the `default`
argument is evaluated eagerly before the method is called. If the fallback value
is computationally expensive or allocates new objects (like
`p["title"].lower()`), this evaluation happens on every iteration, negating any
performance benefits of hoisting or memoization. **Action:** When a fallback
value in a `.get()` lookup is expensive to compute, retrieve the value without a
default (`value = p.get("key")`) and conditionally compute the fallback using an
`if value is None:` block.

## 2026-06-13 - [Hoist dictionary and tuple instantiation from hot execution paths]

**Learning:** Instantiating dictionaries or casting
`dict.items()` to a tuple inside a hot function (like one used for scoring items
iteratively) creates significant allocation and iterator overhead for each call.
**Action:** Always hoist static lookup dictionaries and tuple conversions of
dictionaries to the global/module scope. Accessing a global constant is
significantly faster than re-evaluating the dictionary literal or executing
`dict.items()` on every invocation.

## 2026-06-16 - [Avoid eager evaluation in `.get()` fallbacks with `.lower()`]

# **Learning:** When assigning dictionary `.get()` results and chaining `.lower()` on fallbacks, the `.lower()` executes eagerly if evaluated inline (e.g. `(p.get("title") or "").lower()`), creating unnecessary allocations when the key exists. **Action:** When accessing a string value that requires `.lower()`, assign the `.get()` result first, check if it is `not None`, and then apply `.lower()`. This avoids the eager fallback evaluation and redundant C-level string allocations.

**Learning:** Instantiating dictionaries or casting `dict.items()` to a tuple
inside a hot function (like one used for scoring items iteratively) creates
significant allocation and iterator overhead for each call. **Action:** Always
hoist static lookup dictionaries and tuple conversions of dictionaries to the
global/module scope. Accessing a global constant is significantly faster than
re-evaluating the dictionary literal or executing `dict.items()` on every
invocation.

## 2025-11-20 - [Performance Optimization for system_metrics.sh]
**Learning:** Found several spots where the system_metrics script spawns multiple heavy subprocesses in quick succession (e.g. `uptime` 3 times, `ps aux` 3 times, `launchctl list` 2 times) to parse different values from the same output. In a shell script, avoiding repeated execution of external commands and pipelining by doing it in a single pass (e.g., using a single `awk` statement and `read -r`) can yield significant performance gains, especially when these commands can be relatively slow and are run periodically.
**Action:** Always prefer parsing a single invocation of an external command with `awk` to extract multiple metrics at once, rather than spawning the command multiple times.

## 2026-11-20 - [Parallelize independent gh_json calls using ThreadPoolExecutor]

**Learning:** Sequential read-only API calls (`gh_json`) in scripts create a significant N+1 performance bottleneck due to network latency and blocking I/O overhead. This specifically impacts automation workflows making sequential GitHub API requests.

**Action:** Always use `concurrent.futures.ThreadPoolExecutor` to parallelize independent `gh_json` calls (like fetching issues and PRs simultaneously) rather than executing them sequentially. This drastically reduces execution latency.

## 2026-11-20 - [Avoid Large Method hotspots when extracting code]

**Learning:** When adding `concurrent.futures.ThreadPoolExecutor` logic into an existing large function, it can easily trip static analysis tools (like CodeScene Code Health) causing a 'Large Method' hotspot violation.

**Action:** Proactively extract the multi-line thread pool submission logic into a private helper function to keep the primary method concise and maintain code health baseline scores.

## 2026-06-22 - [Avoid unnecessary .split() list allocation in simple string formatting]

**Learning:** When extracting substrings from a string separated by a known delimiter inside a loop or comprehension (e.g. `line.split("=", 1)`), repeatedly calling `.split()` allocates new lists each time, causing a performance overhead. **Action:** When you only need to split once on the first delimiter and want to avoid unnecessary list allocation, use `str.partition()` instead of `str.split()`. It returns a tuple directly in C and doesn't allocate an arbitrary-length list.
