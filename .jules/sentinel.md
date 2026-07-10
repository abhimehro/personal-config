## 2026-03-20 - Argument Injection in Shell Wrappers

**Vulnerability:** Argument Injection ([CWE-88][CWE-88]) in
`scripts/youtube-download.sh`. The script passed user input `$1` directly to
`yt-dlp` without the `--` delimiter. **Learning:** Even simple wrapper scripts
can be vulnerable to RCE if they pass untrusted input to tools that accept flags
(like `--exec`). The shell expands variables, but the called program parses
flags. **Prevention:** Always use `--` to separate options from positional
arguments when calling CLI tools with untrusted input in shell scripts. Example:
`command -opt -- "$user_input"`.

## 2026-03-21 - Command Injection in Notification System

**Vulnerability:** Found unsanitized input being passed to `eval` in
`smart_notify` function. **Learning:** Even internal helper scripts can be
vulnerable if they construct commands via string concatenation and use `eval`.
Inputs like notification titles might come from external sources (logs,
filenames) and trigger execution. **Prevention:** Avoid `eval`. Use direct
command execution. If constructing complex arguments, verify quoting or use
arrays. For AppleScript, escape quotes and backslashes.

## 2026-03-22 - [Insecure Local Media Sharing]

**Vulnerability:** The `media-streaming/scripts/alldebrid-server.py` and
`infuse-media-server.py` scripts expose the file system via HTTP on `0.0.0.0`
without authentication. **Learning:** These scripts are designed for local
network sharing (Infuse integration) but lack basic security controls, relying
solely on network trust. This is a significant gap if the device connects to
untrusted networks. **Prevention:** Always bind to `127.0.0.1` by default for
development/local tools. If public/LAN access is needed, enforce authentication
(Basic Auth or similar) or use secure tunneling.

## 2026-03-23 - Secure Defaults in Python HTTP Servers

**Vulnerability:** Python's `http.server.SimpleHTTPRequestHandler` provides no
security controls and binds to all interfaces by default if not restricted.
**Learning:** Simple tools often sacrifice security for convenience.
Implementing Basic Auth in Python requires manually handling headers and
decoding Base64. **Prevention:** Use a wrapper class to enforce authentication.
Use `secrets` module for secure password generation. Bind to `127.0.0.1` by
default and require explicit flags for public binding.

## 2026-03-24 - Python Security Best Practices

**Vulnerability:** Timing attacks in password comparison and permissive CORS
configurations. **Learning:** `==` comparison is vulnerable to timing attacks.
Wildcard CORS (`*`) combined with Basic Auth allows authenticated requests from
malicious origins. **Prevention:** Use `secrets.compare_digest()` for
constant-time comparison. Remove wildcard CORS when auth is enabled or implement
strict origin allowlisting.

## 2026-03-25 - Path Traversal in Media Server

**Vulnerability:** Path traversal ([CWE-22][CWE-22]) and argument injection in
`infuse-media-server.py` where untrusted path input was concatenated directly
into rclone commands. **Learning:** Even when using `subprocess.run` (avoiding
shell injection), concatenated arguments can still lead to argument injection
(starting with `-`) or path traversal (`..`) if the called tool respects them.
**Prevention:** Implement strict path validation: decode, remove leading
slashes, split by separator to check for `..`, and block arguments starting with
`-`.

## 2026-03-26 - Path Traversal in Custom HTTP Handlers

**Vulnerability:** Path Traversal ([CWE-22][CWE-22]) in
`media-streaming/scripts/infuse-media-server.py`. The script constructed file
paths for `subprocess` calls by unquoting user input and appending it to a root,
without validating for `..` sequences. **Learning:** When implementing custom
request handlers (overriding `do_GET`), automatic protections provided by
frameworks (like `SimpleHTTPRequestHandler.translate_path`) are bypassed.
Explicit validation is required when mapping URLs to filesystem or external
command paths. **Prevention:** Always validate user-supplied paths before use.
Check for `..` components after decoding. Ideally, use `os.path.abspath` and
verify the path starts with the expected root directory, or reject paths
containing `..` if simple validation suffices.

## 2026-03-27 - Restrict Local Service Binding

**Vulnerability:** Service bound to 0.0.0.0 exposed to LAN. **Learning:**
Default configurations or "optimizations" can inadvertently expose services to
untrusted networks. **Prevention:** Explicitly bind local-only services to
127.0.0.1.

## 2026-03-28 - Insecure Configuration Generation

**Vulnerability:** The `controld-manager` script attempted to secure the DNS
listener by removing specific IPv6 wildcards but failed to explicitly enforce
localhost binding, potentially leaving the service exposed if defaults changed.
**Learning:** Reliance on removing _known bad_ values (denylist) is less secure
than enforcing _known good_ values (allowlist/enforcement) in configuration
generation. **Prevention:** When generating security-critical configurations,
explicitly set the desired secure values rather than trying to sanitize the
output of a tool. Verify the final configuration file content before starting
the service.

