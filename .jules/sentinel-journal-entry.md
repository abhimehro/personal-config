## 2026-02-17 - TOCTOU in Backup Restoration
**Vulnerability:** Time-of-Check Time-of-Use (TOCTOU) vulnerability ([CWE-367][]) in `maintenance/bin/security_manager.sh`. The `restore_config` function verified the integrity of a backup file and then extracted it, allowing a window where the file could be modified between the check and the use.
**Learning:** File verification checks are only effective if they guarantee the file being checked is the same file being used. Operating directly on a mutable file path allows race conditions.
**Prevention:** Copy the file to a secure, private location (like a directory created with `mktemp -d`) before verification. Perform all checks and subsequent operations on this private copy to ensure atomicity.

[CWE-367]: https://cwe.mitre.org/data/definitions/367.html

## 2026-02-17 - Unintended Cloud Backup of SSH Keys
**Vulnerability:** Private SSH keys and sensitive credentials were being backed up to Google Drive by `google_drive_backup.sh` because it lacked default exclusions and failed open when configuration was missing.
**Learning:** Cloud backup scripts must have "secure by default" behavior (fail-secure), meaning they should exclude everything sensitive unless explicitly configured otherwise, or at least have a hardcoded blocklist of known sensitive patterns if configuration is missing.
**Prevention:** Always implement a fallback exclusion list in backup scripts for critical credentials (SSH keys, AWS tokens, etc.) to prevent accidental leakage if configuration files are missing.
