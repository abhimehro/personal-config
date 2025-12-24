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
**Learning:**  comparison is vulnerable to timing attacks. Wildcard CORS () combined with Basic Auth allows authenticated requests from malicious origins.
**Prevention:** Use  for constant-time comparison. Remove wildcard CORS when auth is enabled or implement strict origin allowlisting.
## 2025-12-18 - Python Security Best Practices
**Vulnerability:** Timing attacks in password comparison and permissive CORS configurations.
**Learning:** `==` comparison is vulnerable to timing attacks. Wildcard CORS (`*`) combined with Basic Auth allows authenticated requests from malicious origins.
**Prevention:** Use `secrets.compare_digest()` for constant-time comparison. Remove wildcard CORS when auth is enabled or implement strict origin allowlisting.
## 2025-12-24 - Path Traversal in Custom Rclone Wrapper
**Vulnerability:** `infuse-media-server.py` passed unvalidated URL paths directly to `rclone` via `subprocess`, allowing directory traversal via `../`.
**Learning:** Custom HTTP handlers that map URLs to command-line arguments must explicitly validate paths, as they bypass standard static file server protections.
**Prevention:** Normalize and validate all user-supplied paths before passing them to subprocesses or file APIs.