## 2026-03-29 - Privilege Escalation in Helper Scripts

**Vulnerability:** `scripts/network-mode-manager.sh` (which requests `sudo`)
executed a script from the local repository path relative to itself, rather than
the installed system binary. **Learning:** If a script prompts for `sudo` to run
another script, using a relative path to a user-writable file (like a local repo
clone) creates a privilege escalation path. A malicious actor (or the user
themselves) could modify the target script and then run the wrapper, unknowingly
executing the modified code as root. **Prevention:** Helper scripts that
escalate privileges should prefer executing installed, root-owned binaries
(e.g., in `/usr/local/bin`) over local/relative paths.

## 2026-03-30 - Insecure File Creation in Root Scripts

**Vulnerability:** Insecure file creation ([CWE-732][CWE-732] and
[CWE-59][CWE-59]) in `controld-system/scripts/controld-manager`. The script used
`touch` followed by `chmod 600` on a log file. **Learning:** Checking existence
and setting permissions in two steps creates a race condition. If the target is
a symlink ([CWE-59][CWE-59]), `chmod` follows it and changes permissions of the
target file. **Prevention:** Use `umask` in a subshell (e.g.,
`(umask 077 && touch file)`) to create files with secure permissions atomically.
Verify files are not symlinks (`-L`) before performing operations that follow
them.

## 2026-03-31 - Insecure Permissions on Configuration Files

**Vulnerability:** World-readable configuration files in
`/etc/controld/profiles/` containing sensitive Profile IDs. **Learning:**
Sensitive identifiers should be treated as secrets on disk to prevent
unauthorized access by other local users. Inconsistency between log redaction
and file permissions weakens defense in depth. **Prevention:** Explicitly set
`chmod 600` on generated configuration files and `chmod 700` on their
directories immediately after creation.

## 2026-04-01 - Logic Flaw in Lock File Mechanism

**Vulnerability:** A logic flaw in `maintenance/bin/run_all_maintenance.sh`
where the script checked if a directory existed but failed to handle the case
where a file existed at the lock path, allowing bypass of the locking mechanism.
**Learning:** Checking for directory existence (`[[ -d ... ]]`) after `mkdir`
failure is insufficient if `mkdir` fails due to a file blocking the path. The
script proceeded execution, defeating the lock. **Prevention:** Always handle
the failure case explicitly. If a resource creation fails, verify _why_ or exit
securely. Use `mkdir` atomic creation as the primary check and ensure failure
paths are handled securely (exit by default).

## 2026-04-02 - Variable Scope in Bash Loops

**Vulnerability:** Inaccurate reporting in
`maintenance/bin/security_manager.sh`. The script used a pipe
(`find ... | while ...`) to iterate over files and increment a counter variable.
In Bash, the pipe runs the loop in a subshell, so the counter updates were lost
when the loop finished. **Learning:** Logic bugs in security tools can mask the
very vulnerabilities they are meant to detect. Modifying variables inside a
piped loop is a common pitfall that leads to silent failures. **Prevention:**
Use process substitution (`while ... done < <(command)`) instead of pipes when
you need to modify variables in the parent shell scope from within a loop.

## 2026-04-03 - Tracked Shell History Leak

**Vulnerability:** Shell history file (`.local/share/fish/fish_history`)
containing command logs was committed to the git repository. **Learning:**
Dotfiles repositories often inadvertently include sensitive history files if
they are located within the tracked directory structure (e.g., XDG data dirs).
Standard gitignores may miss newer XDG paths. **Prevention:** Explicitly ignore
known history paths (`.local/share/fish/fish_history`) in `.gitignore` and audit
repository for sensitive files.

## 2026-04-04 - Path Traversal in Backup Restoration

**Vulnerability:** Potential path traversal ([CWE-22][CWE-22]) in
`maintenance/bin/security_manager.sh`. The `restore_config` function extracted
tar archives without checking for directory traversal (`../`) or absolute paths
in the archive entries. **Learning:** Tar archives can contain entries with
`../` or absolute paths that write files outside the intended extraction
directory, potentially overwriting critical system files. **Prevention:** Always
validate tar archive contents before extraction using `tar -tf` and checking for
`../` or leading `/` patterns. Reject archives with unsafe paths.

## 2026-04-05 - Information Disclosure via Hardcoded Paths

**Vulnerability:** Information Disclosure (Username) and Path Traversal in
`adguard/scripts/consolidate_adblock_lists.py`. The script contained a hardcoded
absolute path (`$HOME/Downloads`), revealing the developer's username and making
the script non-portable. **Learning:** Hardcoded paths in scripts often contain
sensitive information (usernames, project structures) and break portability.
They also encourage bad security practices by relying on specific environments
rather than robust configuration. **Prevention:** Use `argparse` or environment
variables to inject paths. Validate that input directories exist. Default to
relative paths (like `.`) for better portability.

## 2026-04-06 - Command Injection in Health Check

