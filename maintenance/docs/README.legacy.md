# macOS Maintenance System

A comprehensive, automated maintenance system designed to prevent system resets and keep your Mac running smoothly.

## 🎯 Purpose

This system addresses common causes of macOS instability and resets:
- **Disk pressure** (automated cleanup)
- **Memory pressure** (monitoring and alerting) 
- **Kernel panics** (detection and logging)
- **Failed launch agents** (detection and reporting)
- **Stale caches** (regular cleanup)
- **Outdated packages** (automated updates)

## 📁 Scripts Overview

### Core Scripts

1. **`health_check.sh`** - Daily comprehensive system health monitoring
   - Monitors disk space, memory pressure, kernel panics
   - Auto-triggers cleanup when disk space is critical
   - Generates detailed health reports
   - **Schedule**: Daily at 08:30

2. **`system_cleanup.sh`** - Regular disk space and cache cleanup
   - Cleans user caches, temp files, logs
   - Homebrew cleanup and verification
   - Browser cache cleanup (conservative)
   - **Schedule**: Wednesdays at 09:00

3. **`brew_maintenance.sh`** - Enhanced Homebrew maintenance
   - Updates formulae and casks (including auto-updating ones with `--greedy`)
   - Handles network failures with retry logic
   - Restarts failed Homebrew services
   - **Schedule**: Sundays at 10:00

4. **`common.sh`** - Shared library with robust error handling
   - Logging, notifications, locking, retry logic
   - Prevents multiple instances from running simultaneously

## 🔧 Configuration

Edit `~/.config/maintenance/config.env` to customize:

```bash
# System thresholds
export DISK_WARN_PCT="80"      # Warn at 80% disk usage
export DISK_CRIT_PCT="90"      # Critical at 90% disk usage
export HEALTHCHECK_AUTO_REMEDIATE="1"  # Auto-cleanup on critical disk usage

# Cleanup settings
export CLEANUP_CACHE_DAYS="30" # Clean caches older than 30 days
export TMP_CLEAN_DAYS="7"      # Clean temp files older than 7 days

# Notifications
export NOTIFY_MODE="auto"      # auto|none
export SLACK_WEBHOOK_URL=""    # Optional Slack notifications

# Package updates
export UPDATE_PIP_USER_PKGS="0"   # Conservative: don't auto-update pip packages
export UPDATE_MAS_APPS="1"        # Auto-update Mac App Store apps
```

## 🚨 Critical Features for Reset Prevention

### 1. **Proactive Disk Monitoring**
- Warns at 80% disk usage
- Auto-cleanup at 90% usage
- Prevents disk-full scenarios that cause system instability

### 2. **Kernel Panic Detection**
- Monitors system logs for panic events
- Tracks shutdown causes
- Early warning system for hardware issues

### 3. **Memory Pressure Monitoring**
- Tracks system memory pressure
- Alerts when memory usage is high
- Helps identify problematic processes

### 4. **Failed Service Detection**
- Monitors launchd services for failures
- Attempts to restart failed Homebrew services
- Prevents cascade failures

## 📊 Logs and Reports

### Log Locations
- **Main logs**: `~/Library/Logs/Maintenance/`
- **Daily health reports**: `~/Library/Logs/Maintenance/health_report-YYYYMMDD-HHMM.txt`

### Log Retention
- Logs are automatically cleaned after 60 days (configurable)
- Health reports provide point-in-time system snapshots

## 🔔 Notifications

The system sends notifications via:
1. **macOS notifications** (always)
2. **Slack** (if webhook URL configured)
3. **Google Cloud Logging** (if enabled)

## 🧪 Manual Testing

Run scripts manually to test:

```bash
# Test health check (most important)
~/Scripts/maintenance/health_check.sh

# Test system cleanup
~/Scripts/maintenance/system_cleanup.sh

# Test brew maintenance
~/Scripts/maintenance/brew_maintenance.sh
```

## 🆘 Troubleshooting

### Common Issues

1. **Script not found errors**
   ```bash
   chmod +x ~/Scripts/maintenance/*.sh
   ```

2. **Permission denied**
   ```bash
   chmod 700 ~/Scripts/maintenance
   chmod 600 ~/.config/maintenance/config.env
   ```

3. **Notifications not working**
   - Check `NOTIFY_MODE` in config.env
   - Test with: `/usr/bin/osascript -e 'display notification "Test" with title "Maintenance"'`

### Health Check Interpretation

- **Disk usage > 80%**: Warning condition, consider cleanup
- **Disk usage > 90%**: Critical, auto-cleanup triggered
- **Kernel panics > 0**: Potential hardware or driver issues
- **Failed launch agents**: Services needing attention
- **Memory pressure > 80%**: High memory usage, investigate processes

## 🔧 Current System Status

Based on your recent health check:
- ✅ **Disk usage**: 30% (healthy)
- ⚠️ **Kernel panics**: 238 in 24h (concerning - likely due to macOS beta)
- ✅ **Network**: Working
- ✅ **Battery**: 87% charging
- ✅ **SIP**: Enabled
- ⚠️ **Homebrew**: Beta OS warnings (expected)

## 📈 Next Steps

1. **Monitor daily health reports** for trends
2. **Watch kernel panic count** - if it continues high, consider filing feedback for macOS beta
3. **Consider enabling Slack notifications** for critical alerts
4. **Review logs weekly** to understand your system's patterns

The system is now actively monitoring for the conditions that typically lead to system resets!
