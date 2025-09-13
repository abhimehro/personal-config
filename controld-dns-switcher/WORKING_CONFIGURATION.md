# Working Control D DNS Configuration

**Status: ✅ FULLY OPERATIONAL** (Last verified: September 13, 2025)

## Overview

This document describes the fully working Control D DNS setup that provides:
- ✅ Profile switching between Privacy and Gaming profiles
- ✅ Real DNS filtering and processing through Control D
- ✅ Raycast extension integration showing proper "Connected" status
- ✅ Low-latency gaming profile for optimal performance
- ✅ Network-aware DNS management

## System Configuration

### Hardware & OS
- **Machine**: Apple Silicon (arm64)
- **OS**: macOS 26.0 (Build 25A5351b)
- **Primary Interface**: en5 (USB 10/100/1000 LAN)
- **Shell**: Bash 3.2.57(1)-release

### Network DNS Configuration
```bash
# Primary active interface
networksetup -setdnsservers "USB 10/100/1000 LAN" 127.0.0.1

# Backup interface (Wi-Fi)
networksetup -setdnsservers "Wi-Fi" 127.0.0.1
```

**Critical**: System network interfaces MUST point to `127.0.0.1` where Control D daemon listens.

## Control D Service Architecture

### Daemon Configuration
- **Location**: `/usr/local/var/ctrld/ctrld.toml`
- **Listener**: `127.0.0.1:53` (localhost DNS port)
- **Process**: `/usr/local/bin/ctrld run --cd <profile_id> --listen 127.0.0.1:53`
- **LaunchDaemon**: `com.controld.ctrld`

### Key Scripts
1. **`controld-switcher`** (`/usr/local/bin/controld-switcher`)
   - Full-featured profile switcher with network intelligence
   - Status reporting and health checks
   - JSON output for integration

2. **`quick-dns-switch`** (`/usr/local/bin/quick-dns-switch`)
   - Reliable profile switching (recommended for automation)
   - Simplified interface
   - Better error handling for profile switches

### Profile Management
- **Privacy Profile**: Standard DNS filtering and privacy protection
- **Gaming Profile**: Low-latency DNS resolution optimized for gaming

## Service Status Files

### Runtime Status
- **Status**: `/var/run/ctrld-switcher/status.json`
  ```json
  {
    "profile": "privacy",
    "status": "active",
    "timestamp": "2025-09-13T14:01:50Z",
    "version": "3.0.0-simple",
    "resolver": "127.0.0.1:53"
  }
  ```

- **Network State**: `/var/run/ctrld-switcher/network_state.json`
  - VPN detection
  - Interface quality metrics
  - Captive portal detection

### Logs
- **Main Log**: `/var/log/ctrld-switcher/ctrld.log` (debug level)
- **Switcher Log**: `/var/log/ctrld-switcher/switcher.log`
- **Structured Log**: `/var/log/ctrld-switcher/structured.jsonl`

## Commands Reference

### Status Check
```bash
# Get current profile and status
controld-switcher status
sudo /usr/local/bin/controld-switcher status

# Check daemon process
sudo launchctl list | grep com.controld.ctrld
ps aux | grep ctrld | grep -v grep
```

### Profile Switching
```bash
# Switch to gaming profile (recommended)
sudo quick-dns-switch gaming

# Switch to privacy profile
sudo quick-dns-switch privacy

# Alternative using controld-switcher
sudo /usr/local/bin/controld-switcher gaming
sudo /usr/local/bin/controld-switcher privacy
```

### Network Diagnostics
```bash
# Verify DNS routing through Control D
dig +short google.com
dig +short @127.0.0.1 facebook.com

# Check network DNS configuration
networksetup -getdnsservers "USB 10/100/1000 LAN"
networksetup -getdnsservers "Wi-Fi"

# Verify Control D is processing queries
sudo tail -f /var/log/ctrld-switcher/ctrld.log
```

## Raycast Extension Integration

### Path Configuration
For proper Raycast detection, ensure binary is available in standard paths:
```bash
# Symlink for Apple Silicon compatibility
sudo ln -sf /usr/local/bin/controld-switcher /opt/homebrew/bin/controld-switcher

# Update PATH in shell profile
echo 'export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"' >> ~/.bash_profile
```

### Extension Status Detection
The Raycast extension should:
1. Check `/var/run/ctrld-switcher/status.json` for active status
2. Parse profile information and timestamp
3. Fall back to CLI command if JSON unavailable
4. Show "Connected" when `status: "active"`

## Troubleshooting

### Common Issues & Solutions

#### 1. "Disconnected" Status Despite Active Service
**Cause**: Network interfaces not configured to use Control D
**Solution**: 
```bash
sudo networksetup -setdnsservers "USB 10/100/1000 LAN" 127.0.0.1
sudo dscacheutil -flushcache
```

#### 2. No DNS Queries in Logs
**Cause**: DNS traffic bypassing Control D daemon
**Solution**: Verify system DNS points to 127.0.0.1

#### 3. Profile Switch Fails
**Cause**: Permission issues or daemon conflicts
**Solution**: Use `quick-dns-switch` instead of `controld-switcher`

#### 4. Raycast Extension Issues
**Cause**: PATH or permission problems
**Solution**: Ensure binary accessible without sudo in standard paths

### Verification Checklist
- [ ] `sudo launchctl list | grep com.controld.ctrld` shows running daemon
- [ ] `networksetup -getdnsservers "USB 10/100/1000 LAN"` returns `127.0.0.1`
- [ ] `dig +short google.com` resolves successfully
- [ ] `/var/log/ctrld-switcher/ctrld.log` shows recent DNS queries
- [ ] `controld-switcher status` returns JSON with `"status": "active"`
- [ ] Raycast extension shows "Connected" status

## Performance Notes

### Gaming Profile Benefits
- Reduced DNS resolution latency
- Optimized upstream routing
- Minimal filtering overhead
- Network-aware adjustments

### Why Default Launch Daemons Were Removed
The default Control D launch daemons were uninstalled because:
- Created conflicts with custom profile switching scripts
- Added unnecessary processing overhead
- Caused higher latency defeating gaming profile purpose
- Redundant with optimized manual management

Current setup provides better performance and reliability.

## Maintenance

### Regular Tasks
```bash
# Weekly log rotation check
sudo ls -la /var/log/ctrld-switcher/

# Verify DNS performance
dig +stats google.com

# Check for configuration drift
sudo controld-switcher health
```

### Updates
When updating Control D or system components:
1. Backup current configuration
2. Test DNS resolution after updates
3. Verify profile switching still works
4. Re-test Raycast extension integration

---

**Configuration Status**: ✅ Verified Working
**Last Updated**: September 13, 2025
**Profile Switching**: ✅ Operational  
**Raycast Integration**: ✅ Connected
**DNS Processing**: ✅ Active