**Vulnerability:** Command Injection ([CWE-78][CWE-78]) in
`maintenance/bin/health_check.sh`. The script interpolated the
`HEALTH_LOG_LOOKBACK_HOURS` variable directly into a command string passed to
`bash -c`, allowing arbitrary code execution if the variable contained malicious
input. **Learning:** Shell scripts that construct commands from variables are
inherently risky. Sourcing configuration files (`source config.env`) without
validation assumes the file is trustworthy, but environment variables can
override defaults or be set maliciously if the config is missing.
**Prevention:** Always sanitize variables used in command construction. Ensure
numeric values are actually integers using regex validation
(`[[ "$VAR" =~ ^[0-9]+$ ]]`) before using them.

## 2026-04-07 - Symlink Attack in Config Generation

**Vulnerability:** Symlink following ([CWE-59][CWE-59]) in
`controld-system/scripts/controld-manager`. The script used `cp` to overwrite
configuration files and `mkdir`+`chmod` for directory creation without adequate
symlink protection, creating TOCTOU race conditions. **Learning:** Operations
like `cp`, `chmod`, and `mkdir` can be exploited through symlinks. Multi-step
operations (mkdir+chmod or rm+cp+chmod) create TOCTOU windows where an attacker
can inject symlinks between steps. Even single checks before operations are
vulnerable if the check and operation aren't atomic. **Prevention:** Use atomic
operations: `install -d -m 700` for directories (creates with permissions in one
step) and `install -m 600` for files (copies and sets permissions atomically).
Add both pre-flight symlink checks AND post-creation verification to minimize
TOCTOU windows. Protect ALL sensitive paths (directories, files, and their
parents), not just the final destination.

[CWE-22]: https://cwe.mitre.org/data/definitions/22.html
[CWE-59]: https://cwe.mitre.org/data/definitions/59.html
[CWE-78]: https://cwe.mitre.org/data/definitions/78.html
[CWE-88]: https://cwe.mitre.org/data/definitions/88.html
[CWE-732]: https://cwe.mitre.org/data/definitions/732.html

## 2026-04-08 - Symlink Hijacking in Setup Script

