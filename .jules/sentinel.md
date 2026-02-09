## 2024-05-22 - Argument Injection in Shell Wrappers
**Vulnerability:** Argument Injection (CWE-88) in `scripts/youtube-download.sh`. The script passed user input `$1` directly to `yt-dlp` without the `--` delimiter.
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
**Vulnerability:** Path traversal (CWE-22) and argument injection in `infuse-media-server.py` where untrusted path input was concatenated directly into rclone commands.
**Learning:** Even when using `subprocess.run` (avoiding shell injection), concatenated arguments can still lead to argument injection (starting with `-`) or path traversal (`..`) if the called tool respects them.
**Prevention:** Implement strict path validation: decode, remove leading slashes, split by separator to check for `..`, and block arguments starting with `-`.
## 2025-12-23 - Path Traversal in Custom HTTP Handlers
**Vulnerability:** Path Traversal (CWE-22) in `media-streaming/scripts/infuse-media-server.py`. The script constructed file paths for `subprocess` calls by unquoting user input and appending it to a root, without validating for `..` sequences.
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
**Vulnerability:** Insecure file creation (CWE-732/CWE-59) in `controld-system/scripts/controld-manager`. The script used `touch` followed by `chmod 600` on a log file.
**Learning:** Checking existence and setting permissions in two steps creates a race condition. If the target is a symlink (CWE-59), `chmod` follows it and changes permissions of the target file.
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
**Vulnerability:** Potential path traversal (CWE-22) in `maintenance/bin/security_manager.sh`. The `restore_config` function extracted tar archives without checking for directory traversal (`../`) or absolute paths in the archive entries.
**Learning:** Tar archives can contain entries with `../` or absolute paths that write files outside the intended extraction directory, potentially overwriting critical system files.
**Prevention:** Always validate tar archive contents before extraction using `tar -tf` and checking for `../` or leading `/` patterns. Reject archives with unsafe paths.

## 2026-01-23 - Hardcoded PII and Absolute Paths
**Vulnerability:** Hardcoded absolute paths containing usernames (PII) in Python utility scripts (`adguard/scripts/*.py`).
**Learning:** Developer convenience (copy-pasting working paths) often leads to non-portable and privacy-leaking code. Scripts intended for personal use often end up in shared repos without cleanup.
**Prevention:** Use `Path.home()` (pathlib) or `os.path.expanduser("~")` to reference user directories dynamically. This ensures portability and protects developer identity.

## 2026-01-24 - Credentials in Process List
**Vulnerability:** Information Disclosure (CWE-214) in `media-streaming/scripts/final-media-server.sh`. The script passed sensitive credentials (`--user`, `--pass`) as command-line arguments to `rclone serve webdav`, exposing them to any local user via `ps`.
**Learning:** Command-line arguments are visible to all users on the system via the process table.
**Prevention:** Use environment variables (e.g., `RCLONE_USER`, `RCLONE_PASS`) or file-based configuration to pass secrets to subprocesses.

## 2026-02-05 - Silent Failure of Security Hardening
**Vulnerability:** The security hardening logic in `controld-manager` relied on non-portable `sed -i ''` syntax, which would fail silently on Linux systems, leaving the configuration insecure (Open Resolver vulnerability).
**Learning:** Shell commands like `sed` and `mktemp` have platform-specific variants. Security logic that depends on these must handle portability to ensure the hardening actually executes.
**Prevention:** Use portable syntax (e.g., `sed -i.bak` followed by `rm`) or explicit OS detection when writing shell scripts that modify security configurations.

## 2026-05-22 - Daemon Scripts Bypassing Secure Defaults
**Vulnerability:** `media-server-daemon.sh` was hardcoded to bind to `0.0.0.0`, bypassing the secure options available in the interactive `final-media-server.sh`.
**Learning:** Background/Daemon scripts often get less security scrutiny than interactive ones and may hardcode insecure conveniences.
**Prevention:** Ensure daemon/service scripts inherit or duplicate the secure defaults of their interactive counterparts.
