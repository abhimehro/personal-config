# Control D Upgrade and Maintenance Guide

## Upgrading ctrld Binary

### Via Homebrew (Recommended)

```bash
# Check current version
ctrld --version

# Upgrade
brew upgrade ctrld

# Verify new version
ctrld --version

# Check if service is still running
sudo ctrld service status

# If service stopped, restart it
sudo ctrld service restart

# Verify everything works
~/.config/controld/health-check.sh
```

**IMPORTANT**: The launch daemon configuration (`/Library/LaunchDaemons/ctrld.plist`) persists across upgrades. The `--skip_self_checks` flag is preserved automatically.

---

## Configuration Changes

### Changing Profiles

**Edit the config file:**
```bash
nano ~/.config/controld/ctrld.toml
```

**Change the upstream in `[network.0]` section:**
```toml
[network.0]
name = "Network 0"
cidrs = ["0.0.0.0/0", "::/0"]
upstream = ["gaming_optimized"]  # Change this line
```

**Restart service:**
```bash
sudo ctrld service restart

# Wait for startup
sleep 3

# Verify
~/.config/controld/health-check.sh
```

### Adding New Profiles

**Add new upstream block:**
```toml
[upstream.3]
name = "custom_profile"
endpoint = "https://freedns.controld.com/YOUR_RESOLVER_ID"
type = "doh"
timeout = 5000
bootstrap_ip = "76.76.2.22"
```

**Restart service:**
```bash
sudo ctrld service restart
```

### Changing Bootstrap IPs

If Control D changes their bootstrap IPs:

1. Update all `bootstrap_ip` values in `ctrld.toml`
2. Restart service: `sudo ctrld service restart`
3. No changes needed to launch daemon

---

## After macOS System Updates

macOS major updates can sometimes reset system configurations. After updating:

### Step 1: Verify Service Status
```bash
sudo ctrld service status
```

If not running:
```bash
sudo ctrld service start --config ~/.config/controld/ctrld.toml --skip_self_checks
```

### Step 2: Check Firewall Exception
```bash
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --listapps | grep ctrld
```

If missing:
```bash
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /opt/homebrew/bin/ctrld
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --unblockapp /opt/homebrew/bin/ctrld
```

### Step 3: Verify Launch Daemon
```bash
sudo launchctl list | grep ctrld
```

If missing:
```bash
sudo ctrld service start --config ~/.config/controld/ctrld.toml --skip_self_checks
```

### Step 4: Full Health Check
```bash
~/.config/controld/health-check.sh
```

---

## Reinstalling from Scratch

If you need to completely reinstall:

### Step 1: Backup Configuration
```bash
mkdir -p ~/Backups/controld-$(date +%Y%m%d)
cp ~/.config/controld/ctrld.toml ~/Backups/controld-$(date +%Y%m%d)/
cp ~/.config/controld/*.md ~/Backups/controld-$(date +%Y%m%d)/
cp ~/.config/controld/health-check.sh ~/Backups/controld-$(date +%Y%m%d)/
sudo cp /Library/LaunchDaemons/ctrld.plist ~/Backups/controld-$(date +%Y%m%d)/ 2>/dev/null || true
```

### Step 2: Uninstall Completely
```bash
# Stop and remove service
sudo ctrld service uninstall

# Remove configuration
rm -rf ~/.config/controld/

# Uninstall binary
brew uninstall ctrld

# Remove firewall exception (optional)
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --remove /opt/homebrew/bin/ctrld
```

### Step 3: Reinstall
```bash
# Install binary
brew install ctrld

# Restore configuration
mkdir -p ~/.config/controld
cp ~/Backups/controld-YYYYMMDD/ctrld.toml ~/.config/controld/
cp ~/Backups/controld-YYYYMMDD/*.md ~/.config/controld/
cp ~/Backups/controld-YYYYMMDD/health-check.sh ~/.config/controld/
chmod +x ~/.config/controld/health-check.sh

# Reinstall service
sudo ctrld service start --config ~/.config/controld/ctrld.toml --skip_self_checks

# Re-add firewall exception
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /opt/homebrew/bin/ctrld
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --unblockapp /opt/homebrew/bin/ctrld

# Verify
~/.config/controld/health-check.sh
```

---

## Migrating to New Machine

