# 🛠️ Automated Maintenance System

A comprehensive automated maintenance system for macOS that keeps your system
clean, updated, and healthy with minimal manual intervention.

## 📊 System Status

**Current Status**: ✅ **Fully Operational**

- **Scripts**: All working and tested with actionable notifications
- **Automation**: 9 launch agents installed by `maintenance/install.sh`
  (`com.abhimehrotra.maint.*` labels)
- **Last Update**: August 2026
- **Dependencies**: terminal-notifier (for interactive notifications)

## ⚡ Raycast Quick Actions

Use these Raycast scripts (installed under `~/Library/Maintenance/bin/`) to
trigger maintenance from the launcher:

- `raycast-brew-maintenance.sh` — Homebrew maintenance (update/upgrade/cleanup)
- `raycast-system-cleanup.sh` — System cleanup
- `raycast-document-backup.sh` — Backup Documents/Desktop/Scripts + configs
- `raycast-package-updates.sh` — Package managers (npm/pip/gem/cargo/mas)
- `raycast-dev-maintenance.sh` — Dev toolchains + cache cleanup + health check

Setup in Raycast:

1. Add a “Script Command” and point to the desired
   `~/Library/Maintenance/bin/raycast-*.sh`.
2. Optional env overrides per action:
   - `TARGET_BREW_SCRIPT` to point at a custom brew maintenance path.
   - `TARGET_CLEANUP_SCRIPT`, `TARGET_DOC_BACKUP_SCRIPT`,
     `TARGET_PACKAGE_UPDATES_SCRIPT`, `TARGET_DEV_MAINT_SCRIPT` similarly.
3. Keep scripts executable: `chmod +x ~/Library/Maintenance/bin/raycast-*.sh`.

Notes:

- These wrappers call the unified maintenance scripts shipped by
  personal-config; no dependency on the old `~/Scripts` location.
- Outputs are shown inline in Raycast; full logs remain under
  `~/Library/Logs/maintenance/` via the underlying tasks.

## Leave-alone process policy (RAM-pressure safety)

Under memory pressure, pausing or killing Apple diagnostic agents
(`ReportCrash*`) while `launchd` respawns them creates a relaunch loop (stopped
`T` processes, extreme load).

- **Policy library**: `maintenance/lib/process_exclusions.sh` (sourced by
  optimizers/monitors)
- **Crash-reporter observation only**: `scripts/report-daemons-watchdog.sh` +
  LaunchAgent `launch-agents/com.speedybee.report-daemons-watchdog.plist`; it
  never disables or kills Apple's launchd-managed reporters
- **Never automate against**: `launchd`, `kernel_task`, `WindowServer`,
  `coreaudiod`, active Spotlight (`mds*`), VM guest services, VPN/auth agents
  listed in the exclusions file
- **Eligible targets**: idle user helpers / Electron-family apps (renice or App
  Tamer AutoSlow only)

## ✨ Features

### 🔄 Automated Schedules

- Daily Health Check: 8:30 AM - System health monitoring
- Daily Service Monitor: 8:35 AM - Optimizes background services (safe mode)
- Daily System Cleanup: 9:00 AM - System maintenance
- Daily Brew Maintenance: 10:00 AM - Homebrew packages + comprehensive cask
  updates
- Daily Nag Remover: 10:00 AM - Suppresses persistent screen capture alerts
- Weekly Maintenance: Monday 9:00 AM - Comprehensive weekly tasks
- Monthly Maintenance: 1st of month 6:00 AM - Deep system maintenance
- Google Drive Backup (Light): 3:15 AM Tue–Sun — home backup light mode
- Google Drive Backup (Full): Monday 4:00 AM — fuller Google Drive backup
- ProtonDrive Backup: **archived** (`bin/archive/protondrive_backup.sh`); not
  installed by `install.sh` (use
  `macos/com.abhimehrotra.protondrive-backup.plist` only if you intentionally
  re-enable it)

### 🏥 Health Monitoring

- **Disk Usage**: Monitor and alert on disk space
- **Memory Status**: Track free memory and pressure
- **System Load**: Monitor system performance
- **Launch Agents**: Check for failed services
- **Network**: Verify connectivity
- **Battery**: Monitor charging status and health
- **Software Updates**: Check for available updates
- **Crash Detection**: Monitor for recent system crashes
- **Homebrew Health**: Validate package manager status
- **Interactive Notifications**: Click-to-view-logs for all tasks
- **Error Summaries**: Consolidated error reports with context

### 🧹 System Cleaning

- **Cache Management**: Clean application and system caches
- **Downloads**: Clean old files from Downloads folder
- **Temporary Files**: Remove old temporary files
- **Browser Caches**: Clean browser cache files safely
- **Package Caches**: Clean Homebrew, npm, and other package caches
- **Log Rotation**: Manage and rotate system logs

### 📦 Comprehensive Package Management

- **Homebrew Packages**: Regular formula updates with health checks
- **Homebrew Casks**: Auto-updating app support with `--greedy-auto-updates`
- **Version :latest Casks**: Optional updates for apps with frequent releases
- **Service Management**: Automatic restart of failed Homebrew services
- **Cache Cleanup**: Automatic pruning of old versions and cache files

