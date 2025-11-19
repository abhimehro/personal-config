# Control D + Windscribe Integration Troubleshooting

## Quick Status Check

> **Note (v4.x):** The preferred way to validate modes end-to-end is via
> `./scripts/network-mode-regression.sh <profile>`. The commands in this file
> remain useful for deeper troubleshooting of the VPN + DNS integration.

Run the verification script:
```bash
bash ~/Documents/dev/personal-config/windscribe-controld/verify-integration.sh
```

## Common Issues

### Issue 1: Raycast Shows "Control D Disconnected"

**Symptoms:**
- Raycast Control D extension reports disconnected
- DNS queries not being filtered
- Ad domains resolve instead of being blocked

**Root Cause:**
Control D is configured to listen on `127.0.0.1:53` (localhost only) instead of `0.0.0.0:53` (all interfaces), preventing Windscribe from accessing it.

**Fix:**
```bash
sudo ~/Documents/dev/personal-config/windscribe-controld/fix-controld-config.sh
```

**What This Does:**
- Backs up current configuration
- Modifies Control D to listen on `0.0.0.0:53`
- Restarts Control D service
- Verifies the listener is on all interfaces

### Issue 2: Ad Blocking Not Working

**Symptoms:**
- `dig doubleclick.net +short` returns IP addresses (should return `0.0.0.0` or nothing)
- System DNS points to Windscribe servers (100.64.0.x) instead of Control D (127.0.0.1)

**Root Cause:**
Windscribe DNS mode is not set to "Local DNS"

**Fix:**
1. Open Windscribe app
2. Go to **Preferences → Connection**
3. Set **DNS** to: **Local DNS**
4. Set **App Internal DNS** to: **OS Default**
5. **Reconnect** to Windscribe

**Verification:**
```bash
# Should show 127.0.0.1 as primary DNS
scutil --dns | head -10

# Should return 0.0.0.0 or empty (blocked)
dig doubleclick.net +short

# Should resolve normally
dig google.com +short
```

### Issue 3: App Updates Fail When Connected to Windscribe

**Symptoms:**
- BetterDisplay or other apps fail to update when Windscribe is connected
- Updates work when disconnected from Windscribe
- Updates work when using Control D alone (without VPN)

**Root Cause:**
This is likely caused by one of two issues:
1. **Split Tunneling**: If enabled, can cause inconsistent DNS behavior
2. **VPN Routing**: Some update servers may be blocked or unreachable through VPN tunnel

**Diagnosis:**
Check if split tunneling is enabled:
1. Open Windscribe app
2. Go to **Preferences → Connection**
3. Check **Split Tunneling** setting

**Fix Option 1: Disable Split Tunneling (Recommended)**
- Ensures consistent DNS behavior across all apps
- All traffic uses VPN + Control D filtering
- May fix update issues by ensuring proper routing

**Fix Option 2: Add App to Split Tunnel Exceptions**
If you must use split tunneling:
1. Go to **Preferences → Connection → Split Tunneling**
2. Add the failing app (e.g., BetterDisplay) to the exception list
3. This allows the app to bypass VPN for updates

**Fix Option 3: Temporarily Disconnect for Updates**
- Disconnect from Windscribe
- Perform app updates
- Reconnect to Windscribe
- **Note**: Control D will still provide DNS filtering while disconnected

### Issue 4: Control D Service Not Running

**Check Status:**
```bash
# Check if process is running
pgrep -f ctrld

# Check listener
sudo lsof -nP -iTCP:53
```

**Restart Service:**
```bash
sudo ctrld stop
sudo ctrld start --config=/etc/controld/ctrld.toml
```

**Check Launch Daemon:**
```bash
# Check if loaded
sudo launchctl list | grep ctrld

# Reload if needed
sudo launchctl unload /Library/LaunchDaemons/ctrld.plist
sudo launchctl load /Library/LaunchDaemons/ctrld.plist
```

### Issue 5: Raycast/Apps Failing with "Network Settings Interference" or IPv6 Leaks

**Symptoms:**
- Raycast updates fail or extensions won't install
- IP location checks show inconsistent results (e.g., only IP, no location data)
- "Network Settings Interference" error from Windscribe

**Root Cause:**
1. **Corrupted Script:** The `controld-manager` script contained masked IP placeholders (`*********`) instead of real IPs, causing configuration generation to fail.
2. **IPv6 Leak:** Control D might be advertising IPv6 support (`::/0`) or AAAA records, which Windscribe (IPv4-only tunnel) drops, causing connection timeouts for apps preferring IPv6.

