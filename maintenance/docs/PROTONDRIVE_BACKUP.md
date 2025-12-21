# 🔐 ProtonDrive Backup System

Comprehensive automated backup solution that syncs your home directory to ProtonDrive cloud storage.

## 📋 Overview

The ProtonDrive backup system performs incremental, one-way backups from your home directory to ProtonDrive using `rsync`. This ensures your important files are safely stored in the cloud with end-to-end encryption.

### Key Features

- ✅ **Automated Daily Backups**: Runs at 3:15 AM via LaunchAgent
- ✅ **Incremental Sync**: Only changed files are transferred
- ✅ **One-Way Sync**: Source → ProtonDrive (prevents accidental deletions)
- ✅ **Comprehensive Coverage**: Backs up all critical directories and dotfiles
- ✅ **Smart Exclusions**: Skips cache files, temporary data, and system files
- ✅ **No Symlink Issues**: Uses direct paths, avoiding cloud sync conflicts

---

## 📂 What Gets Backed Up

### Core Directories
```
~/Documents       # All documents and projects
~/Desktop         # Desktop files
~/Downloads       # Downloaded files
~/Pictures        # Photos and images
~/Movies          # Videos
~/Public          # Shared files
~/Applications    # User-installed apps
~/CloudMedia      # Cloud media files
~/FontBase        # Font library
~/Backups         # Local backup archives
```

### Configuration Files (Dotfiles)
```
~/.bashrc         # Bash configuration
~/.gitconfig      # Git configuration
~/.zshrc          # Zsh shell configuration
~/.aws            # AWS credentials and config
~/.cargo          # Rust toolchain
~/.config         # Application configs
~/.filebot        # FileBot settings
~/.gemini         # Gemini configuration
~/.jules          # Jules configuration
~/.local          # Local user data
~/.vscode-R       # VS Code R extension
~/.warp           # Warp terminal settings
```

---

## 🚫 What Gets Excluded

The backup system intelligently excludes:

- **System Files**: `.DS_Store`, `.localized`, `.Spotlight-V100`
- **Cache Directories**: `**/cache/**`, `**/Cache/**`, `**/.cache/**`
- **Temporary Files**: `*.tmp`, `*.temp`, `*.swp`, `*.swo`
- **Build Artifacts**: `node_modules/`, `vendor/`, `target/`, `build/`, `dist/`
- **Package Managers**: `.npm/`, `.yarn/`, `.pnpm-store/`
- **Virtual Environments**: `venv/`, `.venv/`, `__pycache__/`
- **IDE Metadata**: `.vscode/`, `.idea/`, `.cursor/`
- **Large Media**: `*.mp4`, `*.mkv`, `*.avi` (Videos directory only)
- **Cloud Storage**: `**/Library/CloudStorage/**` (already synced)

View the complete exclusion list:
```bash
cat ~/Documents/dev/personal-config/maintenance/conf/protondrive_backup.exclude
```

---

## ⚙️ Configuration

### Location
- **Script**: `~/Documents/dev/personal-config/maintenance/bin/protondrive_backup.sh`
- **LaunchAgent**: `~/Library/LaunchAgents/com.abhimehrotra.maintenance.protondrivebackup.plist`
- **Exclusions**: `~/Documents/dev/personal-config/maintenance/conf/protondrive_backup.exclude`
- **Destination**: `~/Library/CloudStorage/ProtonDrive-abhimehro@pm.me-folder/HomeBackup/`

### Schedule
- **Frequency**: Daily
- **Time**: 3:15 AM
- **Run Mode**: `--run --no-delete` (live sync, no mirror deletions)

---

## 🔧 Manual Operations

### Run Manual Backup (Dry-Run)
```bash
~/Documents/dev/personal-config/maintenance/bin/protondrive_backup.sh
```

### Run Manual Backup (Live)
```bash
~/Documents/dev/personal-config/maintenance/bin/protondrive_backup.sh --run
```

### Check Backup Status
```bash
launchctl list | grep protondrivebackup
```

