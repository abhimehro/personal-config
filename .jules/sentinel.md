# Sentinel Security Log

## 2025-10-24 - Hardcoded Credentials in Media Server

- **Vulnerability**: Hardcoded password `mediaserver123` found in `media-streaming/scripts/start-media-server.sh` and its generator script. The script also bound to `0.0.0.0` by default.
- **Learning**: Convenience scripts often sacrifice security. Hardcoding credentials in "setup" scripts propagates vulnerabilities to user environments.
- **Prevention**: Never hardcode passwords. Use secure random generation (e.g., `openssl rand`) during setup or first run, and store them in a protected configuration file (e.g., `~/.config/...` with `chmod 600`).

## 2025-12-23 - Unprotected SSH Keys in CI/CD

- **Vulnerability**: CI/CD workflow `github-actions.yml` copied SSH keys from a secret variable directly into `~/.ssh/id_rsa` without restricting permissions (default 644) or clearing the file after use.
- **Learning**: Ephemeral environments are not secure by default. Secrets persisted to disk in world-readable formats can be harvested by other steps or malicious dependencies.
- **Prevention**: Use `ssh-agent` to hold keys in memory. If disk writes are necessary, set `umask 077` before writing or `chmod 600` immediately after. Clean up secrets in a `always()` block.

## 2025-12-20 - Insecure Defaults in Docker Compose

- **Vulnerability**: `docker-compose.yml` for the web service exposed the database port `5432` to the host (`0.0.0.0:5432`) instead of binding to localhost (`127.0.0.1:5432`) or keeping it internal.
- **Learning**: Default port mappings in Docker (e.g., `5432:5432`) expose services to the external network interface if the host firewall is permissive.
- **Prevention**: Explicitly bind internal services to localhost (e.g., `127.0.0.1:5432:5432`) or omit the `ports` section entirely if only inter-container communication is needed.

## 2025-12-18 - Shell Injection via Unquoted Variables

- **Vulnerability**: Command Injection (CWE-78) in `scripts/deploy.sh`. The script used `git checkout $BRANCH_NAME` without quotes. A branch named `; rm -rf /;` would execute the payload.
- **Learning**: Shell variables expanded in command arguments are interpreted by the shell. Malicious input can inject arbitrary commands.
- **Prevention**: Always quote variables (e.g., `"$BRANCH_NAME"`). Use `shellcheck` in CI to catch these.

## 2025-10-18 - Path Traversal in File Upload

- **Vulnerability**: Path Traversal (CWE-22) in `server/upload.js`. The endpoint used `path.join(uploadDir, req.body.filename)` without validating that the result was still inside `uploadDir`.
- **Learning**: Filenames from users are untrusted input. `../` sequences allow writing anywhere the process has permissions.
- **Prevention**: Normalize the path and verify it starts with the expected directory prefix. Use `path.basename()` to strip directory components from uploaded filenames.

## 2025-10-21 - Unrestricted File Upload

- **Vulnerability**: Unrestricted File Upload (CWE-434) in `server/profile.js`. Users could upload `.php` or `.sh` files, which the web server might execute if misconfigured.
- **Learning**: Checking file extensions on the client side is useless. Checking MIME types is insufficient. Executable files in upload directories lead to RCE.
- **Prevention**: Whitelist allowed extensions (e.g., `.jpg`, `.png`). Store uploads outside the web root. Configure the web server to serve uploads as static content (no execution).

## 2025-10-21 - Command Injection in Notification System

- **Vulnerability**: Found unsanitized input being passed to `eval` in `smart_notify` function.
- **Learning**: Even internal helper scripts can be vulnerable if they construct commands via string concatenation and use `eval`. Inputs like notification titles might come from external sources (logs, filenames) and trigger execution.
- **Prevention**: Avoid `eval`. Use direct command execution. If constructing complex arguments, verify quoting or use arrays. For AppleScript, escape quotes and backslashes.

## 2025-10-18 - Insecure Local Media Sharing

- **Vulnerability**: The `media-streaming/scripts/alldebrid-server.py` and `infuse-media-server.py` scripts expose the file system via HTTP on `0.0.0.0` without authentication.
- **Learning**: These scripts are designed for local network sharing (Infuse integration) but lack basic security controls, relying solely on network trust. This is a significant gap if the device connects to untrusted networks.
- **Prevention**: Always bind to `127.0.0.1` by default for development/local tools. If public/LAN access is needed, enforce authentication (Basic Auth or similar) or use secure tunneling.

## 2025-10-21 - Secure Defaults in Python HTTP Servers

