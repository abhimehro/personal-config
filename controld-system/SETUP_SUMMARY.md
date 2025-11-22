# Control D Setup Summary

**Date**: November 18, 2025  
**System**: macOS  
**ctrld Version**: v1.4.7

> **Current Implementation Note (v4.1+):** This file describes the
> original standalone `~/.config/controld` setup using DoH/TCP. The
> production system now uses DoH3 by default via
> `/etc/controld` + `controld-manager`, with mode switching handled by
> `scripts/network-mode-manager.sh`. The data-flow diagrams and
> reasoning below still apply conceptually; treat specific protocol and
> path references as historical where they differ from the v4.1+
> architecture.

## At a Glance: Data Flow

### Without VPN
```
┌─────────────┐
│   Your App  │
└──────┬──────┘
       │ DNS query (e.g., "example.com")
       ▼
┌─────────────────────┐
│ macOS DNS Resolver  │
│   (127.0.0.1:53)    │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│   Control D (ctrld) │ ◄── Local service, port 53
│   127.0.0.1:53      │     Filtering, privacy rules
└──────┬──────────────┘
       │ DNS-over-HTTPS (encrypted)
       │ Port 443
       ▼
┌─────────────────────┐
│ Control D Servers   │ ◄── freedns.controld.com
│ (DoH endpoints)     │     76.76.2.22 (bootstrap)
└──────┬──────────────┘
       │ Upstream query
       ▼
┌─────────────────────┐
│    Internet DNS     │ ◄── Authoritative servers
│  (e.g., example.com)│
└─────────────────────┘
```

**Security layers**:
- ✅ ISP can't see DNS queries (DoH encryption)
- ⚠️  ISP can see destination IPs (HTTP traffic)
- ✅ Control D filtering active (malware/tracker blocking)

### With VPN (Windscribe + Local DNS)
```
┌─────────────┐
│   Your App  │
└──────┬──────┘
       │ DNS query
       ▼
┌─────────────────────┐
│ macOS DNS Resolver  │
│   (127.0.0.1:53)    │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│   Control D (ctrld) │ ◄── Local service
│   127.0.0.1:53      │     Filtering, privacy rules
└──────┬──────────────┘
       │ DNS-over-HTTPS
       │ Port 443
       ▼
┌─────────────────────┐
│  Windscribe Tunnel  │ ◄── VPN encryption layer
│    (utun interface) │     Double encryption
└──────┬──────────────┘
       │ Encrypted tunnel
       ▼
┌─────────────────────┐
│ Control D Servers   │ ◄── Via VPN exit node
│ (DoH endpoints)     │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│    Internet DNS     │
└─────────────────────┘
```

**Security layers**:
- ✅ ISP can't see DNS queries (VPN + DoH = double encrypted)
- ✅ ISP can't see destination IPs (VPN tunnel)
- ✅ Control D filtering active
- ✅ **Maximum privacy configuration**

## What Was Configured

### 1. Service Installation
- **Method**: ctrld's built-in service installer
- **Launch Daemon**: `/Library/LaunchDaemons/ctrld.plist`
- **Auto-start**: Enabled (starts on boot)
- **Special Flag**: `--skip_self_checks` (see below for reasoning)

### 2. DNS Profiles
Three Control D resolver profiles configured:

1. **privacy_enhanced** (6m971e9jaf) - Default, active
   - Maximum privacy/security filtering
   - Blocks trackers, ads, malware

2. **browsing_privacy** (rcnz7qgvwg)
   - Balanced privacy for general use
   
3. **gaming_optimized** (1xfy57w34t7)
   - Minimal filtering for lower latency

### 3. Firewall Configuration
- **Exception added**: `/opt/homebrew/bin/ctrld`
- **Reason**: Allow ctrld to make outbound DoH connections
- **Method**: macOS Application Firewall

### 4. Bootstrap IPs
- All upstreams use: `76.76.2.22`
- This is Control D's primary bootstrap IP for establishing initial DoH connections

## The "Connection Refused" Problem

### Root Cause
During startup, ctrld runs self-checks that attempt to:
1. Connect to bootstrap IPs on port 443
2. Verify DoH endpoints are reachable
3. Perform test DNS queries

**The Issue**: macOS firewall blocks these initial connections during the self-check phase, causing "connection refused" errors even though:
- The firewall exception is present
- The connections work fine during normal operation
- curl can successfully reach the same endpoints

### Why This Happens
Timing issue between:
- Service startup (requires sudo/root)
- Firewall rule application
- Initial connection attempts

The self-checks happen too quickly, before firewall rules fully apply.

## The Solution: `--skip_self_checks`

### What It Does
- Bypasses startup validation tests
- Service starts immediately
- Connections established during normal operation (which work fine)

### Security Tradeoff Analysis

**Decision**: Use fail-operational approach (skip self-checks)

#### Why This Is Safe