**Vulnerability:** Symlink following
([CWE-59](https://cwe.mitre.org/data/definitions/59.html)) in
`scripts/setup-controld.sh`. The script performed `sudo chmod`, `sudo chown`,
and `sudo cp` on paths `/etc/controld` and `/usr/local/bin/controld-manager`
without checking if they were symbolic links. **Learning:** Setup scripts
running with elevated privileges (sudo) are prime targets for symlink attacks.
If a user-writable path (or a path that could be created by a user) is a
symlink, operations on it affect the target, potentially corrupting system files
(e.g., changing `/etc` permissions). **Prevention:** Always verify that a path
is not a symbolic link (`[[ -L ... ]]`) before performing sensitive operations
like `chmod`, `chown`, or `cp` on it, especially when running as root.

## 2026-04-09 - Backup Integrity Verification

**Vulnerability:** Lack of integrity checks for backup archives in
`maintenance/bin/security_manager.sh`. The script restored backups without
verifying they hadn't been tampered with or corrupted. **Learning:** Backup
systems that rely solely on file existence or basic path checks are vulnerable
to restoring compromised or corrupted states. A malicious actor with filesystem
access could modify a backup archive to inject malicious configurations or
scripts, which would then be restored with high privileges. **Prevention:**
Implement cryptographic checksums (e.g., SHA256) for all backup archives upon
creation and verify these checksums before restoration. This primarily detects
corruption or tampering. Strong authenticity guarantees are only provided if the
checksum data itself is protected separately (for example, stored off-host, in
an append-only log, or signed), rather than being just another writable file
alongside the backups.

## 2026-04-10 - Credentials in Process List

**Vulnerability:** Information Disclosure ([CWE-214][CWE-214]) in
`media-streaming/scripts/media-server-daemon.sh` and
`media-streaming/scripts/final-media-server.sh`. The scripts passed sensitive
credentials (passwords) as command-line arguments (`--user`, `--pass`) to
`rclone`. **Learning:** Command-line arguments are visible to all users on the
system via process listing tools like `ps aux`. This exposes secrets to any user
or process with read access to process information. **Prevention:** Use
environment variables (e.g., `RCLONE_PASS`) to pass secrets to CLI tools, as
environment variables are typically only visible to the process owner and root.

[CWE-214]: https://cwe.mitre.org/data/definitions/214.html

## 2026-04-11 - Insecure Temporary File Creation

**Vulnerability:** Insecure Temporary File Creation ([CWE-377][CWE-377]) in
`scripts/compare_shell_configs.sh`. The script created a predictable temporary
file in `/tmp` using a timestamp, allowing a race condition where an attacker
could pre-create the file (potentially as a symlink) to overwrite arbitrary
files or read sensitive data. **Learning:** Using predictable filenames in
shared directories like `/tmp` is insecure. The `> file` redirection follows
symlinks if the file exists, and files created via shell redirection typically
end up with permissions 0644 under a default umask of 022, which might expose
sensitive data. **Prevention:** Always use `mktemp` to create temporary files.
It generates a unique filename and sets restrictive permissions (0600)
atomically. Use `trap` to ensure cleanup.

[CWE-377]: https://cwe.mitre.org/data/definitions/377.html

## 2026-04-12 - Terminal Injection in Logging Functions

**Vulnerability:** Terminal Injection ([CWE-150][CWE-150]) in
`scripts/youtube-download.sh` and `scripts/lib/network-core.sh`. The scripts
used `echo -e` to print user input (clipboard content or function arguments),
allowing an attacker to inject escape sequences to manipulate the terminal
output or spoof log entries. **Learning:** `echo -e` interprets backslash
escapes in all arguments. Even if the intent is to print a variable, `echo -e`
treats it as a format string of sorts. This is dangerous when handling untrusted
input like clipboard content or filenames. **Prevention:** Use
`printf "%s\n" "$VAR"` to print untrusted strings. This treats the content
literally. If color codes are needed, print them separately with `echo -ne` or
`printf` and then print the variable content safely.

[CWE-150]: https://cwe.mitre.org/data/definitions/150.html

## 2026-04-13 - Path Traversal Bypass via Backslashes

**Vulnerability:** A directory traversal
([CWE-22](https://cwe.mitre.org/data/definitions/22.html)) vulnerability existed
in `media-streaming/archive/scripts/infuse-media-server.py` where the
`validate_path` function split the path using forward slashes (`/`) to check for
`..` components. This allowed an attacker to bypass the check by using
backslashes (`\`), e.g., `..\..\etc\passwd`, which might be interpreted by the
underlying operating system or tools (like `rclone`) as directory separators,
leading to unauthorized file access. **Learning:** Checking for directory
traversal using only string splitting on forward slashes is insufficient because
many systems and tools normalize or accept backslashes as path separators.
Attackers can use this discrepancy to bypass simple string-matching filters.
**Prevention:** Always normalize path separators (e.g., converting all `\` to
`/`) before performing any path validation or traversal checks. This ensures
that all potential directory traversal sequences are evaluated consistently,
regardless of the separator used by the attacker.

## 2026-04-14 - Command Injection Risk via eval

**Vulnerability:** Command Injection
([CWE-78](https://cwe.mitre.org/data/definitions/78.html)) risk existed in
`scripts/bootstrap_fish_plugins.sh`. The `spinner` function constructed commands
by joining arguments into a single string (`local cmd="$*"`) and evaluating them
with `eval "$cmd"`. This is an unsafe pattern that can lead to arbitrary code
execution if dynamic input is introduced later. **Learning:** Using `eval` to
run commands is an anti-pattern that introduces command injection
vulnerabilities when strings are executed. String manipulation and joining lose
shell parameter separation and escaping. **Prevention:** Avoid using `eval` to
execute command strings. Pass arguments as separate elements and use safe array
execution `"$@"` directly.

## 2026-04-15 - Insecure Temporary File Creation in Bash Scripts

**Vulnerability:** Maintenance scripts (`monthly_maintenance.sh`,
`weekly_maintenance.sh`, `system_metrics.sh`) used hardcoded, predictable
temporary file paths in `/tmp` (e.g., `/tmp/monthly_maintenance.lock`,
`/tmp/maintenance_io_test.tmp`). **Learning:** This is a classic CWE-377
(Insecure Temporary File Creation) vulnerability. It allows for symlink attacks
where an attacker pre-creates the file as a symlink to a critical system file,
tricking the script (often running as root or a privileged user) into
overwriting it. It also allows Denial of Service by pre-creating lock files to
prevent scripts from running. **Prevention:** Always use
`mktemp -t 'prefix.XXXXXX'` for temporary files, or store lock files in
user-specific, restricted directories (e.g., `$HOME/Library/Logs/maintenance/`)
rather than the world-writable `/tmp`.

## 2026-04-16 - Insecure Temporary File Creation (CWE-377) in Maintenance Scripts

**Vulnerability:** Predictable temporary file creation in `/tmp/` existed across
several maintenance scripts (`generate_error_summary.sh`, `node_maintenance.sh`,
`performance_optimizer.sh`, `smart_scheduler.sh`). For example,
`MARKER_FILE="/tmp/maintenance_run_marker_$$"`. **Learning:** This is a classic
CWE-377 vulnerability. It allows for symlink attacks where an attacker
pre-creates the file as a symlink to a critical system file, tricking the script
(often running as root or a privileged user) into overwriting it. It also allows
Denial of Service by pre-creating lock files to prevent scripts from running.
**Prevention:** Always use `mktemp -t 'prefix.XXXXXX'` for secure temporary file
creation. This guarantees uniqueness and correct permissions, preventing race
conditions and symlink attacks.

## 2026-04-17 - Insecure Temporary Directory in Surgical Cleanup

**Vulnerability:** An Insecure Temporary File Creation
([CWE-377](https://cwe.mitre.org/data/definitions/377.html)) vulnerability was
found in `scripts/macos/SURGICAL_CLEANUP.sh`. The script used a predictable,
hardcoded temporary path (`/tmp/fish_backup`) to temporarily store the user's
`fish` configuration during cleanup. **Learning:** Using a predictable path in a
world-writable directory like `/tmp` allows a local attacker to pre-create the
directory as a symbolic link. When the script attempts to move the backed-up
files back to their original location
(`mv "/tmp/fish_backup" "$HOME/.config/fish"`), it could follow the symlink,
leading to arbitrary file overwrite or backup hijacking with the script runner's
privileges. **Prevention:** Always generate unique, unpredictable temporary
directories using `mktemp -d -t 'prefix.XXXXXX'` for storing backups during
multi-step file operations. Ensure the directory is securely removed afterward.

## 2026-04-18 - Command Injection Risk via eval in Home Directory Resolution

**Vulnerability:** Command Injection
([CWE-78](https://cwe.mitre.org/data/definitions/78.html)) risk existed in
`configs/.config/mole/lib/core/base.sh` within the `get_user_home` function. The
code used `eval echo "~$user"` as a fallback for home directory resolution
without validating the `$user` variable, allowing potential execution of
arbitrary commands if an attacker could control the username string.
**Learning:** `eval` is dangerous when used for dynamic variable expansion like
tilde expansion if the input is not strictly validated. Even if primarily
internal, it creates a risky trust boundary violation. **Prevention:** Use
native, secure commands like `getent passwd "$user" | cut -d: -f6` on Linux. If
`eval` is absolutely necessary for tilde expansion, strictly validate the
username against a safe POSIX regex (`^[a-zA-Z0-9_][a-zA-Z0-9_.-]*\$?$`) before
execution.

## 2026-04-19 - Command Injection Risk via eval in dynamic variable assignment

**Vulnerability:** Command Injection
([CWE-78](https://cwe.mitre.org/data/definitions/78.html)) risk existed in
`maintenance/bin/system_cleanup.sh`, `configs/.config/mole/lib/core/base.sh`,
and `configs/.config/mole/lib/core/app_protection.sh`. Functions used `eval` to
assign variables dynamically based on function arguments (e.g.
`eval "$var_name=\"\$value\""`). If an attacker could control the variable name
passed to these functions, they could inject arbitrary bash commands.
**Learning:** Using `eval` to mimic pass-by-reference variable assignment in
shell scripts exposes the script to command injection vulnerabilities if the
variable name is not strictly validated. **Prevention:** Strictly validate the
dynamically passed variable name against `^[a-zA-Z_][a-zA-Z0-9_]*$` before
evaluation to prevent Command Injection (CWE-78).

## 2026-04-20 - Insecure Temporary File Creation (CWE-377) in LaunchAgent

**Vulnerability:** Predictable temporary file paths (`/tmp/morning-brief.out`
and `/tmp/morning-brief.err`) were used for `StandardOutPath` and
`StandardErrorPath` in `launch-agents/com.speedybee.morningbrief.plist`.
**Learning:** This is a classic CWE-377 vulnerability. It allows for symlink
attacks where a local attacker can pre-create the log files as symlinks pointing
to sensitive files. When the LaunchAgent runs, `launchd` will open the files
following the symlink, overwriting the target files with the job's output.
**Prevention:** Always route macOS LaunchAgent/LaunchDaemon logs to secure,
user-owned directories (like `/Users/username/Library/Logs/`) instead of
world-writable directories like `/tmp`.

## 2025-03-31 - [secrets module AttributeError]

**Vulnerability:** Use of `secrets.choices` instead of
`secrets.SystemRandom().choices` **Learning:** `secrets` module does not have a
module-level `choices` function, leading to `AttributeError` and runtime
crashes, potentially preventing server from starting up or properly initializing
secure credentials. **Prevention:** Use `secrets.choice` in a loop or
`secrets.SystemRandom().choices` to generate random strings of a given length.

## 2026-04-21 - Command Injection Risk via printf -v dynamic variable assignment

**Vulnerability:** Command Injection
([CWE-78](https://cwe.mitre.org/data/definitions/78.html)) risk existed in
`maintenance/bin/system_cleanup.sh`. The script used `printf -v "$1" ...` to
assign variables dynamically based on function arguments. In bash, if an
attacker can control the variable name passed to `printf -v`, they can execute
arbitrary shell commands via array index execution (e.g. `a[0$(id>&2)]`).
**Learning:** Using `printf -v` to mimic pass-by-reference variable assignment
in shell scripts exposes the script to command injection vulnerabilities,
similar to `eval`, if the variable name is not strictly validated. The attacker
can inject commands through the array index evaluation mechanism built into
bash's variable resolution. **Prevention:** Strictly validate the dynamically
passed variable name against `^[a-zA-Z_][a-zA-Z0-9_]*$` before execution in
`printf -v`, `eval`, or `declare` to prevent Command Injection (CWE-78).

## 2026-04-22 - Option Injection Risk via pgrep/pkill

**Vulnerability:** Option Injection
([CWE-88](https://cwe.mitre.org/data/definitions/88.html)) risk existed in
`pgrep` and `pkill` calls across
`configs/.config/mole/lib/core/app_protection.sh`,
`configs/.config/mole/lib/clean/system.sh`,
`configs/.config/mole/lib/optimize/tasks.sh`,
`configs/.config/mole/lib/uninstall/batch.sh`,
`maintenance/bin/service_monitor.sh`, and
`maintenance/bin/service_optimizer.sh`. Variables containing untrusted input
(e.g. process names) could be interpreted as command-line flags (like `-u 0`) if
they started with a hyphen, causing the commands to execute with unintended
behavior. **Learning:** Using variable patterns with process management commands
like `pgrep` or `pkill` without a double-dash separator `--` exposes shell
scripts to option injection attacks, where attacker-controlled strings starting
with hyphens alter the target scope of the termination or search process.
**Prevention:** Always use the `--` separator with `pgrep` and `pkill` before
passing dynamic or external variables (e.g., `pkill -x -- "$pattern"`) to ensure
arguments are treated strictly as patterns and not parsed as command-line
options.

## 2026-04-23 - Command Injection Risk via subprocess.run with shell=True

**Vulnerability:** Command Injection
([CWE-78](https://cwe.mitre.org/data/definitions/78.html)) risk existed in
`parse_inventory.py`. The code constructed a GitHub CLI command string
dynamically using
`f"source ../email-security-pipeline/GH_TOKEN.env && gh pr view {pr} -R {repo} --json ..."`
and executed it using `subprocess.run(..., shell=True)`. Because `pr` and `repo`
were parsed from a markdown file (`tasks/pr-inventory.md`), an attacker could
potentially control these values to inject arbitrary shell commands.
**Learning:** Using `subprocess.run` with `shell=True` and dynamically
interpolated strings is a classic command injection vulnerability, effectively
equivalent to using `eval` or `system()` in other languages. While `source`
requires a shell to run, relying on the shell to parse `.env` files is dangerous
when mixed with untrusted input in the same command. **Prevention:** Avoid
`shell=True` in `subprocess.run`. Pass commands and arguments as a list of
strings. If you need to load environment variables, parse the `.env` file
manually in Python and pass the resulting dictionary to the `env` parameter of
`subprocess.run`.

## 2026-04-25 - Command Injection Risk via eval in dynamic variable assignment

**Vulnerability:** Command Injection
([CWE-78](https://cwe.mitre.org/data/definitions/78.html)) risk existed in
`configs/.config/mole/lib/core/app_protection.sh` and
`configs/.config/mole/lib/core/base.sh`. Functions used `eval` to assign
variables dynamically based on function arguments without validating the
variable name (e.g. `eval "$var_name=\"\$regex\""`). If an attacker could
control the variable name passed to these functions, they could inject arbitrary
bash commands. **Learning:** Using `eval` to mimic pass-by-reference variable
assignment in shell scripts exposes the script to command injection
vulnerabilities if the variable name is not strictly validated. **Prevention:**
Strictly validate the dynamically passed variable name against
`^[a-zA-Z_][a-zA-Z0-9_]*$` before evaluation to prevent Command Injection
(CWE-78).

## 2026-04-26 - Terminal Injection Risk via echo -e

**Vulnerability:** Terminal Injection
([CWE-150](https://cwe.mitre.org/data/definitions/150.html)) existed in
`scripts/test_ssh_connections.sh`. The script used `echo -e` to print log
messages containing untrusted input, allowing an attacker to inject escape
sequences to manipulate terminal output. **Learning:** `echo -e` interprets
backslash escapes in all arguments. Even if the intent is to print a variable,
`echo -e` treats it as a format string. **Prevention:** Use
`printf "%b %s\n" "$COLOR" "$*"` for colored output instead of `echo -e` to
ensure variables are printed literally.

## 2026-05-03 - CLI Argument Information Exposure Fix in Fish Script

**Vulnerability:** Information Exposure (CWE-214) / Exposure of Sensitive
Information Through Process Arguments. `done.fish` passed the
`__done_kitty_remote_control_password` to `kitty @` via the `--password`
command-line flag. **Learning:** Process command lines are typically globally
readable on Unix-like systems via `ps` or `/proc`. Passing secrets as
command-line arguments is insecure. **Prevention:** Use environment variables,
standard input (STDIN), or file descriptors to pass secrets to processes
securely, as these are not exposed in the process table. For kitty specifically,
the `KITTY_RC_PASSWORD` environment variable provides a secure alternative to
the `--password` CLI flag.

## 2026-05-05 - Command Injection Risk via eval in dynamic variable assignment

**Vulnerability:** Command Injection (CWE-78) risk existed in log timers and app
protection regex building due to the use of eval. **Learning:** Dynamic variable
names were assigned via eval, allowing arbitrary command execution if an
attacker controls the variable name. **Prevention:** Refactor to use printf -v
for dynamic assignment and indirect expansion (${!var}) for dynamic reading.

## 2026-05-06 - Terminal Injection via echo -e

**Vulnerability:** Terminal Injection vulnerability where malicious input
containing escape characters could manipulate the terminal display or execute
arbitrary commands depending on the terminal emulator. Found in `setup.sh`
logging functions.

## 2026-05-17 - AppleScript Injection via osascript and display dialog

**Vulnerability:** AppleScript Injection (CWE-74) existed in
`configs/.config/mole/lib/core/sudo.sh` where `osascript` was executing a string
containing user-controlled variable
`${MOLE_SUDO_PROMPT:-Admin access required}`. **Learning:** Using inline string
interpolation in AppleScript code executed via `osascript` allows an attacker to
inject arbitrary AppleScript commands if they control the variable.
**Prevention:** Use `osascript -e 'on run argv'` and pass dynamic variables
safely as command-line arguments (e.g. `(item 1 of argv)`).

## 2026-05-29 - AppleScript Injection Risk via osascript and string interpolation

**Vulnerability:** AppleScript Injection
([CWE-74](https://cwe.mitre.org/data/definitions/74.html)) existed in
`media-streaming/scripts/mount-media.sh` and
`media-streaming/scripts/rename-media.sh` where `osascript` was executing a
string containing user-controlled variables. Even though the scripts attempted
to escape double quotes (`${title//\"/\\\"}`), this could be bypassed using
backslashes (e.g. `\" & do shell script \"...\" & \"`). **Learning:** Using
inline string interpolation in AppleScript code executed via `osascript` allows
an attacker to inject arbitrary AppleScript commands if they control the
variable, even if quotes are escaped. **Prevention:** Use
`osascript -e 'on run argv'` and pass dynamic variables safely as command-line
arguments (e.g. `(item 1 of argv)`).

## 2026-06-03 - AppleScript Injection via osascript and string interpolation in batch.sh

**Vulnerability:** AppleScript Injection
([CWE-74](https://cwe.mitre.org/data/definitions/74.html)) existed in
`configs/.config/mole/lib/uninstall/batch.sh` where `osascript` was executing a
string containing the user-controlled variable `$clean_name` (derived from
`$app_name`). Even though the script attempted to manually escape double quotes
(`${clean_name//\"/\\\"}`), this approach is brittle and can be bypassed.
**Learning:** Using inline string interpolation in AppleScript code executed via
`osascript` allows an attacker to inject arbitrary AppleScript commands if they
control the variable, even if quotes are escaped. **Prevention:** Use
`osascript - "$variable"` (or `osascript -e 'on run argv'`) and pass dynamic
variables safely as command-line arguments to the `on run argv` handler (e.g.
`item 1 of argv`).

## 2026-06-01 - Bash Eval Injection in Trap Restoration

**Vulnerability:** Bash Eval Injection via `eval "${old_int_trap:-trap - INT}"`
in UI spinner traps. **Learning:** Shell-assigned variable expansions inside
`eval` can still introduce command injection if an attacker previously
influenced the environment's `trap` commands. It creates unnecessary attack
surface. **Prevention:** Avoid saving and restoring traps using `eval` when
executing local synchronous blocks like UI spinners. Isolate the execution and
custom temporary traps inside a subshell `( ... )`, which protects the parent
shell's configuration and eliminates the need for `eval`.

## 2026-06-15 - Option Injection Risk via pgrep/pkill

**Vulnerability:** Option Injection
([CWE-88](https://cwe.mitre.org/data/definitions/88.html)) risk existed in
`media-streaming/scripts/sync-launchagents.sh`. The variables passed to
`pgrep -fl` and `pkill -f` (specifically `$script`) were untrusted and could be
interpreted as command-line flags if they started with a hyphen. **Learning:**
Using variable patterns with process management commands like `pgrep` or `pkill`
without a double-dash separator `--` exposes shell scripts to option injection
attacks, where attacker-controlled strings starting with hyphens alter the
target scope of the termination or search process. This is the exact same
learning documented on 2026-04-22, found in another file. **Prevention:** Always
use the `--` separator with `pgrep` and `pkill` before passing dynamic or
external variables (e.g., `pkill -f -- "$pattern"`) to ensure arguments are
treated strictly as patterns and not parsed as command-line options.

## 2026-06-25 - AppleScript Option Injection Risk via osascript without -- delimiter

**Vulnerability:** AppleScript Option Injection (CWE-74/CWE-88 variant). Even when passing dynamic variables safely to `osascript` using `-e 'on run argv'`, the variables were passed directly after the script string without the `--` delimiter (e.g. `osascript -e 'on run argv' ... -e 'end run' "$msg" "$title"`). If an attacker controls the variable and starts it with a hyphen, `osascript` may interpret the variable as a command-line flag rather than a positional argument, leading to option injection or unintended execution.
**Learning:** When invoking `osascript` with dynamic variables from bash, you must explicitly separate options from arguments using the `--` delimiter before positional arguments to prevent them from being parsed as flags.
**Prevention:** Always use the `--` argument delimiter before positional arguments when using `osascript` with external variables (e.g., `osascript -e 'on run argv' ... -- "$VAR"`).


## 2026-06-27 - AppleScript Option Injection in Batch Uninstaller

**Vulnerability:** AppleScript Option Injection (CWE-88 variant). In `configs/.config/mole/lib/uninstall/batch.sh` and `configs/.config/mole/lib/core/file_ops.sh`, `osascript - "$variable"` is used without the `--` delimiter before the positional arguments (e.g. `osascript - "$clean_name" <<-'EOF'`). If the variable starts with a hyphen, it might be interpreted as a flag, leading to Option Injection.
**Learning:** When passing dynamic variables as positional arguments to `osascript` using heredocs (`<<`), a `--` separator is still required before the variables.
**Prevention:** Always use the `--` argument delimiter before positional arguments when using `osascript` with external variables (e.g., `osascript - -- "$VAR" <<-'EOF'`).

## 2026-06-25 - AppleScript Option Injection Risk via osascript without -- delimiter
**Vulnerability:** AppleScript Option Injection (CWE-88 variant). Even when passing dynamic variables safely to `osascript` using `-e 'on run argv'`, the variables were passed directly after the script string without the `--` delimiter. In other places, `osascript - "$variable"` was used without `--` before the positional arguments. If an attacker controls the variable and starts it with a hyphen, `osascript` may interpret the variable as a command-line flag rather than a positional argument, leading to option injection or unintended execution. Note: because BSD `getopt` halts at `-`, the `--` must appear before the `-` stdin indicator (e.g., `osascript -- - "$VAR"`).
**Learning:** When invoking `osascript` with dynamic variables from bash, you must explicitly separate options from arguments using the `--` delimiter before any positional arguments or stdin indicators to prevent them from being parsed as flags.
**Prevention:** Always use the `--` argument delimiter before the `-` stdin indicator or any positional arguments when using `osascript` with external variables (e.g., `osascript -- - "$VAR" <<-'EOF'`).

## 2026-07-15 - Option Injection in pkill

**Vulnerability:** Option Injection (CWE-88 variant). Found that some scripts using `pkill` for process management did not include the `--` delimiter before the process name argument when other flags were present. For instance, `pkill -f "ctrld"` was changed to `pkill -f -- "ctrld"`. If an attacker controls the variable and starts it with a hyphen, `pkill` may interpret the variable as a command-line flag rather than a positional argument, leading to option injection or unintended execution.
**Learning:** When invoking `pkill` with dynamic variables from bash, you must explicitly separate options from arguments using the `--` delimiter before positional arguments to prevent them from being parsed as flags.
**Prevention:** Always use the `--` argument delimiter before positional arguments when using `pkill` with external variables (e.g., `pkill -f -- "ctrld"`).

## $(date +%Y-%m-%d) - AppleScript Option Injection Risk via osascript without -- delimiter
**Vulnerability:** AppleScript Option Injection (CWE-88 variant). Even when passing dynamic variables safely to `osascript` using `-e 'on run argv'`, the variables were passed directly after the script string without the `--` delimiter. In other places, `osascript - "$variable"` was used without `--` before the positional arguments. If an attacker controls the variable and starts it with a hyphen, `osascript` may interpret the variable as a command-line flag rather than a positional argument, leading to option injection or unintended execution. Note: because BSD `getopt` halts at `-`, the `--` must appear before the `-` stdin indicator (e.g., `osascript -- - "$VAR"`).
**Learning:** When invoking `osascript` with dynamic variables from bash, you must explicitly separate options from arguments using the `--` delimiter before any positional arguments or stdin indicators to prevent them from being parsed as flags.
**Prevention:** Always use the `--` argument delimiter before the `-` stdin indicator or any positional arguments when using `osascript` with external variables (e.g., `osascript -- - "$VAR" <<-'EOF'`).

## $(date +%Y-%m-%d) - Option Injection in pkill
**Vulnerability:** Option Injection (CWE-88 variant). Found that some scripts using `pkill` for process management did not include the `--` delimiter before the process name argument when other flags were present. For instance, `pkill -f "ctrld"` was changed to `pkill -f -- "ctrld"`. If an attacker controls the variable and starts it with a hyphen, `pkill` may interpret the variable as a command-line flag rather than a positional argument, leading to option injection or unintended execution.
**Learning:** When invoking `pkill` with dynamic variables from bash, you must explicitly separate options from arguments using the `--` delimiter before positional arguments to prevent them from being parsed as flags.
**Prevention:** Always use the `--` argument delimiter before positional arguments when using `pkill` with external variables (e.g., `pkill -f -- "ctrld"`).
