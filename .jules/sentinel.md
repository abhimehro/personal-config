## 2024-05-22 - Argument Injection in Shell Wrappers
**Vulnerability:** Argument Injection ([CWE-88][]) in `scripts/youtube-download.sh`. The script passed user input `$1` directly to `yt-dlp` without the `--` delimiter.
**Learning:** Even simple wrapper scripts can be vulnerable to RCE if they pass untrusted input to tools that accept flags (like `--exec`). The shell expands variables, but the called program parses flags.
**Prevention:** Always use `--` to separate options from positional arguments when calling CLI tools with untrusted input in shell scripts. Example: `command -opt -- "$user_input"`.
## 2025-10-21 - Command Injection in Notification System
**Vulnerability:** Found unsanitized input being passed to `eval` in `smart_notify` function.
**Learning:** Even internal helper scripts can be vulnerable if they construct commands via string concatenation and use `eval`. Inputs like notification titles might come from external sources (logs, filenames) and trigger execution.
**Prevention:** Avoid `eval`. Use direct command execution. If constructing complex arguments, verify quoting or use arrays. For AppleScript, escape quotes and backslashes.
## 2025-10-18 - [Insecure Local Media Sharing]
**Vulnerability:** The `media-streaming/scripts/alldebrid-server.py` and `infuse-media-server.py` scripts expose the file system via HTTP on `0.0.0.0` without authentication.
**Learning:** These scripts are designed for local network sharing (Infuse integration) but lack basic security controls, relying solely on network trust. This is a significant gap if the device connects to untrusted networks.
**Prevention:** Always bind to `127.0.0.1` by default for development/local tools. If public/LAN access is needed, enforce authentication (Basic Auth or similar) or use secure tunneling.
## 2025-10-21 - Secure Defaults in Python HTTP Servers
**Vulnerability:** Python's `http.server.SimpleHTTPRequestHandler` provides no security controls and binds to all interfaces by default if not restricted.
**Learning:** Simple tools often sacrifice security for convenience. Implementing Basic Auth in Python requires manually handling headers and decoding Base64.
**Prevention:** Use a wrapper class to enforce authentication. Use `secrets` module for secure password generation. Bind to `127.0.0.1` by default and require explicit flags for public binding.
## 2025-12-18 - Python Security Best Practices
**Vulnerability:** Timing attacks in password comparison and permissive CORS configurations.
**Learning:** `==` comparison is vulnerable to timing attacks. Wildcard CORS (`*`) combined with Basic Auth allows authenticated requests from malicious origins.
**Prevention:** Use `secrets.compare_digest()` for constant-time comparison. Remove wildcard CORS when auth is enabled or implement strict origin allowlisting.
## 2025-12-20 - Path Traversal in Media Server
**Vulnerability:** Path traversal ([CWE-22][]) and argument injection in `infuse-media-server.py` where untrusted path input was concatenated directly into rclone commands.
**Learning:** Even when using `subprocess.run` (avoiding shell injection), concatenated arguments can still lead to argument injection (starting with `-`) or path traversal (`..`) if the called tool respects them.
**Prevention:** Implement strict path validation: decode, remove leading slashes, split by separator to check for `..`, and block arguments starting with `-`.
## 2025-12-23 - Path Traversal in Custom HTTP Handlers
**Vulnerability:** Path Traversal ([CWE-22][]) in `media-streaming/scripts/infuse-media-server.py`. The script constructed file paths for `subprocess` calls by unquoting user input and appending it to a root, without validating for `..` sequences.
**Learning:** When implementing custom request handlers (overriding `do_GET`), automatic protections provided by frameworks (like `SimpleHTTPRequestHandler.translate_path`) are bypassed. Explicit validation is required when mapping URLs to filesystem or external command paths.
**Prevention:** Always validate user-supplied paths before use. Check for `..` components after decoding. Ideally, use `os.path.abspath` and verify the path starts with the expected root directory, or reject paths containing `..` if simple validation suffices.

## 2025-12-24 - Restrict Local Service Binding
**Vulnerability:** Service bound to 0.0.0.0 exposed to LAN.
**Learning:** Default configurations or "optimizations" can inadvertently expose services to untrusted networks.
**Prevention:** Explicitly bind local-only services to 127.0.0.1.

## 2025-10-24 - Insecure Configuration Generation
**Vulnerability:** The `controld-manager` script attempted to secure the DNS listener by removing specific IPv6 wildcards but failed to explicitly enforce localhost binding, potentially leaving the service exposed if defaults changed.
**Learning:** Reliance on removing *known bad* values (denylist) is less secure than enforcing *known good* values (allowlist/enforcement) in configuration generation.
**Prevention:** When generating security-critical configurations, explicitly set the desired secure values rather than trying to sanitize the output of a tool. Verify the final configuration file content before starting the service.

## 2026-01-23 - Privilege Escalation in Helper Scripts
**Vulnerability:** `scripts/network-mode-manager.sh` (which requests `sudo`) executed a script from the local repository path relative to itself, rather than the installed system binary.
**Learning:** If a script prompts for `sudo` to run another script, using a relative path to a user-writable file (like a local repo clone) creates a privilege escalation path. A malicious actor (or the user themselves) could modify the target script and then run the wrapper, unknowingly executing the modified code as root.
**Prevention:** Helper scripts that escalate privileges should prefer executing installed, root-owned binaries (e.g., in `/usr/local/bin`) over local/relative paths.

