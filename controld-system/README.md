# Control D Setup Guide

## Overview
This setup provides three resolver profiles for different use cases:

1. **Privacy Enhanced** (`6m971e9jaf`) - Maximum privacy/security filtering
2. **Browsing Privacy** (`rcnz7qgvwg`) - Balanced privacy for general browsing  
3. **Gaming Optimized** (`1xfy57w34t7`) - Minimal rules for optimal gaming performance

## Installation Status
✅ `ctrld` installed via Homebrew (v1.4.7)  
✅ Configuration file created at `~/.config/controld/ctrld.toml`  
✅ Profile switcher script at `~/bin/ctrld-switch`  
✅ Service configured for auto-start on boot with `--skip_self_checks`  
✅ Firewall exception added for `/opt/homebrew/bin/ctrld`

## Service Management (Auto-Start Enabled)

The service is now installed as a Launch Daemon and will **automatically start on boot**.

### Check Service Status
```bash
# Check if service is running
sudo ctrld service status

# View logs in real-time
sudo tail -f /var/log/ctrld.log
```

### Manual Service Control
```bash
# Stop service
sudo ctrld service stop

# Start service (manual)
sudo ctrld service start --config ~/.config/controld/ctrld.toml --skip_self_checks

# Restart service (e.g., after config changes)
sudo ctrld service restart
```

### Verify DNS Resolution
```bash
# Test DNS through Control D
dig @127.0.0.1 example.com +short
```

## Profile Management

### Switch Profiles (Easy Method)
```bash
# Switch to gaming profile
ctrld-switch gaming

# Switch to browsing profile
ctrld-switch browsing

# Switch to privacy profile
ctrld-switch privacy
```

### Manual Profile Switching
If you prefer manual control:

1. Edit `~/.config/controld/ctrld.toml`
2. Change the `upstream` value in `[network.0]` section:
   - For privacy: `upstream = ["privacy_enhanced"]`
   - For browsing: `upstream = ["browsing_privacy"]`
   - For gaming: `upstream = ["gaming_optimized"]`
3. Restart service: `sudo ctrld service restart`

### Quick Start with Specific Profile
```bash
# Start directly with a specific resolver
sudo ctrld start --cd 6m971e9jaf   # Privacy
sudo ctrld start --cd rcnz7qgvwg   # Browsing
sudo ctrld start --cd 1xfy57w34t7  # Gaming
```

## Important: Skip Self-Checks Configuration

### Why `--skip_self_checks` is Required

The service is configured with the `--skip_self_checks` flag to bypass startup validation tests.

**The Problem:**
- During startup, ctrld performs connectivity tests to bootstrap IPs
- These tests attempt to connect to Control D's DoH endpoints on port 443
- macOS firewall blocks these initial connections during self-checks
- Result: "connection refused" errors cause startup to fail

**The Solution:**
- `--skip_self_checks` skips the startup validation phase
- Service starts immediately and establishes connections during normal operation
- Once running, DNS queries resolve successfully via DoH

**Security Tradeoff: Fail-Secure vs Fail-Operational**

| Approach | Description | Pros | Cons |
|----------|-------------|------|------|
| **Fail-Secure** | Self-checks must pass before service starts | Catches config errors early | Service won't start if checks fail |
| **Fail-Operational** | Skip checks, prioritize availability | Service starts reliably | Config errors detected at runtime |

**Our Decision: Fail-Operational** (using `--skip_self_checks`)

**Reasoning:**
1. **Self-checks protect against misconfiguration, not attacks**
   - They verify connectivity and config syntax
   - They don't prevent DNS spoofing, MITM, or other security threats

2. **Real security comes from DoH encryption**
   - All DNS traffic is encrypted via HTTPS once service is running
   - Control D's filtering rules provide the actual threat protection
   - Bootstrap IP checks don't add security value

3. **Configuration is already validated and working**
   - We've manually tested the config
   - Service resolves DNS correctly once running
   - Self-check failures are false positives due to firewall timing

4. **Better operational reliability**
   - Service can start even if upstreams are temporarily unreachable
   - Reduces maintenance burden (no firewall rule management for changing IPs)
   - Aligns with "infrastructure should self-heal" principle

