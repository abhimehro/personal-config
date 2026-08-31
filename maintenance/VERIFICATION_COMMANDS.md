# 🧪 Maintenance Automation - Verification Commands

Use these commands to test and verify your maintenance automation system is
working correctly.

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
./run_all_maintenance.sh weekly
```

### Monthly Orchestrator (Test all monthly tasks together)

```bash
# Test complete monthly automation (use FORCE_RUN=1 on non-1st days so
# editor_cleanup and deep_cleaner run instead of self-gating)
cd ~/Documents/dev/personal-config/maintenance/bin
FORCE_RUN=1 ./run_all_maintenance.sh monthly
```

## 🔄 Launch Agent Management

### Check Active Launch Agents

```bash
# See which maintenance agents are loaded
launchctl list | grep com.abhimehrotra

# Check specific agent status
launchctl list com.abhimehrotra.maint.healthcheck
launchctl list com.abhimehrotra.maint.weekly
launchctl list com.abhimehrotra.maint.monthly
```

### Load/Reload Launch Agents (if needed)

```bash
# Install/update all maintenance agents from the repo (preferred)
~/Documents/dev/personal-config/maintenance/install.sh

# Load individual agents from the installed LaunchAgents directory
launchctl load ~/Library/LaunchAgents/com.abhimehrotra.maint.healthcheck.plist
launchctl load ~/Library/LaunchAgents/com.abhimehrotra.maint.systemcleanup.plist
launchctl load ~/Library/LaunchAgents/com.abhimehrotra.maint.brew.plist
launchctl load ~/Library/LaunchAgents/com.abhimehrotra.maint.weekly.plist
launchctl load ~/Library/LaunchAgents/com.abhimehrotra.maint.monthly.plist
```

### Unload Launch Agents (if needed)

```bash
# Unload all maintenance agents
launchctl unload ~/Library/LaunchAgents/com.abhimehrotra.maint.*.plist
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

# View recent master maintenance log
tail -20 $(ls -t ~/Library/Logs/maintenance/maintenance_master_*.log | head -1)

# View individual task logs (timestamped per run)
ls -lt ~/Library/Logs/maintenance/{quick_cleanup,node_maintenance,google_drive_monitor,service_optimizer,performance_optimizer}_*.log | head -10
ls -lt ~/Library/Logs/maintenance/{system_cleanup,editor_cleanup,deep_cleaner}_*.log | head -10
```

### Check Launch Agent Output

```bash
# Check launch agent stdout/stderr
tail -10 ~/Library/Logs/maintenance/health_check.out
tail -10 ~/Library/Logs/maintenance/health_check.err

tail -10 ~/Library/Logs/maintenance/brew_maintenance.out
tail -10 ~/Library/Logs/maintenance/brew_maintenance.err

tail -10 ~/Library/Logs/maintenance/maintenance_weekly.out
tail -10 ~/Library/Logs/maintenance/maintenance_weekly.err

tail -10 ~/Library/Logs/maintenance/maintenance_monthly.out
tail -10 ~/Library/Logs/maintenance/maintenance_monthly.err
```

## 🕐 Schedule Verification

```bash
# Your current schedule:
echo "Daily: Health Check at 8:30 AM"
echo "Daily: System Cleanup at 9:00 AM"
echo "Daily: Homebrew Maintenance at 10:00 AM"
echo "Weekly: Maintenance at 9:00 AM Monday"
echo "Monthly: Deep Cleaning at 6:00 AM on 1st of month"

# Check next run times
launchctl list com.abhimehrotra.maint.healthcheck
launchctl list com.abhimehrotra.maint.systemcleanup
launchctl list com.abhimehrotra.maint.brew
launchctl list com.abhimehrotra.maint.weekly
launchctl list com.abhimehrotra.maint.monthly
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
3. **Verify executable permissions**:
   `chmod +x ~/Documents/dev/personal-config/maintenance/bin/*.sh`

### If launch agents aren't working:

1. **Regenerate installed agents** (preferred):
   `~/Documents/dev/personal-config/maintenance/install.sh`
2. **Check syntax of repo sample plists**:
   `plutil ~/Documents/dev/personal-config/maintenance/launchd/*.plist`
3. **Reload agents**: `launchctl unload` then `launchctl load`
4. **Check Console app** for system-level launch agent errors

### Common Issues:

- **Permission denied**: Run `chmod +x` on script files
- **Path not found**: Check `$HOME` expansion in launch agents
- **Still getting password prompts**: Verify `AUTOMATED_RUN=1` is set in
  environment variables

---

**🎉 Your maintenance automation system is fully functional and ready for
hands-off operation!**