### On Old Machine: Export Configuration
```bash
# Create export directory
mkdir -p ~/controld-export

# Copy all files
cp -r ~/.config/controld ~/controld-export/
sudo cp /Library/LaunchDaemons/ctrld.plist ~/controld-export/ 2>/dev/null || true

# Create archive
tar -czf ~/controld-export.tar.gz -C ~ controld-export/

# Transfer controld-export.tar.gz to new machine
```

### On New Machine: Import Configuration
```bash
# Extract archive
tar -xzf ~/Downloads/controld-export.tar.gz -C ~

# Install ctrld
brew install ctrld

# Move configuration
mkdir -p ~/.config
mv ~/controld-export/controld ~/.config/

# Install service
sudo ctrld service start --config ~/.config/controld/ctrld.toml --skip_self_checks

# Add firewall exception
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /opt/homebrew/bin/ctrld
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --unblockapp /opt/homebrew/bin/ctrld

# Verify
~/.config/controld/health-check.sh
```

---

## Protocol Changes (DoH → DoT/DoQ)

If you want to switch from DoH (DNS-over-HTTPS) to DoT (DNS-over-TLS) or DoQ (DNS-over-QUIC):

### For DoT
```toml
[upstream.0]
name = "privacy_enhanced"
endpoint = "tls://freedns.controld.com:853"
type = "dot"
timeout = 5000
bootstrap_ip = "76.76.2.22"
```

### For DoQ (if supported)
```toml
[upstream.0]
name = "privacy_enhanced"
endpoint = "quic://freedns.controld.com:8853"
type = "doq"
timeout = 5000
bootstrap_ip = "76.76.2.22"
```

**After changing:**
```bash
sudo ctrld service restart
~/.config/controld/health-check.sh
```

**NOTE**: `--skip_self_checks` remains appropriate regardless of protocol.

---

## Monitoring Integration

### Add to Weekly Maintenance

Edit `~/Public/Scripts/run_all_maintenance.sh`:

```bash
# Add near the end of the script
echo "=== Control D Service Check ==="
if [ -x "${HOME}/Public/Scripts/maintenance/controld_monitor.sh" ]; then
    "${HOME}/Public/Scripts/maintenance/controld_monitor.sh"
else
    echo "Control D monitor not found"
fi
```

### Create Daily Health Check (Optional)

Create `~/Library/LaunchAgents/com.user.controld-daily-check.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.controld-daily-check</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/abhimehrotra/Public/Scripts/maintenance/controld_monitor.sh</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/Users/abhimehrotra/Public/Scripts/controld_daily_check.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/abhimehrotra/Public/Scripts/controld_daily_check_error.log</string>
</dict>
</plist>
```

Load it:
```bash
launchctl load ~/Library/LaunchAgents/com.user.controld-daily-check.plist
```

---

## When `--skip_self_checks` Becomes Unnecessary

In future versions, if:
1. macOS firewall behavior changes, OR
2. ctrld modifies its self-check logic, OR
3. Control D changes bootstrap IP handling

You might be able to remove `--skip_self_checks`. To test:

```bash
# Uninstall current service
sudo ctrld service uninstall

# Try installing without the flag
sudo ctrld service start --config ~/.config/controld/ctrld.toml

# If it succeeds and passes health check
~/.config/controld/health-check.sh

# Then you can use the new configuration
```

Until then, `--skip_self_checks` remains the recommended configuration.

---

## Troubleshooting Upgrade Issues

### Issue: Service won't start after upgrade

**Check binary path:**
```bash
which ctrld
# Should be: /opt/homebrew/bin/ctrld

# Check launch daemon has correct path
sudo cat /Library/LaunchDaemons/ctrld.plist | grep ProgramArguments -A5
```

**If path changed, reinstall service:**
```bash
sudo ctrld service uninstall
sudo ctrld service start --config ~/.config/controld/ctrld.toml --skip_self_checks
```

### Issue: Configuration format changed

Check ctrld changelog:
```bash
brew info ctrld
```

Look for breaking changes in TOML format. Update `ctrld.toml` accordingly.

### Issue: New self-check behavior

If a new version introduces different self-check logic:
1. Try running without `--skip_self_checks` first
2. If it works, update launch daemon
3. If it fails, continue using `--skip_self_checks`

---

## Known-Good Baseline Tests