- **Vulnerability**: Python's `http.server.SimpleHTTPRequestHandler` provides no security controls and binds to all interfaces by default if not restricted.
- **Learning**: Simple tools often sacrifice security for convenience. Implementing Basic Auth in Python requires manually handling headers and decoding Base64.
- **Prevention**: Use a wrapper class to enforce authentication. Use `secrets` module for secure password generation. Bind to `127.0.0.1` by default and require explicit flags for public binding.

## 2025-12-18 - Python Security Best Practices

- **Vulnerability**: Timing attacks in password comparison and permissive CORS configurations.
- **Learning**: `==` comparison is vulnerable to timing attacks. Wildcard CORS (`*`) combined with Basic Auth allows authenticated requests from malicious origins.
- **Prevention**: Use `secrets.compare_digest()` for constant-time comparison. Remove wildcard CORS when auth is enabled or implement strict origin allowlisting.

## 2025-12-20 - Path Traversal in Media Server

- **Vulnerability**: Path traversal (CWE-22) and argument injection in `infuse-media-server.py` where untrusted path input was concatenated directly into rclone commands.
- **Learning**: Even when using `subprocess.run` (avoiding shell injection), concatenated arguments can still lead to argument injection (starting with `-`) or path traversal (`..`) if the called tool respects them.
- **Prevention**: Implement strict path validation: decode, remove leading slashes, split by separator to check for `..`, and block arguments starting with `-`.

## 2025-12-23 - Path Traversal in Custom HTTP Handlers

- **Vulnerability**: Path Traversal (CWE-22) in `media-streaming/scripts/infuse-media-server.py`. The script constructed file paths for `subprocess` calls by unquoting user input and appending it to a root, without validating for `..` sequences.
- **Learning**: When implementing custom request handlers (overriding `do_GET`), automatic protections provided by frameworks (like `SimpleHTTPRequestHandler.translate_path`) are bypassed. Explicit validation is required when mapping URLs to filesystem or external command paths.
- **Prevention**: Always validate user-supplied paths before use. Check for `..` components after decoding. Ideally, use `os.path.abspath` and verify the path starts with the expected root directory, or reject paths containing `..` if simple validation suffices.

## 2025-10-14 - Stored XSS in Media Server

- **Vulnerability**: The `infuse-media-server.py` script was vulnerable to Stored XSS. Filenames and directory paths obtained from `rclone` were inserted directly into the HTML response without escaping. An attacker with the ability to create files on the media source could execute arbitrary JavaScript in the context of the user viewing the directory listing.
- **Learning**: Directory listing tools that output HTML must always treat filenames as untrusted input and escape them. Even if the source is considered "internal" (like a file system), filenames can be crafted to contain malicious payloads.
- **Prevention**: Always use `html.escape()` when inserting data into HTML context. Implement Content Security Policy (CSP) headers to mitigate the impact of XSS vulnerabilities.

## 2024-05-22 - Argument Injection in Shell Wrappers

- **Vulnerability**: Argument Injection (CWE-88) in `scripts/youtube-download.sh`. The script passed user input `$1` directly to `yt-dlp` without the `--` delimiter.
- **Learning**: Even simple wrapper scripts can be vulnerable to RCE if they pass untrusted input to tools that accept flags (like `--exec`). The shell expands variables, but the called program parses flags.
- **Prevention**: Always use `--` to separate options from positional arguments when calling CLI tools with untrusted input in shell scripts. Example: `command -opt -- "$user_input"`.

## 2024-05-23 - Shell Script Command Injection via Eval

- **Vulnerability**: Found `retry` functions in shell libraries (`common.sh`) using `eval "$cmd"` to execute commands passed as strings.
- **Learning**: Shell scripts using `eval` on arguments are highly susceptible to command injection if the arguments are not strictly controlled.
- **Prevention**: Avoid `eval` for command execution. Use arrays `"${cmd[@]}"` to store and execute commands. Refactor functions to accept command arguments variadically (e.g., `func args...`) rather than as a single string.

## 2025-05-23 - Insecure Global SSH Forwarding

- **Vulnerability**: Global `ForwardAgent yes` and `ForwardX11Trusted yes` found in `configs/ssh/config`.
- **Learning**: Global configuration files in dotfiles repositories can inadvertently expose users to agent hijacking and X11 attacks when connecting to any host, not just trusted ones.
- **Prevention**: Disable forwarding (`ForwardAgent no`, `ForwardX11 no`) by default in the `Host *` section. Enable them only for specific, trusted `Host` entries where necessary.
