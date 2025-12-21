# 🔧 Backup Discovery Installation Guide

This guide will help you install and configure the automated backup discovery system.

## 📋 Overview

The backup discovery LaunchAgent runs weekly (Mondays at 9:15 AM) to automatically scan for new files and directories that should be backed up.

## 🚀 Installation

### Option 1: Quick Install (Recommended)

Run the installation script:
```bash
~/Documents/dev/personal-config/maintenance/bin/install_backup_discovery.sh
```

### Option 2: Manual Installation

1. **Copy LaunchAgent**:
   ```bash
   cp ~/Documents/dev/personal-config/maintenance/launchd/com.abhimehrotra.maintenance.backupdiscovery.plist \
      ~/Library/LaunchAgents/
   ```

2. **Load LaunchAgent**:
   ```bash
   launchctl load ~/Library/LaunchAgents/com.abhimehrotra.maintenance.backupdiscovery.plist
   ```

3. **Verify Installation**:
   ```bash
   launchctl list | grep backupdiscovery
   ```

## ⏰ Schedule

- **Frequency**: Weekly
- **Day**: Monday
- **Time**: 9:15 AM (15 minutes after weekly maintenance)
- **Priority**: Low (Nice value: 10)

## 📊 Monitoring

### Check Status
```bash
launchctl list | grep backupdiscovery
```

### View Logs
```bash
# Standard output
cat ~/Library/Logs/maintenance/backup_discovery.out

# Error output
cat ~/Library/Logs/maintenance/backup_discovery.err

# View detailed reports
ls -lt ~/Library/Logs/maintenance/backup_discovery_*.log | head -5
```

### View Latest Discovery Report
```bash
ls -t ~/Library/Logs/maintenance/backup_discovery_*.log | head -1 | xargs cat
```

## 🔧 Manual Run

To run discovery manually at any time:
```bash
~/Documents/dev/personal-config/maintenance/bin/protondrive_backup_discover.sh --scan
```

## 🔄 Uninstall

If you need to remove the LaunchAgent:
```bash
launchctl unload ~/Library/LaunchAgents/com.abhimehrotra.maintenance.backupdiscovery.plist
rm ~/Library/LaunchAgents/com.abhimehrotra.maintenance.backupdiscovery.plist
```

## 📧 Notifications (Optional)

To receive notifications when new backup candidates are found, you can integrate with terminal-notifier:

1. **Install terminal-notifier** (if not already installed):
   ```bash
   brew install terminal-notifier
   ```

2. **Edit the discovery script** to add notification at the end:
   ```bash
   vim ~/Documents/dev/personal-config/maintenance/bin/protondrive_backup_discover.sh
   ```

   Add before the final section:
   ```bash
   # Send notification if candidates found
   if [ ${#candidates[@]} -gt 0 ]; then
       terminal-notifier -title \"Backup Discovery\" \
           -message \"Found ${#candidates[@]} new backup candidates\" \
           -group \"backup-discovery\"
   fi
   ```

## 🐛 Troubleshooting

### LaunchAgent Not Running

Check if it's loaded:
```bash
launchctl list | grep backupdiscovery
```

If not found, reload:
```bash
launchctl unload ~/Library/LaunchAgents/com.abhimehrotra.maintenance.backupdiscovery.plist
launchctl load ~/Library/LaunchAgents/com.abhimehrotra.maintenance.backupdiscovery.plist
```

### No Logs Generated

Check permissions:
```bash
ls -la ~/Library/Logs/maintenance/
```

Create directory if missing:
```bash
mkdir -p ~/Library/Logs/maintenance/
```

### Script Not Executing

Verify script is executable:
```bash
ls -la ~/Documents/dev/personal-config/maintenance/bin/protondrive_backup_discover.sh
```

Make executable if needed:
```bash
chmod +x ~/Documents/dev/personal-config/maintenance/bin/protondrive_backup_discover.sh
```

## 📚 Related Documentation

- [ProtonDrive Backup System](PROTONDRIVE_BACKUP.md)
- [Maintenance System README](../README.md)

