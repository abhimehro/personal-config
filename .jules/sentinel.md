## 2026-01-05 - Insecure Temporary File Creation
**Vulnerability:** Predictable temporary filename creation in `scripts/compare_shell_configs.sh`.
**Learning:** Shell scripts using standard redirection `>` to `/tmp/filename` are vulnerable to symlink attacks if the filename is predictable.
**Prevention:** Always use `mktemp` to create temporary files with random names and safe permissions (0600).
