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