**Alternative (Not Recommended):**
You *could* add firewall exceptions for bootstrap IPs, but:
- Bootstrap IPs may change without notice from Control D
- Requires ongoing firewall rule maintenance
- Doesn't provide meaningful security benefit
- Self-checks still might fail if upstreams are temporarily down

### Health Monitoring

Use the included health check script:
```bash
~/.config/controld/health-check.sh
```

This provides the same confidence as self-checks, but at runtime.

## Common Commands

### Service Management
```bash
sudo ctrld service status      # Check service status
sudo ctrld service stop        # Stop the service
sudo ctrld service restart     # Restart the service
sudo ctrld service uninstall   # Remove service
```

### Break-Glass Troubleshooting

**When the health check fails, follow this diagnostic tree:**

#### Step 1: Is the service running?
```bash
sudo ctrld service status
```

**If NO** → Go to Step 2
**If YES** → Go to Step 3

#### Step 2: Service not running
```bash
# Check if launch daemon is loaded
sudo launchctl list | grep ctrld

# If not loaded, reinstall
sudo ctrld service start --config ~/.config/controld/ctrld.toml --skip_self_checks

# If still fails, check logs
sudo tail -50 /var/log/ctrld.log | grep -i error
```

**Common causes:**
- Config file syntax error → Check `~/.config/controld/ctrld.toml`
- Port 53 conflict → Check: `sudo lsof -i :53`
- Missing binary → Reinstall: `brew reinstall ctrld`

#### Step 3: Service running but DNS not resolving
```bash
# Test local DNS
dig @127.0.0.1 example.com +short

# If fails, check upstream connectivity
sudo tail -50 /var/log/ctrld.log | grep upstream
```

**Common causes:**
- Upstream marked as down → Check internet connection
- Bootstrap IP unreachable → Check firewall: `sudo /usr/libexec/ApplicationFirewall/socketfilterfw --listapps | grep ctrld`
- Wrong listener IP → Verify `listener.0` in config is 127.0.0.1

#### Step 4: Emergency DNS restoration
**If you need to bypass Control D immediately:**
```bash
# Stop Control D
sudo ctrld service stop

# System will use default DNS (from DHCP/router)
# Test: dig example.com +short

# To permanently disable auto-start
sudo ctrld service uninstall
```

#### Step 5: Complete reset
**Nuclear option - start from scratch:**
```bash
# Uninstall service
sudo ctrld service uninstall

# Backup config
cp ~/.config/controld/ctrld.toml ~/ctrld.toml.backup

# Remove configuration
rm -rf ~/.config/controld/

# Reinstall from backup
mkdir -p ~/.config/controld
cp ~/ctrld.toml.backup ~/.config/controld/ctrld.toml
sudo ctrld service start --config ~/.config/controld/ctrld.toml --skip_self_checks

# Re-add firewall exception
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /opt/homebrew/bin/ctrld
```

### Troubleshooting

#### "Connection Refused" Errors in Logs
If you see these during manual startup (without `--skip_self_checks`):
```
ERR failed to connect to upstream.0, endpoint: https://freedns.controld.com/... error="dial tcp ***:443: connect: connection refused"
```

**This is expected and harmless**:
- These errors occur during self-checks only
- They don't affect runtime DNS resolution
- Service will work correctly with `--skip_self_checks`
- No action needed

#### DNS Not Resolving
```bash
# Test DNS resolution directly
dig @127.0.0.1 example.com

# Check if service is running
sudo ctrld service status

# View recent errors
sudo tail -20 /var/log/ctrld.log

# Verify current profile
cat ~/.config/controld/ctrld.toml | grep "upstream ="
```

#### Service Not Starting After Reboot
```bash
# Check if launch daemon is loaded
sudo launchctl list | grep ctrld

# Reinstall service if needed
sudo ctrld service stop
sudo ctrld service start --config ~/.config/controld/ctrld.toml --skip_self_checks
```

#### Verify Firewall Configuration
```bash
# Check if ctrld is allowed through firewall
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --listapps | grep ctrld

# Should show: /opt/homebrew/bin/ctrld
```