## 2026-02-08 - Insecure File Creation in Root Scripts
**Vulnerability:** Insecure file creation ([CWE-732][] and [CWE-59][]) in `controld-system/scripts/controld-manager`. The script used `touch` followed by `chmod 600` on a log file.
**Learning:** Checking existence and setting permissions in two steps creates a race condition. If the target is a symlink ([CWE-59][]), `chmod` follows it and changes permissions of the target file.
**Prevention:** Use `umask` in a subshell (e.g., `(umask 077 && touch file)`) to create files with secure permissions atomically. Verify files are not symlinks (`-L`) before performing operations that follow them.

## 2026-02-08 - Insecure Permissions on Configuration Files
**Vulnerability:** World-readable configuration files in `/etc/controld/profiles/` containing sensitive Profile IDs.
**Learning:** Sensitive identifiers should be treated as secrets on disk to prevent unauthorized access by other local users. Inconsistency between log redaction and file permissions weakens defense in depth.
**Prevention:** Explicitly set `chmod 600` on generated configuration files and `chmod 700` on their directories immediately after creation.

## 2026-02-08 - Logic Flaw in Lock File Mechanism
**Vulnerability:** A logic flaw in `maintenance/bin/run_all_maintenance.sh` where the script checked if a directory existed but failed to handle the case where a file existed at the lock path, allowing bypass of the locking mechanism.
**Learning:** Checking for directory existence (`[[ -d ... ]]`) after `mkdir` failure is insufficient if `mkdir` fails due to a file blocking the path. The script proceeded execution, defeating the lock.
**Prevention:** Always handle the failure case explicitly. If a resource creation fails, verify *why* or exit securely. Use `mkdir` atomic creation as the primary check and ensure failure paths are handled securely (exit by default).

## 2026-02-08 - Variable Scope in Bash Loops
**Vulnerability:** Inaccurate reporting in `maintenance/bin/security_manager.sh`. The script used a pipe (`find ... | while ...`) to iterate over files and increment a counter variable. In Bash, the pipe runs the loop in a subshell, so the counter updates were lost when the loop finished.
**Learning:** Logic bugs in security tools can mask the very vulnerabilities they are meant to detect. Modifying variables inside a piped loop is a common pitfall that leads to silent failures.
**Prevention:** Use process substitution (`while ... done < <(command)`) instead of pipes when you need to modify variables in the parent shell scope from within a loop.

## 2026-02-08 - Tracked Shell History Leak
**Vulnerability:** Shell history file (`.local/share/fish/fish_history`) containing command logs was committed to the git repository.
**Learning:** Dotfiles repositories often inadvertently include sensitive history files if they are located within the tracked directory structure (e.g., XDG data dirs). Standard gitignores may miss newer XDG paths.
**Prevention:** Explicitly ignore known history paths (`.local/share/fish/fish_history`) in `.gitignore` and audit repository for sensitive files.

## 2026-02-08 - Path Traversal in Backup Restoration
**Vulnerability:** Potential path traversal ([CWE-22][]) in `maintenance/bin/security_manager.sh`. The `restore_config` function extracted tar archives without checking for directory traversal (`../`) or absolute paths in the archive entries.
**Learning:** Tar archives can contain entries with `../` or absolute paths that write files outside the intended extraction directory, potentially overwriting critical system files.
**Prevention:** Always validate tar archive contents before extraction using `tar -tf` and checking for `../` or leading `/` patterns. Reject archives with unsafe paths.

## 2026-02-09 - Information Disclosure via Hardcoded Paths
**Vulnerability:** Information Disclosure (Username) and Path Traversal in `adguard/scripts/consolidate_adblock_lists.py`. The script contained a hardcoded absolute path (`/Users/abhimehrotra/Downloads`), revealing the developer's username and making the script non-portable.
**Learning:** Hardcoded paths in scripts often contain sensitive information (usernames, project structures) and break portability. They also encourage bad security practices by relying on specific environments rather than robust configuration.
**Prevention:** Use `argparse` or environment variables to inject paths. Validate that input directories exist. Default to relative paths (like `.`) for better portability.

[CWE-22]: https://cwe.mitre.org/data/definitions/22.html
[CWE-59]: https://cwe.mitre.org/data/definitions/59.html
[CWE-78]: https://cwe.mitre.org/data/definitions/78.html
[CWE-88]: https://cwe.mitre.org/data/definitions/88.html
[CWE-732]: https://cwe.mitre.org/data/definitions/732.html

## 2026-02-10 - Command Injection in Health Check
**Vulnerability:** Command Injection ([CWE-78][]) in `maintenance/bin/health_check.sh`. The script interpolated the `HEALTH_LOG_LOOKBACK_HOURS` variable directly into a command string passed to `bash -c`, allowing arbitrary code execution if the variable contained malicious input.
**Learning:** Shell scripts that construct commands from variables are inherently risky. Sourcing configuration files (`source config.env`) without validation assumes the file is trustworthy, but environment variables can override defaults or be set maliciously if the config is missing.
**Prevention:** Always sanitize variables used in command construction. Ensure numeric values are actually integers using regex validation (`[[ "$VAR" =~ ^[0-9]+$ ]]`) before using them.

## 2026-02-12 - Symlink Attack in Config Generation
**Vulnerability:** Symlink following ([CWE-59][]) in `controld-system/scripts/controld-manager`. The script used `cp` to overwrite a configuration file without checking if the destination was a symlink.
**Learning:** `cp` follows symlinks by default when the destination exists. If an attacker can create a symlink at the destination path, running `cp` as root will overwrite the symlink's target.
**Prevention:** Remove the destination file (`rm -f`) before copying to ensure any existing symlinks are broken. Also, verify critical directories are not symlinks before use.