## 🚀 Quick Start

### Prerequisites

```bash
# Install terminal-notifier for interactive notifications
brew install terminal-notifier
```

### Manual Commands

```bash
# Run health check
~/Library/Maintenance/bin/health_check.sh

# Run quick cleanup
~/Library/Maintenance/bin/quick_cleanup.sh

# Run weekly maintenance
~/Library/Maintenance/bin/run_all_maintenance.sh weekly

# Run monthly maintenance (comprehensive)
# Use FORCE_RUN=1 on non-1st days so editor/deep-cleaner sub-scripts also run.
FORCE_RUN=1 ~/Library/Maintenance/bin/run_all_maintenance.sh monthly

# View logs interactively
~/Library/Maintenance/bin/view_logs.sh health_check  # View health check logs
~/Library/Maintenance/bin/view_logs.sh summary       # View error summary
~/Library/Maintenance/bin/view_logs.sh weekly        # View weekly logs
```

### Check Automation Status

```bash
# View all maintenance launch agents
launchctl list | grep com.abhimehrotra

# Check logs
ls ~/Library/Logs/maintenance/

# View recent health report
ls ~/Library/Logs/maintenance/health_report-*.txt | tail -1 | xargs cat

# View latest error summary
~/Library/Maintenance/bin/view_logs.sh summary

# View specific task logs
~/Library/Maintenance/bin/view_logs.sh quick_cleanup
```

## 📁 Directory Structure

```
maintenance/
├── bin/                          # Executable Scripts
│   ├── run_all_maintenance.sh    # Master orchestration script
│   ├── weekly_maintenance.sh     # Compatibility shim to run_all_maintenance.sh weekly
│   ├── monthly_maintenance.sh    # Compatibility shim to run_all_maintenance.sh monthly
│   ├── health_check.sh           # System health monitoring
│   ├── quick_cleanup.sh          # Quick system cleanup
│   ├── brew_maintenance.sh       # Homebrew maintenance
│   ├── node_maintenance.sh       # Node.js maintenance
│   ├── google_drive_monitor.sh       # Google Drive monitoring
│   ├── system_cleanup.sh         # System cleanup
│   ├── view_logs.sh              # Interactive log viewer (NEW)
│   ├── generate_error_summary.sh # Error consolidation tool (NEW)
│   ├── smart_scheduler.sh        # Intelligent scheduling
│   └── archive/                  # Archived/broken scripts
├── conf/                        # Configuration Files
│   └── config.env              # Main configuration
├── lib/                         # Library Files
│   ├── common.sh               # Shared functions
│   └── archive/                # Archived libraries
├── tmp/                         # Temporary Files & Logs
└── docs/                        # Documentation
```

## ⚙️ Configuration

### Main Configuration (`conf/config.env`)

Key settings you can customize:

```bash
# Disk space warnings
DISK_WARN_PCT=80           # Warning threshold
DISK_CRIT_PCT=90           # Critical threshold

# Cleanup settings
CLEANUP_CACHE_DAYS=30      # Clean caches older than 30 days
TMP_CLEAN_DAYS=7           # Clean temp files older than 7 days

# Log retention
LOG_RETENTION_DAYS=60      # Keep logs for 60 days

# Package management
UPDATE_HOMEBREW=1          # Auto-update Homebrew packages
UPDATE_MAS_APPS=1          # Auto-update Mac App Store apps
```

## 📋 Launch Agent Schedules

### Active Schedules

Labels below match what `maintenance/install.sh` writes
(`com.abhimehrotra.maint.*`). That installer is authoritative: it generates
`~/Library/LaunchAgents/com.abhimehrotra.maint.*.plist` and snapshots the same
files into `maintenance/launchd/`. Older `…maintenance.*` names live under
`maintenance/launchd/archive/`. `sync-launchagents` does **not** cover this
path; it only syncs `media-streaming/launchd` and `launch-agents`.

1. **Daily Health Check** (`com.abhimehrotra.maint.healthcheck`)
   - Time: 8:30 AM daily
   - Script: `health_check.sh`
   - Purpose: System health monitoring
   - Notifications: ✅ Click to view logs

2. **Daily Brew Maintenance** (`com.abhimehrotra.maint.brew`)
   - Time: 10:00 AM daily
   - Script: `brew_maintenance.sh`
   - Purpose: Homebrew packages + comprehensive cask updates
   - Notifications: ✅ Click to view logs

3. **Daily Nag Remover** (`com.abhimehrotra.maint.screencapture-nag-remover`)
   - Time: 10:00 AM daily
   - Script: `screencapture_nag_remover.sh`
   - Purpose: Suppresses persistent macOS screen capture alerts
   - Note: Requires Full Disk Access for `/bin/bash`

4. **Daily Service Monitor** (`com.abhimehrotra.maint.servicemonitor`)
   - Time: 8:35 AM daily
   - Script: `service_monitor.sh`
   - Purpose: Disables unused background services (without killing widgets)

