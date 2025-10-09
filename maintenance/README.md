# 🛠️ Automated Maintenance System

A comprehensive automated maintenance system for macOS that keeps your system clean, updated, and healthy with minimal manual intervention.

## 📊 System Status

**Current Status**: ✅ **Fully Operational**
- **Scripts**: All working and tested
- **Automation**: 5 launch agents active (exit code 0)
- **Last Update**: October 2025
- **Dependencies**: Self-contained, no external library issues

## ✨ Features

### 🔄 Automated Schedules
- **Daily Health Check**: 8:30 AM - System health monitoring
- **Daily Brew Maintenance**: 10:00 AM - Homebrew updates  
- **Daily System Cleanup**: 9:00 AM - System maintenance
- **Weekly Maintenance**: Monday 9:00 AM - Comprehensive weekly tasks
- **Monthly Maintenance**: 1st of month 6:00 AM - Deep system maintenance

### 🏥 Health Monitoring
- **Disk Usage**: Monitor and alert on disk space (currently 15%)
- **Memory Status**: Track free memory and pressure
- **System Load**: Monitor system performance
- **Launch Agents**: Check for failed services
- **Network**: Verify connectivity
- **Battery**: Monitor charging status and health
- **Software Updates**: Check for available updates
- **Crash Detection**: Monitor for recent system crashes
- **Homebrew Health**: Validate package manager status

### 🧹 System Cleaning
- **Cache Management**: Clean application and system caches
- **Downloads**: Clean old files from Downloads folder
- **Temporary Files**: Remove old temporary files
- **Browser Caches**: Clean browser cache files safely
- **Package Caches**: Clean Homebrew, npm, and other package caches
- **Log Rotation**: Manage and rotate system logs

## 🚀 Quick Start

### Manual Commands
```bash
# Run health check
~/Documents/dev/personal-config/maintenance/bin/run_all_maintenance.sh health

# Run quick cleanup
~/Documents/dev/personal-config/maintenance/bin/run_all_maintenance.sh quick

# Run weekly maintenance
~/Documents/dev/personal-config/maintenance/bin/run_all_maintenance.sh weekly

# Run monthly maintenance (comprehensive)
~/Documents/dev/personal-config/maintenance/bin/run_all_maintenance.sh monthly
```

### Check Automation Status
```bash
# View all maintenance launch agents
launchctl list | grep maintenance

# Check logs
ls ~/Library/Logs/maintenance/

# View recent health report
ls ~/Library/Logs/maintenance/health_report-*.txt | tail -1 | xargs cat
```

## 📁 Directory Structure

```
maintenance/
├── bin/                          # Executable Scripts
│   ├── run_all_maintenance.sh    # Master orchestration script
│   ├── health_check.sh           # System health monitoring
│   ├── quick_cleanup.sh          # Quick system cleanup
│   ├── brew_maintenance.sh       # Homebrew maintenance
│   ├── node_maintenance.sh       # Node.js maintenance
│   ├── onedrive_monitor.sh       # OneDrive monitoring
│   ├── system_cleanup.sh         # System cleanup
│   ├── editor_cleanup.sh         # Editor cache cleanup
│   ├── deep_cleaner.sh          # Deep system cleaning
│   ├── panic_analyzer.sh        # Kernel panic analysis
│   ├── execute_cleanup.sh       # Execution cleanup
│   └── archive/                 # Archived/broken scripts
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
1. **Daily Health Check** (`com.abhimehrotra.maintenance.healthcheck`)
   - Time: 8:30 AM daily
   - Script: `health_check.sh`
   - Purpose: System health monitoring

2. **Daily Brew Maintenance** (`com.abhimehrotra.maintenance.brew`)
   - Time: 10:00 AM daily  
   - Script: `brew_maintenance.sh`
   - Purpose: Homebrew updates

3. **Daily System Cleanup** (`com.abhimehrotra.maintenance.systemcleanup`)
   - Time: 9:00 AM daily
   - Script: `system_cleanup.sh`
   - Purpose: System maintenance

4. **Weekly Maintenance** (`com.user.maintenance.weekly`)
   - Time: Monday 9:00 AM
   - Script: `run_all_maintenance.sh weekly`
   - Purpose: Comprehensive weekly tasks

5. **Monthly Maintenance** (`com.abhimehrotra.maintenance.monthly`)
   - Time: 1st of month 6:00 AM
   - Script: `run_all_maintenance.sh monthly`
   - Purpose: Deep system maintenance

## 📊 Monitoring & Logs

### Log Locations
- **Script Logs**: `~/Library/Logs/maintenance/`
- **Health Reports**: `~/Library/Logs/maintenance/health_report-*.txt`
- **Master Logs**: `~/Documents/dev/personal-config/maintenance/tmp/`

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
launchctl list | grep -E "(maintenance|cleanup)"

# Check recent logs
ls -la ~/Library/Logs/maintenance/ | tail -10

# View latest health report
ls ~/Library/Logs/maintenance/health_report-*.txt | tail -1 | xargs cat
```

## 🔧 Troubleshooting

### Common Issues

**Launch Agent Not Running**
```bash
# Check status
launchctl list | grep maintenance

# Reload if needed
launchctl unload ~/Library/LaunchAgents/com.abhimehrotra.maintenance.healthcheck.plist
launchctl load ~/Library/LaunchAgents/com.abhimehrotra.maintenance.healthcheck.plist
```

**Script Permissions**
```bash
# Fix permissions
chmod +x ~/Documents/dev/personal-config/maintenance/bin/*.sh
```

**Log Directory Missing**
```bash
# Create log directories
mkdir -p ~/Library/Logs/maintenance
mkdir -p ~/Documents/dev/personal-config/maintenance/tmp
```

## 🔄 Updates & Maintenance

This maintenance system is self-maintaining, but you can:

1. **Update Scripts**: Pull latest versions from your personal-config repository
2. **Modify Schedules**: Edit launch agent plist files in `~/Library/LaunchAgents/`
3. **Customize Settings**: Edit `conf/config.env`
4. **Add New Scripts**: Place in `bin/` directory and update `run_all_maintenance.sh`

## 📈 Performance Impact

- **CPU Usage**: Minimal (runs during low-activity hours)
- **Disk Space**: Saves space by cleaning caches and old files
- **Network**: Minimal (only for update checks)
- **Battery**: Scheduled during charging hours when possible

## 🎯 Benefits

✅ **Automated System Health Monitoring**  
✅ **Proactive Issue Detection**  
✅ **Automatic Package Updates**  
✅ **System Cleanup & Optimization**  
✅ **Detailed Logging & Reporting**  
✅ **Zero Manual Intervention Required**  
✅ **Customizable Schedules & Settings**  

---

*Last Updated: October 2025 - System Status: Fully Operational*