After major changes (macOS updates, ctrld upgrades, profile switches), run this minimal test suite to verify everything works:

### Baseline Test Script

Create a quick baseline check:

```bash
# ~/.config/controld/baseline-test.sh
#!/bin/bash

echo "=== Control D Baseline Tests ==="
echo ""

failed=0

# Test 1: Service running
echo -n "1. Service status... "
if sudo ctrld service status &>/dev/null; then
    echo "✓ PASS"
else
    echo "✗ FAIL"
    failed=$((failed + 1))
fi

# Test 2: DNS resolution
echo -n "2. DNS resolution... "
if dig @127.0.0.1 example.com +short +timeout=5 | grep -q "^[0-9]"; then
    echo "✓ PASS"
else
    echo "✗ FAIL"
    failed=$((failed + 1))
fi

# Test 3: DoH encryption active
echo -n "3. DoH encryption... "
if sudo tail -10 /var/log/ctrld.log | grep -q "REPLY.*upstream"; then
    echo "✓ PASS"
else
    echo "✗ FAIL"
    failed=$((failed + 1))
fi

# Test 4: Firewall exception
echo -n "4. Firewall exception... "
if sudo /usr/libexec/ApplicationFirewall/socketfilterfw --listapps | grep -q ctrld; then
    echo "✓ PASS"
else
    echo "✗ FAIL"
    failed=$((failed + 1))
fi

# Test 5: Launch daemon loaded
echo -n "5. Launch daemon... "
if sudo launchctl list | grep -q ctrld; then
    echo "✓ PASS"
else
    echo "✗ FAIL"
    failed=$((failed + 1))
fi

# Test 6: Config file valid
echo -n "6. Config file syntax... "
if [ -f ~/.config/controld/ctrld.toml ] && grep -q "\[upstream\.0\]" ~/.config/controld/ctrld.toml; then
    echo "✓ PASS"
else
    echo "✗ FAIL"
    failed=$((failed + 1))
fi

echo ""
if [ $failed -eq 0 ]; then
    echo "Result: ALL TESTS PASSED ✓"
    exit 0
else
    echo "Result: $failed test(s) FAILED ✗"
    echo "Run full health check: ~/.config/controld/health-check.sh"
    exit 1
fi
```

Make it executable:
```bash
chmod +x ~/.config/controld/baseline-test.sh
```

### When to Run Baseline Tests

**Always run after**:
1. macOS major version update (e.g., 14.x → 15.x)
2. ctrld version upgrade (`brew upgrade ctrld`)
3. Changing Control D profile
4. Switching DNS protocols (DoH → DoT)
5. Any manual edits to `ctrld.toml`

**Usage**:
```bash
# Quick baseline check
~/.config/controld/baseline-test.sh

# If all pass, you're good to go
# If any fail, run full diagnostics:
~/.config/controld/health-check.sh
```

### Post-Change Checklist

After any significant change:

```bash
# 1. Run baseline tests
~/.config/controld/baseline-test.sh

# 2. Test actual DNS query
dig example.com +short

# 3. Verify active profile (should match your config)
grep "upstream = " ~/.config/controld/ctrld.toml

# 4. Check recent logs for errors
sudo tail -20 /var/log/ctrld.log | grep -i error

# 5. If using VPN, test DNS leak
curl -s https://ipleak.net/json/ | jq -r '.dns_servers[]'
# Should NOT show ISP DNS servers
```

---

## Version Tracking

Keep track of what's working:

```bash
# Create version log
cat > ~/.config/controld/VERSION_LOG.md << EOF
# Control D Version History

## Current Configuration
- ctrld version: $(ctrld --version)
- macOS version: $(sw_vers -productVersion)
- Last updated: $(date)
- Using --skip_self_checks: YES
- Status: Working ✓

## Upgrade History
- YYYY-MM-DD: Upgraded from vX.Y.Z to vA.B.C - no issues
EOF
```

Update this file after each upgrade.

---

## Emergency Contacts

If something breaks after an upgrade:

1. **Check health**: `~/.config/controld/health-check.sh`
2. **Check logs**: `sudo tail -50 /var/log/ctrld.log`
3. **Break-glass procedure**: See `~/.config/controld/README.md`
4. **Rollback**: `brew install ctrld@<previous-version>`
5. **Community**: Control D Discord/Reddit
6. **Official support**: support@controld.com