5. **Daily System Cleanup** (`com.abhimehrotra.maint.systemcleanup`)
   - Time: 9:00 AM daily (9:30 AM on Mondays to avoid collision)
   - Script: `system_cleanup.sh`
   - Purpose: System maintenance

6. **Weekly Maintenance** (`com.abhimehrotra.maint.weekly`)
   - Time: Monday 9:00 AM
   - Script: `run_all_maintenance.sh weekly`
   - Purpose: quick cleanup, node maintenance, Google Drive monitoring, service
     & performance optimizers
   - Notifications: ✅ Click to view error summary

7. **Monthly Maintenance** (`com.abhimehrotra.maint.monthly`)
   - Time: 1st of month 6:00 AM
   - Script: `run_all_maintenance.sh monthly`
   - Purpose: system cleanup, editor cleanup, deep cleaner
   - Notifications: ✅ Click to view error summary

8. **Google Drive Backup (Light)**
   (`com.abhimehrotra.maint.googledrivebackup.light`)
   - Time: 3:15 AM Tue–Sun
   - Purpose: Light-mode Google Drive home backup

9. **Google Drive Backup (Full)**
   (`com.abhimehrotra.maint.googledrivebackup.full`)
   - Time: Monday 4:00 AM
   - Purpose: Fuller Google Drive backup

10. **ProtonDrive Backup** (archived — not installed by `install.sh`)
    - Optional: `macos/com.abhimehrotra.protondrive-backup.plist`
    - Script: `bin/archive/protondrive_backup.sh`
    - Historical:
      `maintenance/launchd/com.abhimehrotra.maintenance.protondrivebackup.plist`

## 📊 Monitoring & Logs

### Interactive Notifications

All maintenance tasks send **interactive notifications** via terminal-notifier:

- **Click any notification** to open relevant logs in TextEdit
- **Error summaries** consolidate issues across all tasks
- **Lock context** shows concurrent execution handling
- **Actionable alerts** link directly to problem areas

### Log Locations

- **Script Logs**: `~/Library/Logs/maintenance/`
- **Error Summaries**: `~/Library/Logs/maintenance/error_summary-*.txt`
- **Lock Context**: `~/Library/Logs/maintenance/lock_context.log`
- **Health Reports**: `~/Library/Logs/maintenance/health_report-*.txt`

### Health Report Contents

```
Disk usage for /: 15%
Free memory: 58 MB
System load averages: 4.97 5.25 5.50
Kernel panic-like log entries in last 24h: 0
Launch agents: All running normally
brew doctor: System ready to brew
Outdated Homebrew packages: 0
Software updates: None available
Network connectivity: OK
Recent crash logs (last 24h): 0
Battery status: 87%; charging
```

### Checking System Status

```bash
# View launch agent status
launchctl list | grep -E 'com\.abhimehrotra'

# Check recent logs
ls -la ~/Library/Logs/maintenance/ | tail -10

# View latest health report
ls ~/Library/Logs/maintenance/health_report-*.txt | tail -1 | xargs cat
```

## 🔧 Troubleshooting

### Common Issues

**Notifications Not Working**

```bash
# Install terminal-notifier if missing
brew install terminal-notifier

# Test notification system
terminal-notifier -title "Test" -message "Click me" \
  -execute "~/Library/Maintenance/bin/view_logs.sh summary"
```

**Launch Agent Not Running**

```bash
# Check status
launchctl list | grep com.abhimehrotra

# Reload if needed
launchctl kickstart -k gui/$(id -u)/com.abhimehrotra.maint.healthcheck
```

**Script Permissions**

```bash
# Fix permissions
chmod +x ~/dev/personal-config/maintenance/bin/*.sh
```

**Log Directory Missing**

```bash
# Create log directories
mkdir -p ~/Library/Logs/maintenance
mkdir -p ~/dev/personal-config/maintenance/tmp
```

## 🔄 Updates & Maintenance

This maintenance system is self-maintaining, but you can:

1. **Update Scripts**: Pull latest versions from your personal-config repository
2. **Modify Schedules**: Edit launch agent plist files in
   `~/Library/LaunchAgents/`
3. **Customize Settings**: Edit `conf/config.env`
4. **Add New Scripts**: Place in `bin/` directory and update
   `run_all_maintenance.sh`

## 📈 Performance Impact

- **CPU Usage**: Minimal (runs during low-activity hours)
- **Disk Space**: Saves space by cleaning caches and old files
- **Network**: Minimal (only for update checks)
- **Battery**: Scheduled during charging hours when possible

## 🎯 Benefits

✅ **Automated System Health Monitoring** ✅ **Proactive Issue Detection** ✅
**Automatic Package Updates** ✅ **System Cleanup & Optimization** ✅ **Detailed
Logging & Reporting** ✅ **Zero Manual Intervention Required** ✅ **Customizable
Schedules & Settings**

---

_Last Updated: August 2026 - Align docs with `install.sh` labels; ProtonDrive
archived_
