# Maintenance System Updates - January 2026

## 🎯 Issues Resolved

### 1. ✅ Enhanced Health Check Panic Diagnostics

**Problem:** Health check notifications showed "Issue detected: 1" and "Panics: 2" without sufficient diagnostic detail to identify root causes.

**Solution:** Enhanced `health_check.sh` with comprehensive panic analysis integration.

#### Changes Made:
- **Detailed Panic Detection**: Added logic to detect both actual panic report files and panic messages in system logs
- **File Path Resolution**: Extracts most recent panic report file path with timestamp
- **Contextual Information**: Notification now shows:
  - Number of panics detected
  - Timestamp of most recent panic
  - Direct path to panic report files
- **Actionable Notifications**: Terminal-notifier now includes:
  - "View Panic Analysis" action button
  - Executes `panic_analyzer.sh` for comprehensive analysis
  - Click-to-view functionality for full diagnostics

#### Technical Improvements:
```bash
# Before: Simple count
Panics: 2

# After: Detailed diagnostics
Panics: 2
Most recent panic: kernel-20260105-142305.panic at 2026-01-05 14:23:05
Click to view detailed panic analysis
```

#### Files Modified:
- `/Users/speedybee/Documents/dev/personal-config/maintenance/bin/health_check.sh`

#### New Notification Behavior:
- **With Panics**: Shows "View Panic Analysis" action → executes `panic_analyzer.sh`
- **No Panics**: Shows simple "System healthy" notification
- **Other Issues**: Shows "View Logs" action → opens health check logs

---

### 2. ✅ Cloud Drive Migration (OneDrive → Google Drive + Proton Drive)

**Problem:** Maintenance system was configured for OneDrive, but user migrated to Google Drive (primary) and Proton Drive (weekly backups).

**Solution:** Complete refactoring of cloud storage monitoring for new dual-drive setup.

#### Changes Made:

##### New Script: `google_drive_monitor.sh`
- **Location Detection**: Auto-detects Google Drive at:
  - `~/Library/CloudStorage/GoogleDrive-abhimhrtr@gmail.com`
- **Sync Status Monitoring**:
  - Checks for files modified in last 48 hours
  - Detects sync errors from Drive logs
  - Verifies Google Drive process is running
- **Health Checks**:
  - Directory size tracking
  - Disk space monitoring for Drive location
  - Network connectivity to drive.google.com
  - Login item verification
- **Proton Drive Integration**:
  - Companion check for recent backup activity
  - Monitors: `~/Library/CloudStorage/ProtonDrive-abhimehro@pm.me-folder/HomeBackup`
  - Alerts if no recent backup detected
- **Notifications**:
  - Issues detected: Actionable notification with log viewer
  - Normal operation: Simple status confirmation
  - Shows both Google Drive and Proton Drive status

##### Updated Script: `weekly_maintenance.sh`
- **Removed**: `onedrive_monitor.sh` task
- **Added**: `google_drive_monitor.sh` task
- Maintains weekly Monday execution schedule

##### Archived Script: `onedrive_monitor.sh`
- Moved to: `/Users/speedybee/Documents/dev/personal-config/maintenance/bin/archive/`
- Preserved for reference if needed

#### Technical Details:

**Google Drive Detection:**
```bash
GDRIVE_DIR="$HOME/Library/CloudStorage/GoogleDrive-abhimhrtr@gmail.com"
# Checks:
# - Process running (pgrep -f "Google Drive")
# - Directory exists and accessible
# - Recent file modifications (48h window)
# - Sync error logs
```

**Proton Drive Backup Verification:**
```bash
PROTON_DIR="$HOME/Library/CloudStorage/ProtonDrive-abhimehro@pm.me-folder/HomeBackup"
# Checks:
# - Recent backup activity (24h window)
# - Directory accessibility
# - File count in backup location
```

**Notification Message Format:**
```
Google Drive: Running | Sync: Active (127 files modified in last 48h)
Proton Drive Backup: Recent backup detected
```

#### Files Created/Modified:
- ✅ **Created**: `google_drive_monitor.sh`
- ✅ **Modified**: `weekly_maintenance.sh`
- ✅ **Archived**: `onedrive_monitor.sh` → `archive/onedrive_monitor.sh`

---

## 📋 Verification Steps

### Test Enhanced Health Check:
```bash
# Manual execution
~/Documents/dev/personal-config/maintenance/bin/health_check.sh

# Check for panic analysis integration
# If panics detected, notification should offer "View Panic Analysis" action
# Clicking notification executes panic_analyzer.sh
```

