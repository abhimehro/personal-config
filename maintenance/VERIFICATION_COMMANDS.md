# 🧪 Maintenance Automation - Verification Commands

Use these commands to test and verify your maintenance automation system is working correctly.

## 📋 Quick System Check

```bash
# Check all maintenance scripts are present and executable
ls -la ~/Documents/dev/personal-config/maintenance/bin/*.sh

# Verify launch agents are properly formatted
plutil ~/Documents/dev/personal-config/maintenance/launchd/*.plist
```

## 🧪 Test Individual Scripts (Manual)

### Health Check (Daily Script)
```bash
# Test without password prompts
cd ~/Documents/dev/personal-config/maintenance/bin
AUTOMATED_RUN=1 ./health_check.sh
```

### Homebrew Maintenance (Weekly Script)  
```bash
# Test brew maintenance
cd ~/Documents/dev/personal-config/maintenance/bin
./brew_maintenance.sh
```

### Monthly Scripts (Test individually)
```bash
cd ~/Documents/dev/personal-config/maintenance/bin

# Test system cleanup (monthly)
FORCE_RUN=1 AUTOMATED_RUN=1 ./system_cleanup.sh

# Test editor cleanup (monthly)  
FORCE_RUN=1 AUTOMATED_RUN=1 ./editor_cleanup.sh

# Test deep cleaner (monthly) - runs longer
FORCE_RUN=1 AUTOMATED_RUN=1 ./deep_cleaner.sh
```

### Weekly Orchestrator (Test all weekly tasks together)
```bash
# Test complete weekly automation
cd ~/Documents/dev/personal-config/maintenance/bin
FORCE_RUN=1 ./weekly_maintenance.sh
```

### Monthly Orchestrator (Test all monthly tasks together)
```bash
# Test complete monthly automation
cd ~/Documents/dev/personal-config/maintenance/bin
FORCE_RUN=1 ./monthly_maintenance.sh
```

## 🔄 Launch Agent Management

### Check Active Launch Agents
```bash
# See which maintenance agents are loaded
launchctl list | grep com.abhimehrotra.maintenance

# Check specific agent status
launchctl list com.abhimehrotra.maintenance.healthcheck
```

### Load/Reload Launch Agents (if needed)
```bash
# Load all maintenance agents
launchctl load ~/Documents/dev/personal-config/maintenance/launchd/*.plist

# Or load individually
launchctl load ~/Documents/dev/personal-config/maintenance/launchd/com.abhimehrotra.maintenance.healthcheck.plist
launchctl load ~/Documents/dev/personal-config/maintenance/launchd/com.abhimehrotra.maintenance.systemcleanup.plist
launchctl load ~/Documents/dev/personal-config/maintenance/launchd/com.abhimehrotra.maintenance.brew.plist  
launchctl load ~/Documents/dev/personal-config/maintenance/launchd/com.abhimehrotra.maintenance.weekly.plist
launchctl load ~/Documents/dev/personal-config/maintenance/launchd/com.abhimehrotra.maintenance.monthly.plist
```

### Unload Launch Agents (if needed)
```bash
# Unload all maintenance agents
launchctl unload ~/Documents/dev/personal-config/maintenance/launchd/*.plist
```

## 📊 Check Logs and Results

### View Recent Logs
```bash
# Check maintenance logs directory
ls -la ~/Library/Logs/maintenance/

# View recent health check
tail -20 ~/Library/Logs/maintenance/health_check.log

# View recent brew maintenance  
tail -20 ~/Library/Logs/maintenance/brew_maintenance.log

# View weekly maintenance
tail -20 ~/Library/Logs/maintenance/weekly_maintenance.log

# View monthly maintenance
tail -20 ~/Library/Logs/maintenance/monthly_maintenance.log

# View individual monthly task logs
tail -20 ~/Library/Logs/maintenance/system_cleanup.log
tail -20 ~/Library/Logs/maintenance/editor_cleanup.log
tail -20 ~/Library/Logs/maintenance/deep_cleaner.log
```

### Check Launch Agent Output
```bash
# Check launch agent stdout/stderr
tail -10 ~/Library/Logs/maintenance/health_check.out
tail -10 ~/Library/Logs/maintenance/health_check.err

tail -10 ~/Library/Logs/maintenance/brew_maintenance.out  
tail -10 ~/Library/Logs/maintenance/brew_maintenance.err

tail -10 ~/Library/Logs/maintenance/weekly_maintenance.out
tail -10 ~/Library/Logs/maintenance/weekly_maintenance.err

tail -10 ~/Library/Logs/maintenance/monthly_maintenance.out
tail -10 ~/Library/Logs/maintenance/monthly_maintenance.err
```

## 🕐 Schedule Verification

```bash
# Your current schedule:
echo "Daily: Health Check at 8:30 AM"
echo "Daily: System Cleanup at 9:00 AM"
echo "Daily: Homebrew Maintenance at 10:00 AM"  
echo "Weekly: Comprehensive Maintenance at 9:00 AM Monday"
echo "Monthly: Deep Cleaning at 9:00 AM on 1st of month"

# Check next run times
launchctl list com.abhimehrotra.maintenance.healthcheck
launchctl list com.abhimehrotra.maintenance.systemcleanup
launchctl list com.abhimehrotra.maintenance.brew
launchctl list com.abhimehrotra.maintenance.weekly
launchctl list com.abhimehrotra.maintenance.monthly
```

## 🎯 Expected Results

- ✅ **No password prompts** during any automated execution
- ✅ **Scripts complete successfully** without `common.sh` errors  
- ✅ **Notifications appear** on macOS for completed tasks
- ✅ **Log files created** in `~/Library/Logs/maintenance/`
- ✅ **Launch agents loaded** and scheduled properly

## 🚨 Troubleshooting

### If a script fails:
1. **Check the log files** for error messages
2. **Run manually** with the test commands above
3. **Verify executable permissions**: `chmod +x ~/Documents/dev/personal-config/maintenance/bin/*.sh`

### If launch agents aren't working:
1. **Check syntax**: `plutil ~/Documents/dev/personal-config/maintenance/launchd/*.plist`
2. **Reload agents**: `launchctl unload` then `launchctl load`  
3. **Check Console app** for system-level launch agent errors

### Common Issues:
- **Permission denied**: Run `chmod +x` on script files
- **Path not found**: Check `$HOME` expansion in launch agents
- **Still getting password prompts**: Verify `AUTOMATED_RUN=1` is set in environment variables

---

**🎉 Your maintenance automation system is fully functional and ready for hands-off operation!**