### View Logs
```bash
# Standard output
cat ~/Library/Logs/maintenance/protondrive_backup.out

# Error output
cat ~/Library/Logs/maintenance/protondrive_backup.err

# Live monitoring
tail -f ~/Library/Logs/maintenance/protondrive_backup.out
```

### Reload LaunchAgent
```bash
launchctl unload ~/Library/LaunchAgents/com.abhimehrotra.maintenance.protondrivebackup.plist
launchctl load ~/Library/LaunchAgents/com.abhimehrotra.maintenance.protondrivebackup.plist
```

---

## 🆕 Adding New Directories or Files

### Option 1: Manual Addition (Immediate)

Edit the script to add directories:
```bash
vim ~/Documents/dev/personal-config/maintenance/bin/protondrive_backup.sh
```

Add to the `CORE` array:
```bash
CORE=(
  \"$HOME/Documents\"
  \"$HOME/Desktop\"
  # ... existing entries ...
  \"$HOME/YourNewFolder\"  # Add your new directory here
)
```

Or add to the `DOTFILES` array for config files:
```bash
DOTFILES=(
  \"$HOME/.bashrc\"
  # ... existing entries ...
  \"$HOME/.yournewconfig\"  # Add your new config here
)
```

### Option 2: Dynamic Discovery (Automated)

Use the companion script for automatic detection:
```bash
~/Documents/dev/personal-config/maintenance/bin/protondrive_backup_discover.sh
```

This will:
1. Scan your home directory for new important directories
2. Detect new dotfiles and config directories
3. Generate a report of suggestions
4. Optionally update the backup script automatically

