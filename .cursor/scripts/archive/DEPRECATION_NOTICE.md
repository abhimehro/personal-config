# Deprecated Scripts Archive

This directory contains scripts that have been deprecated and replaced by more comprehensive solutions.

## Purpose
- **Documentation**: Preserve historical implementation details
- **Reference**: Learn from past approaches and avoid repeating mistakes
- **Audit Trail**: Maintain a record of workflow evolution

---

## Archived Scripts

### backup-configs.sh (Archived: 2025-12-21)

**Original Purpose**: Backup key configs and scripts from personal-config repo to cloud storage

**Deprecation Reason**: 
- Superseded by `maintenance/bin/protondrive_backup.sh`
- Limited scope (only backed up configs/, scripts/, controld-dns-switcher/)
- Required manual symlink management (\"backups link\")
- Created broken symlinks that caused sync errors in ProtonDrive

**Replacement**: 
- `~/Documents/dev/personal-config/maintenance/bin/protondrive_backup.sh`
- Automated via LaunchAgent: `com.abhimehrotra.maintenance.protondrivebackup.plist`

**Key Improvements in Replacement**:
1. ✅ Backs up entire home directory (Documents, Desktop, Downloads, Pictures, etc.)
2. ✅ Includes comprehensive dotfiles (.config, .zshrc, .gitconfig, etc.)
3. ✅ Automated scheduling (no manual intervention required)
4. ✅ No symlink dependencies - uses direct paths
5. ✅ Better error handling and logging
6. ✅ Excludes unnecessary files via exclude list

**Issue Identified**: 
The default `BACKUP_BASE=\"${BACKUP_BASE:-backups link}\"` created a symlink pointing to a non-existent OneDrive path (`/Users/abhimehrotra/Library/CloudStorage/OneDrive-Personal/Folders/backups link`), which caused ProtonDrive sync errors (\"No URL for file upload\").

**Lesson Learned**:
- Avoid using symlinks with cloud sync services when possible
- Always use absolute paths with proper username variables
- Comprehensive backups are better than fragmented backup scripts
- Document backup scope clearly to avoid redundant backup systems

---

## Archive Guidelines

When archiving scripts:
1. Document the deprecation date
2. Explain why it was replaced
3. Note any issues or problems encountered
4. Link to the replacement solution
5. Extract lessons learned for future reference