### Test Google Drive Monitoring:
```bash
# Manual execution
~/Documents/dev/personal-config/maintenance/bin/google_drive_monitor.sh

# Should report:
# - Google Drive status (Running/Not running)
# - Sync status with file count
# - Proton Drive backup status
# - Network connectivity
```

### Test Weekly Maintenance:
```bash
# Force run (don't wait for Monday)
FORCE_RUN=1 ~/Documents/dev/personal-config/maintenance/bin/weekly_maintenance.sh

# Should execute:
# 1. quick_cleanup.sh
# 2. node_maintenance.sh
# 3. google_drive_monitor.sh (NEW - replaces onedrive_monitor.sh)
```

---

## 🔄 Automation Schedule (Unchanged)

Your existing LaunchAgent schedules remain active:

- **Daily 8:30 AM**: Health check (now with enhanced panic diagnostics)
- **Daily 9:00 AM**: System cleanup
- **Daily 10:00 AM**: Homebrew maintenance
- **Daily 3:15 AM**: Proton Drive backup (already configured)
- **Monday 9:00 AM**: Weekly maintenance (now monitors Google Drive)
- **Monthly 6:00 AM**: Deep system maintenance

---

## 📦 Dependencies

All required tools already installed:
- ✅ `terminal-notifier` (for enhanced notifications)
- ✅ Google Drive app
- ✅ Proton Drive app
- ✅ Standard Unix utilities (find, grep, awk, etc.)

---

## 🎓 Key Improvements Summary

### Health Check Enhancement:
1. **Better Diagnostics**: Panic reports now include file paths and timestamps
2. **Actionable Alerts**: Click notification to view full panic analysis
3. **Root Cause Visibility**: No more vague "Issue detected: 1" messages
4. **Integrated Analysis**: Leverages existing `panic_analyzer.sh` tool

### Cloud Drive Migration:
1. **Dual-Drive Support**: Monitors both Google Drive (primary) and Proton Drive (backup)
2. **Comprehensive Checks**: Sync status, connectivity, disk space, error logs
3. **Automated Monitoring**: Weekly execution via existing LaunchAgent
4. **Clean Migration**: OneDrive monitoring cleanly archived

---

## 📝 Next Steps (Optional)

1. **Monitor First Automated Run**: 
   - Health check runs daily at 8:30 AM
   - Weekly maintenance runs Monday at 9:00 AM
   - Check notifications and logs for proper operation

2. **Review Logs After First Week**:
   ```bash
   # View recent logs
   ls ~/Library/Logs/maintenance/ | tail -10
   
   # Check Google Drive monitor logs
   tail -50 ~/Library/Logs/maintenance/google_drive_monitor.log
   
   # Check health check logs
   tail -50 ~/Library/Logs/maintenance/health_check.log
   ```

3. **Adjust Sync Check Window** (if needed):
   - Default: 48 hours for Google Drive activity detection
   - Configure via: `GDRIVE_SYNC_CHECK_HOURS` in `config.env`

4. **Verify Proton Drive Backup Schedule**:
   - Should run daily at 3:15 AM via existing LaunchAgent
   - Check: `com.abhimehrotra.maintenance.protondrivebackup.plist`

---

## 🔍 Troubleshooting

### If Health Check Still Shows Vague Messages:
```bash
# Check if terminal-notifier is working
terminal-notifier -title "Test" -message "Click me" -execute "echo test"

# Verify panic_analyzer.sh is executable
ls -l ~/Documents/dev/personal-config/maintenance/bin/panic_analyzer.sh

# Run health check manually to see output
~/Documents/dev/personal-config/maintenance/bin/health_check.sh
```

### If Google Drive Monitoring Fails:
```bash
# Verify Google Drive path
ls -la ~/Library/CloudStorage/GoogleDrive-abhimhrtr@gmail.com

# Check Google Drive process
pgrep -fl "Google Drive"

# Test connectivity
ping -c 3 drive.google.com

# Run monitor manually
~/Documents/dev/personal-config/maintenance/bin/google_drive_monitor.sh
```

---

## ✅ Completion Status

**All requested improvements implemented and tested:**
- ✅ Health check now provides detailed panic diagnostics
- ✅ Notifications are actionable with click-to-view analysis
- ✅ Google Drive monitoring integrated with comprehensive checks
- ✅ Proton Drive backup verification added
- ✅ OneDrive monitoring cleanly archived
- ✅ Weekly maintenance updated for new cloud setup
- ✅ All scripts executable and ready for automated runs

**No manual intervention required** - system will operate automatically on existing schedules.

---

*Updated: January 5, 2026*
*System Status: ✅ Fully Operational*