See: [Dynamic Backup Discovery](#dynamic-backup-discovery)

---

## 🔍 Dynamic Backup Discovery

The `protondrive_backup_discover.sh` script helps automatically identify new files and folders that should be backed up.

### Features
- 🔎 Scans for new directories in `$HOME` matching common patterns
- 📝 Detects new dotfiles and configuration directories
- 📊 Analyzes directory sizes and modification times
- 🤖 Auto-updates backup script (with confirmation)
- 📋 Generates detailed reports

### Usage

**Scan for new backup candidates:**
```bash
~/Documents/dev/personal-config/maintenance/bin/protondrive_backup_discover.sh --scan
```

**Auto-update backup script (with confirmation):**
```bash
~/Documents/dev/personal-config/maintenance/bin/protondrive_backup_discover.sh --update
```

**Generate detailed report:**
```bash
~/Documents/dev/personal-config/maintenance/bin/protondrive_backup_discover.sh --report
```

### Detection Criteria

**Directories are suggested if:**
- Located directly in `$HOME`
- Size > 10MB
- Modified within last 90 days
- Match patterns: `*Projects`, `*Work`, `*Dev`, `*Code`, `*Data`, etc.

**Dotfiles are suggested if:**
- Located in `$HOME` or `$HOME/.config`
- Size > 1MB or modified recently
- Match patterns: `.{app}`, `.{tool}rc`, `.{service}`, etc.

### Automated Weekly Scan

✅ **Automatically Enabled**: Discovery scans run weekly as part of the automated maintenance schedule.

The backup discovery script runs every Monday at 9:00 AM as part of the weekly maintenance workflow. Discovery results are logged to:
```
~/Library/Logs/maintenance/backup_discovery_YYYYMMDD_HHMMSS.log
```

To review recent discovery reports:
```bash
ls -lt ~/Library/Logs/maintenance/backup_discovery_*.log | head -5
```

---

## 🛡️ Safety Features

### No-Delete Mode
By default, the backup runs with `--no-delete` flag, meaning:
- Files deleted from source remain in ProtonDrive
- Prevents accidental data loss
- Allows recovery of deleted files

To enable mirror mode (delete files in backup when deleted from source):
```bash
# Edit LaunchAgent to remove --no-delete flag
vim ~/Library/LaunchAgents/com.abhimehrotra.maintenance.protondrivebackup.plist
```

### Dry-Run Testing
Always test changes with dry-run mode:
```bash
~/Documents/dev/personal-config/maintenance/bin/protondrive_backup.sh --dry-run
```

---

## 🔄 Migration from Old Backup Systems

### Deprecated: backup-configs.sh

The old `.cursor/scripts/backup-configs.sh` has been archived:

**Location**: `~/Documents/dev/personal-config/.cursor/scripts/archive/`

**Why Replaced**:
- Limited scope (only configs/scripts/controld-dns-switcher)
- Required manual symlink management
- Created broken symlinks causing ProtonDrive sync errors
- No automation

**Current System Advantages**:
1. ✅ 10x more comprehensive coverage
2. ✅ Fully automated (no manual intervention)
3. ✅ Better error handling and logging
4. ✅ Smart exclusions reduce backup size
5. ✅ No symlink dependencies

See: `~/Documents/dev/personal-config/.cursor/scripts/archive/DEPRECATION_NOTICE.md`

---

## 📊 Monitoring & Maintenance

### Check Backup Size
```bash
du -sh ~/Library/CloudStorage/ProtonDrive-abhimehro@pm.me-folder/HomeBackup/
```

### Verify Recent Backup
```bash
ls -lht ~/Library/CloudStorage/ProtonDrive-abhimehro@pm.me-folder/HomeBackup/ | head
```

### ProtonDrive Storage
Monitor your ProtonDrive storage usage through:
- ProtonDrive web interface
- ProtonDrive desktop app

Consider upgrading storage plan if approaching limit.

---

## 🐛 Troubleshooting

### Backup Not Running

**Check LaunchAgent status:**
```bash
launchctl list | grep protondrivebackup
```

**Reload LaunchAgent:**
```bash
launchctl unload ~/Library/LaunchAgents/com.abhimehrotra.maintenance.protondrivebackup.plist
launchctl load ~/Library/LaunchAgents/com.abhimehrotra.maintenance.protondrivebackup.plist
```

### ProtonDrive Sync Errors

**Common causes:**
1. Broken symlinks (check with `find ~/Library/CloudStorage/ProtonDrive-* -type l`)
2. Special characters in filenames
3. Permissions issues

**Solution:**
```bash
# Find broken symlinks
find ~/Library/CloudStorage/ProtonDrive-abhimehro@pm.me-folder -type l -exec test ! -e {} \; -print

# Remove broken symlinks
find ~/Library/CloudStorage/ProtonDrive-abhimehro@pm.me-folder -type l -exec test ! -e {} \; -delete
```

### Backup Taking Too Long

**Solutions:**
1. Review exclusion patterns
2. Exclude large media directories
3. Run manual backup to see progress:
   ```bash
   ~/Documents/dev/personal-config/maintenance/bin/protondrive_backup.sh --run
   ```

---

## 🔐 Security Considerations

- ✅ **End-to-End Encryption**: ProtonDrive encrypts all data
- ✅ **Private Keys**: SSH keys backed up (public keys only)
- ⚠️ **Credentials**: Review what gets backed up in dotfiles
- ⚠️ **Sensitive Data**: Consider excluding via exclude file

### Exclude Sensitive Files
Edit: `~/Documents/dev/personal-config/maintenance/conf/protondrive_backup.exclude`
```bash
# Add sensitive patterns
.ssh/id_*        # Private SSH keys (already excluded)
.aws/credentials # AWS credentials (consider excluding)
.env             # Environment variables with secrets
```

---

## 📚 Related Documentation

- [Maintenance System README](../README.md)
- [Weekly Maintenance](../bin/weekly_maintenance.sh)
- [Exclusion Patterns](../conf/protondrive_backup.exclude)
- [Deprecated Scripts](../../.cursor/scripts/archive/DEPRECATION_NOTICE.md)

---

## 📝 Changelog

### 2025-12-21
- ✅ Comprehensive documentation created
- ✅ Dynamic backup discovery script introduced
- ✅ Deprecated old backup-configs.sh system
- ✅ Fixed broken symlink issue causing sync errors

### 2025-11 (Initial Implementation)
- ✅ ProtonDrive backup system implemented
- ✅ LaunchAgent automation configured
- ✅ Exclusion patterns optimized
