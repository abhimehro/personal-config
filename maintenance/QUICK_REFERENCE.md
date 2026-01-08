# 🚀 Maintenance System - Quick Reference

## 📋 Essential Commands

### Daily Operations
```bash
# Health Check (2-3 minutes)
~/Documents/dev/personal-config/maintenance/bin/run_all_maintenance.sh health

# Quick Cleanup (1-2 minutes)  
~/Documents/dev/personal-config/maintenance/bin/run_all_maintenance.sh quick
```

### Weekly/Monthly Operations
```bash
# Weekly Maintenance (5-10 minutes)
~/Documents/dev/personal-config/maintenance/bin/run_all_maintenance.sh weekly

# Monthly Deep Clean (10-20 minutes)
~/Documents/dev/personal-config/maintenance/bin/run_all_maintenance.sh monthly
```

## 📊 System Monitoring

### Check Status
```bash
# Launch agents status
launchctl list | grep maintenance

# Recent logs
ls -la ~/Library/Logs/maintenance/ | tail -5

# Latest health report
ls ~/Library/Logs/maintenance/health_report-*.txt | tail -1 | xargs cat
```

### Current Automation Schedule
- **3:15 AM Daily**: Google Drive Backup (Light Archives)
- **3:30 AM Monday**: Google Drive Backup (Full Archives)
- **8:30 AM Daily**: Health Check
- **9:00 AM Daily**: System Cleanup
- **10:00 AM Daily**: Homebrew Updates
- **Monday 9:00 AM**: Weekly Maintenance
- **1st of Month 6:00 AM**: Monthly Deep Clean

## 🔧 Troubleshooting

### Restart Launch Agents
```bash
# Restart health check
launchctl unload ~/Library/LaunchAgents/com.abhimehrotra.maintenance.healthcheck.plist
launchctl load ~/Library/LaunchAgents/com.abhimehrotra.maintenance.healthcheck.plist
```

### Fix Permissions
```bash
chmod +x ~/Documents/dev/personal-config/maintenance/bin/*.sh
```

### Create Missing Directories
```bash
mkdir -p ~/Library/Logs/maintenance
mkdir -p ~/Documents/dev/personal-config/maintenance/tmp
```

## 📈 Current System Health

**As of Last Check:**
- ✅ Disk Usage: 15% (healthy)
- ✅ Homebrew: 0 outdated packages  
- ✅ Network: Connected
- ✅ Launch Agents: All running (exit code 0)
- ✅ Battery: 87% and charging
- ✅ Software Updates: None available

---
*For detailed information, see the full [README.md](README.md)*