## 2024-05-22 - Argument Injection in Shell Wrappers
**Vulnerability:** Argument Injection (CWE-88) in `scripts/youtube-download.sh`. The script passed user input `$1` directly to `yt-dlp` without the `--` delimiter.
**Learning:** Even simple wrapper scripts can be vulnerable to RCE if they pass untrusted input to tools that accept flags (like `--exec`). The shell expands variables, but the called program parses flags.
**Prevention:** Always use `--` to separate options from positional arguments when calling CLI tools with untrusted input in shell scripts. Example: `command -opt -- "$user_input"`.
