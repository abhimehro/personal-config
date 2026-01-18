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

## 2024-05-22 - Argument Injection in Shell Wrappers
- **Vulnerability**: Argument Injection (CWE-88) in `scripts/youtube-download.sh`. The script passed user input `$1` directly to `yt-dlp` without the `--` delimiter.
- **Learning**: Even simple wrapper scripts can be vulnerable to RCE if they pass untrusted input to tools that accept flags (like `--exec`). The shell expands variables, but the called program parses flags.
- **Prevention**: Always use `--` to separate options from positional arguments when calling CLI tools with untrusted input in shell scripts. Example: `command -opt -- "$user_input"`.

## 2024-05-23 - Shell Script Command Injection via Eval
- **Vulnerability**: Found `retry` functions in shell libraries (`common.sh`) using `eval "$cmd"` to execute commands passed as strings.
- **Learning**: Shell scripts using `eval` on arguments are highly susceptible to command injection if the arguments are not strictly controlled.
- **Prevention**: Avoid `eval` for command execution. Use arrays `"${cmd[@]}"` to store and execute commands. Refactor functions to accept command arguments variadically (e.g., `func args...`) rather than as a single string.