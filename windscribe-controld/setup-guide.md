# Windscribe VPN + Control D DNS Setup Guide

## Summary
This guide documents the successful configuration of Windscribe VPN with Control D DNS privacy filtering on macOS.

## Final Working Configuration

### Control D Settings
- **Profile**: Privacy profile (6m971e9jaf)
- **Protocol**: DNS-over-HTTPS (DoH)
- **Listener**: `0.0.0.0:53` (all interfaces) - **KEY CHANGE**
- **Manager**: Custom controld-manager with profile switching

### Windscribe Settings
- **DNS**: Local DNS
- **App Internal DNS**: OS Default
- **Split Tunneling**: OFF (disabled)

## Key Technical Solution

The critical breakthrough was modifying Control D's configuration to listen on all interfaces (`0.0.0.0:53`) instead of just localhost (`127.0.0.1:53`).

**Before**: Control D only accessible locally, Windscribe couldn't reach it through VPN tunnel
**After**: Control D accessible through VPN tunnel, enabling "Local DNS" to work properly

## Configuration Files

### Control D Privacy Profile
Location: `/etc/controld/ctrld.privacy.toml`
Key change: `ip = '0.0.0.0'` instead of `ip = '127.0.0.1'`

### Setup Script
Location: `~/Documents/dev/personal-config/windscribe-controld-setup.sh`
Purpose: Automated verification and configuration

## Commands Used

```bash
# Stop Control D
sudo controld-manager stop

# Modify configuration (change 127.0.0.1 to 0.0.0.0)
sudo sed 's/ip = \x27127\.0\.0\.1\x27/ip = \x270\.0\.0\.0\x27/' /etc/controld/ctrld.privacy.toml > /tmp/ctrld_new.toml
sudo cp /tmp/ctrld_new.toml /etc/controld/ctrld.privacy.toml

# Restart with privacy profile
sudo controld-manager switch privacy doh

# Verify
sudo lsof -nP -iTCP:53  # Should show *:53 not 127.0.0.1:53
```

## How It Works

1. **DNS Query Flow**: App → Windscribe VPN → Control D (0.0.0.0:53) → Filtered results → VPN tunnel → App
2. **Traffic Protection**: All traffic routed through Windscribe VPN servers
3. **DNS Privacy**: All DNS queries filtered by Control D privacy rules
4. **Ad Blocking**: Advertising domains blocked (e.g., doubleclick.net → 127.0.0.1)

## Verification

```bash
# Test the complete setup
bash ~/Documents/dev/personal-config/windscribe-controld-setup.sh

# Manual verification
dig doubleclick.net +short      # Should return 127.0.0.1 (blocked)
dig google.com +short           # Should resolve normally
scutil --dns | head -10         # Should show Windscribe VPN in resolver #1
```

## Split Tunneling Issue

**Problem**: When split tunneling was enabled, DNS behavior was inconsistent
- Some apps used VPN DNS (Control D filtering)
- Other apps bypassed VPN (no filtering)
- Created connection/disconnection loops

**Solution**: Disable split tunneling for consistent DNS behavior across all applications

## Expected Results

- ✅ VPN protection for all traffic
- ✅ DNS privacy filtering active
- ✅ Ad domains blocked (doubleclick.net, googleadservices.com)
- ✅ Normal sites work (facebook.com, google.com)
- ✅ Raycast shows Control D as connected
- ✅ IP location shows VPN server (expected)

## Backup and Recovery

Backup files created in:
- `/etc/controld/ctrld.privacy.toml.backup`
- `~/Documents/dev/personal-config/ctrld.toml.backup`

To restore original configuration:
```bash
sudo controld-manager stop
sudo cp /etc/controld/ctrld.privacy.toml.backup /etc/controld/ctrld.privacy.toml
sudo controld-manager switch privacy doh
```

## Maintenance

Profile switching commands:
```bash
sudo controld-manager switch privacy doh    # Privacy profile
sudo controld-manager switch gaming doh     # Gaming profile
sudo controld-manager status                # Check current status
```