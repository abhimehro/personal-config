## February 2026 - Security Hardening Sprint

### Thu Feb 13 2026: Repository Status and Automation
- **PR #217**: Added daily repository status automation workflow
  - Automated monitoring of repository health and activity
  - Integration with GitHub Actions for daily status reports
  - Co-Authored-By: GitHub Copilot

### Wed Feb 12 2026: Symlink Attack Prevention (Setup Script)
- **PR #216**: Fixed symlink hijacking vulnerability in `setup-controld.sh`
  - Replaced insecure `cp` + `chmod` + `chown` pattern with atomic `install -m 755`
  - Reduced TOCTOU (Time-of-Check-Time-of-Use) race condition windows
  - Related to [CWE-59](https://cwe.mitre.org/data/definitions/59.html) - Improper Link Resolution Before File Access
  - Co-Authored-By: GitHub Copilot

### Tue Feb 11 2026: TOCTOU Race Elimination
- **PR #215**: Eliminated TOCTOU races in `controld-manager`
  - Implemented atomic `install` command for file and directory operations
  - Added comprehensive pre-flight symlink checks for all critical paths
  - Added post-creation verification for defense-in-depth
  - Created `tests/test_symlink_protection.sh` test suite
  - Related to [CWE-362](https://cwe.mitre.org/data/definitions/362.html) - Race Condition
  - Co-Authored-By: GitHub Copilot

### Mon Feb 10 2026: Symlink Attack Hardening
- **PR #213**: Hardened `controld-manager` against symlink attacks
  - Replaced `mkdir -p` + `chmod` with atomic `install -d -m 700`
  - Replaced `rm -f` + `cp` + `chmod` with atomic `install -m 600`
  - Added symlink detection for configuration directories and files
  - Improved configuration file permission security (chmod 600)
  - Related to [CWE-59](https://cwe.mitre.org/data/definitions/59.html) - Improper Link Resolution Before File Access
  - Co-Authored-By: GitHub Copilot

### Recent UX Improvements
- Enhanced network menu with active state indicators (✅ checkmarks)
- Improved maintenance CLI with help system and duration tracking
- Fixed hardcoded path exposure in AdGuard consolidation script

---

## Previous Changes

- Fri Sep 26 06:19:05 CDT 2025: Updated configs - c632ab1 Add comprehensive macOS maintenance system - Friday victory
- Tue Oct  7 18:35:37 CDT 2025: Updated configs - dbb0150 Add WORKING Control D system configuration
- Tue Oct  7 18:35:59 CDT 2025: Updated configs - b8ab65f Clean up repository - remove all old DNS configurations
- Tue Oct  7 18:44:46 CDT 2025: Updated configs - 3e8e13c Clean up repository - remove all old DNS configurations
- Tue Oct  7 18:44:47 CDT 2025: Updated configs - 3e8e13c Further clean up repository - remove DNS config references from documentation
- Tue Oct  7 18:46:04 CDT 2025: Updated configs - be4530b Update CHANGELOG.md and add missing validation script
- Tue Oct  7 19:06:44 CDT 2025: Updated configs - 88061a8 Update CHANGELOG.md with recent repository cleanup changes
- Tue Oct  7 19:10:01 CDT 2025: Updated configs - 2d321ed Update CHANGELOG.md with recent repository cleanup changes
- Tue Oct  7 19:19:50 CDT 2025: Updated configs - 984a4d7 Update CHANGELOG.md with latest commit entry
- Tue Oct  7 19:21:14 CDT 2025: Updated configs - a84c407 Merge branch 'update-changelog' into main

Resolve conflicts in CHANGELOG.md and scripts/validate-configs.sh:
- Combined all CHANGELOG entries in chronological order
- Merged validation script with both set -euo pipefail and comments
- Tue Oct  7 19:21:33 CDT 2025: Updated configs - 4890fb0 Update CHANGELOG.md with merge commit details
- Tue Oct  7 19:21:48 CDT 2025: Updated configs - b465780 Final CHANGELOG.md update after merge resolution
- Tue Oct  7 19:22:02 CDT 2025: Updated configs - 26574eb Update CHANGELOG.md after branch cleanup