1. **Self-checks don't prevent attacks**
   - They only validate configuration syntax and connectivity
   - They don't protect against DNS spoofing, MITM, or malware
   - Real security comes from DoH encryption (HTTPS)

2. **Configuration is pre-validated**
   - We manually tested the config
   - DNS resolution works correctly once service runs
   - Self-check failures are false positives

3. **Operational benefits**
   - Service starts reliably on every boot
   - No manual intervention needed
   - Can recover from temporary upstream outages
   - No ongoing firewall rule maintenance

#### Alternative Approach (Not Chosen)

**Option**: Modify firewall to explicitly allow bootstrap IPs

**Why we didn't do this**:
- Bootstrap IPs can change without notice
- Would require ongoing maintenance
- Doesn't add meaningful security
- Self-checks could still fail if upstreams are temporarily down
- More complex and fragile

## Files Created/Modified

### Configuration Files
- `~/.config/controld/ctrld.toml` - Main configuration
- `/Library/LaunchDaemons/ctrld.plist` - Auto-start daemon

### Documentation
- `~/.config/controld/README.md` - Comprehensive guide
- `~/.config/controld/QUICKREF.md` - Quick command reference
- `~/.config/controld/SETUP_SUMMARY.md` - This file

### Utilities
- `~/.config/controld/health-check.sh` - Service health monitoring

### System Configuration
- Firewall exception for `/opt/homebrew/bin/ctrld`

## Verification Commands

```bash
# Check service is running
sudo ctrld service status

# Verify DNS resolution
dig @127.0.0.1 example.com +short

# Run comprehensive health check
~/.config/controld/health-check.sh

# Check launch daemon is loaded
sudo launchctl list | grep ctrld

# Verify firewall exception
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --listapps | grep ctrld
```

## Post-Reboot Testing

After a system reboot, verify:
1. Service auto-starts: `sudo ctrld service status`
2. DNS resolves: `dig @127.0.0.1 example.com`
3. No errors in logs: `sudo tail -20 /var/log/ctrld.log`
4. Health check passes: `~/.config/controld/health-check.sh`

## Teaching Moments from This Setup

### 1. Fail-Secure vs Fail-Operational
Professional systems must choose:
- **Fail-secure**: Refuse to start if any check fails (prevents misconfig)
- **Fail-operational**: Start anyway, detect issues at runtime (better availability)

Our choice: Fail-operational because the self-checks provide validation but not security.

### 2. Defense in Depth
Real security comes from layered protections:
- DoH encryption (prevents DNS snooping)
- Control D filtering (blocks malicious domains)
- Firewall (controls network access)
- Self-checks are just validation, not a security layer

### 3. The "Works on My Machine" Problem
curl succeeded but ctrld failed with identical connections because:
- Different execution context (interactive user vs system service)
- Different timing (immediate vs startup phase)
- Different permissions (user vs root)

This taught us: Test services in the environment where they'll actually run.

### 4. Operational Wisdom
"Future you will thank present you for":
- Creating health check scripts (validate assumptions)
- Documenting decisions with reasoning (especially tradeoffs)
- Writing quick reference guides (reduce cognitive load)
- Backing up working configs (recovery plan)

## Backup/Restore Strategy

### Backup Important Files
```bash
# Create backup directory
mkdir -p ~/Backups/controld-$(date +%Y%m%d)

# Backup configuration and docs
cp ~/.config/controld/ctrld.toml ~/Backups/controld-$(date +%Y%m%d)/
cp ~/.config/controld/*.md ~/Backups/controld-$(date +%Y%m%d)/
cp ~/.config/controld/health-check.sh ~/Backups/controld-$(date +%Y%m%d)/

# Backup launch daemon (requires sudo)
sudo cp /Library/LaunchDaemons/ctrld.plist ~/Backups/controld-$(date +%Y%m%d)/
```

### Restore After Reinstall
```bash
# Reinstall ctrld
brew install ctrld

# Restore configuration
cp ~/Backups/controld-YYYYMMDD/ctrld.toml ~/.config/controld/

# Reinstall service
sudo ctrld service start --config ~/.config/controld/ctrld.toml --skip_self_checks

# Re-add firewall exception
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /opt/homebrew/bin/ctrld

# Verify
~/.config/controld/health-check.sh
```

## Future Maintenance

### When to Update
- Control D releases new resolver IDs
- ctrld software updates (via Homebrew)
- macOS major version updates

### After macOS Updates
1. Verify service is still running
2. Check firewall exception still exists
3. Run health check
4. Check logs for new errors

### Profile Changes
To switch between profiles, either:
- Use `ctrld-switch` script (if available)
- Edit `ctrld.toml` and change `upstream` value
- Restart service: `sudo ctrld service restart`

## Support Resources

- Control D Dashboard: https://controld.com/dashboard
- Control D Docs: https://docs.controld.com/
- ctrld GitHub: https://github.com/Control-D-Inc/ctrld
- Local docs: `~/.config/controld/README.md`
- Quick ref: `~/.config/controld/QUICKREF.md`