**Fix:**
The `controld-manager` script has been patched to use correct IPs.
Additionally, IPv6 has been disabled system-wide using `ipv6-manager.sh` which now uses `sysctl` to ignore Router Advertisements, preventing VPNs from assigning IPv6 addresses.

**Action Required:**
1. Apply the IPv6 fix:
   ```bash
   sudo ~/Documents/dev/personal-config/scripts/macos/ipv6-manager.sh disable
   ```
2. **Reconnect Windscribe** (required to drop any existing IPv6 addresses).
3. Verify Raycast updates work.

## Configuration Reference

### Correct Windscribe Settings
- **DNS**: Local DNS
- **App Internal DNS**: OS Default
- **Split Tunneling**: OFF (recommended)

### Correct Control D Configuration
Location: `/etc/controld/ctrld.toml`

Key settings:
```toml
[listener.0]
  ip = '0.0.0.0'    # Must be 0.0.0.0, not 127.0.0.1
  port = 53
```

### Expected System State
```bash
# Control D listening on all interfaces
$ sudo lsof -nP -iTCP:53
COMMAND   PID USER   FD   TYPE DEVICE SIZE/OFF NODE NAME
ctrld   34796 root   11u  IPv6  ...       0t0  TCP *:53 (LISTEN)

# System DNS pointing to Control D
$ scutil --dns | head -6
DNS configuration
resolver #1
  nameserver[0] : 127.0.0.1
  
# Ad blocking active
$ dig doubleclick.net +short
0.0.0.0

# Normal sites work
$ dig google.com +short
142.250.217.46
```

## Emergency Recovery

If nothing works and you need to restore network connectivity:

**Option 1: Stop Control D**
```bash
sudo ctrld stop
pkill -f ctrld
```

**Option 2: Reset Windscribe DNS**
```bash
# In Windscribe app:
# Set DNS to: Automatic
# Reconnect
```

**Option 3: Reset System DNS**
```bash
# Via GUI: System Settings → Network → Wi-Fi → Details → DNS
# Remove custom DNS servers and use automatic

# Via CLI:
sudo networksetup -setdnsservers Wi-Fi Empty
```

## Understanding the Integration

### DNS Query Flow (Correct Setup)
```
App → macOS → Control D (127.0.0.1:53) → Control D filters → 
Control D DoH (dns.controld.com) → Windscribe VPN tunnel → Internet
```

### Why Control D Must Listen on 0.0.0.0
- Windscribe creates a VPN tunnel interface (utun)
- When "Local DNS" is enabled, Windscribe routes DNS queries to 127.0.0.1
- BUT queries come from VPN interface, not localhost
- Control D must listen on ALL interfaces (0.0.0.0) to accept these queries
- Listening on 127.0.0.1 only accepts queries from true localhost

### Security Note
Listening on 0.0.0.0:53 is safe because:
- Port 53 is only accessible on local interfaces
- macOS firewall prevents external access
- VPN tunnel is isolated from external networks
- Control D only responds to legitimate DNS queries

## Maintenance

### Regular Health Checks
Add to your maintenance scripts:
```bash
# Check Control D + Windscribe integration
bash ~/Documents/dev/personal-config/windscribe-controld/verify-integration.sh
```

### Profile Switching
The `controld-manager` script exists but isn't in PATH. To use it:
```bash
# Check status
bash ~/Documents/dev/personal-config/controld-system/scripts/controld-manager status

# Switch profiles (if needed in future)
sudo bash ~/Documents/dev/personal-config/controld-system/scripts/controld-manager switch privacy
sudo bash ~/Documents/dev/personal-config/controld-system/scripts/controld-manager switch gaming
```

### Backup Configuration
Your current config is automatically backed up when running the fix script:
```bash
ls -lt /etc/controld/ctrld.toml.backup* | head -5
```

## Support Resources

- **Control D Docs**: https://docs.controld.com/
- **Windscribe Support**: https://windscribe.com/support
- **Your Setup Guide**: `~/Documents/dev/personal-config/windscribe-controld/setup-guide.md`
- **Verification Script**: `~/Documents/dev/personal-config/windscribe-controld/verify-integration.sh`
- **Fix Script**: `~/Documents/dev/personal-config/windscribe-controld/fix-controld-config.sh`