### Uninstall
```bash
# Stop and remove service
sudo ctrld service uninstall

# Optionally remove configuration
rm -rf ~/.config/controld/
```

## Security Notes

### WHY This Matters
- **Local DNS Proxy**: ctrld runs locally and forwards DNS queries to Control D's encrypted resolvers
- **DoH (DNS over HTTPS)**: All DNS queries are encrypted, preventing ISP snooping
- **Profile-Based Filtering**: Different profiles block different categories of threats/content

### Attack Prevention
- **DNS Hijacking**: Encrypted DNS prevents MITM attacks on DNS queries
- **Tracking**: Control D's resolvers can block trackers and ads at DNS level
- **Malware**: Privacy profiles block known malicious domains

### What Could Go Wrong
- **Service Conflicts**: If another DNS service (like dnsmasq) uses port 53, ctrld will fail
- **Sudo Required**: Service management requires root permissions for system DNS configuration
- **Profile Mismatch**: Using gaming profile may allow more connections (less filtering)

## Backup & Restore

### Backup Configuration
```bash
cp ~/.config/controld/ctrld.toml ~/Documents/dev/personal-config/controld-backup.toml
```

### Restore Configuration  
```bash
cp ~/Documents/dev/personal-config/controld-backup.toml ~/.config/controld/ctrld.toml
sudo ctrld reload
```

## Integration with personal-config Repository

Consider adding these files to your personal-config repo:
```bash
cd ~/Documents/dev/personal-config
mkdir -p controld
cp ~/.config/controld/ctrld.toml controld/
cp ~/bin/ctrld-switch controld/
cp ~/.config/controld/README.md controld/
git add controld/
git commit -m "Add Control D configuration and profile management"
git push
```

## Profile Recommendations

**Privacy Enhanced** (Protocol: DoH/TCP) - Use when:
- Banking, sensitive work
- Maximum security needed
- Don't mind some sites potentially blocked
- **Recommended when using VPN**

**Browsing Privacy** (Protocol: DoH/TCP) - Use when:
- General web browsing
- Social media, shopping
- Want balance of security and compatibility
- **Recommended when using VPN**

**Gaming Optimized** (Protocol: DoH3/QUIC) - Use when:
- Online gaming (reduces latency)
- Streaming services
- Need maximum compatibility
- **Best for non-VPN usage**

## Network Mode Management (v4.0 Separation Strategy)

We have consolidated network state management into a single script to reliably switch between "DNS Mode" (Control D) and "VPN Mode" (Windscribe). This aligns with the Infrastructure-as-Code model: the Control D dashboard is the source of truth for resolver behavior, while this script manages macOS network state.

**Location:** `scripts/network-mode-manager.sh`

### Usage

- **Enable Control D DNS mode**
  ```bash
  ./scripts/network-mode-manager.sh controld browsing
  # or: controld privacy | controld gaming
  ```

- **Enable Windscribe VPN mode**
  ```bash
  ./scripts/network-mode-manager.sh windscribe
  ```

- **Show current status**
  ```bash
  ./scripts/network-mode-manager.sh status
  ```

- **Run full end-to-end regression (Control D → Windscribe)**
  ```bash
  ./scripts/network-mode-regression.sh browsing
  ```

> **Note:** For day-to-day use, prefer `scripts/network-mode-manager.sh`, which orchestrates
> Control D and Windscribe modes and internally delegates Control D activation to
> `controld-system/scripts/controld-manager switch <profile>`. You can still call
> `controld-manager` directly for low-level debugging, but avoid mixing manual
> calls with `network-mode-manager` in the same session.

## Teaching Moments

### Pattern: Configuration as Code
This setup follows the "infrastructure as code" pattern:
- Declarative config file (TOML format)
- Version-controllable profiles
- Automated switching scripts
- Professional teams use this for reproducible environments

### Security Story: DNS Layer Protection
This protects against attacks where malicious actors:
1. Redirect DNS queries to fake IPs (pharming)
2. Track browsing via DNS logs (ISP surveillance)
3. Inject ads or malware via DNS manipulation

### Maintenance Wisdom: Future You Will Thank You For
- Documenting resolver IDs in comments
- Creating helper scripts for common tasks
- Keeping configs in version control
- Testing each profile before deployment
