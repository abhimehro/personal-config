# Control D + AdGuard Optimal Configuration

**Last Updated**: October 10, 2025  
**Status**: ✅ Working  
**macOS Version**: 15.0.1 (Sequoia)

## Overview

This configuration allows Control D DNS and AdGuard to work together optimally without conflicts, providing comprehensive DNS filtering, privacy protection, and web content blocking.

## Working Configuration Summary

| Service | Role | Protocol | Status |
|---------|------|----------|--------|
| **Control D** | DNS filtering, privacy, malware blocking | DoH (TCP/443) | ✅ Active |
| **AdGuard** | Web content filtering, ad blocking | System default DNS | ✅ Active |
| **System DNS** | Points to Control D localhost resolver | 127.0.0.1:53 | ✅ Configured |

## Key Technical Decisions

### Why DoH Instead of DoH3/DoQ?
- **DoH3/DoQ (UDP/443)**: Failed due to macOS IPv6 system-level issues
- **DoH (TCP/443)**: Works reliably with AdGuard's network extension
- **Result**: Stable, encrypted DNS over HTTPS

### Why This Architecture?
- **Control D**: Handles all DNS queries (filtering, privacy, analytics)
- **AdGuard**: Handles web content filtering (ads, trackers, scripts)
- **No DNS conflicts**: Each service operates in its optimal domain

## Control D Configuration

### DNS Protocol Settings
- **Protocol**: DNS-over-HTTPS (DoH) - TCP/443
- **Bootstrap Resolvers**: System default (1.1.1.1, 8.8.8.8)
- **Local Resolver**: 127.0.0.1:53
- **Profile**: Privacy Boost (active)

### Profile Features Active
- DNS filtering with custom rules
- Privacy protection with IP masking
- Malware and phishing protection
- Analytics and logging

## AdGuard Configuration

### DNS Settings
```
DNS Provider: System default (NOT AdGuard DNS)
```

### Network Settings
```
✅ Automatically filter applications: ENABLED
✅ Filter HTTPS protocol: ENABLED
✅ Filter websites with EV certificates: ENABLED
```

### Critical Exclusions

**HTTPS Exclusions** (Network → Exclusions...):
```
*.controld.com
dns.controld.com
verify.controld.com
```

**Application Exclusions**:
```
Bundle ID: com.controld.app
```

### Advanced Settings (if needed)
```
network.extension.dns.redirect.exclude.bundleids = com.cisco.anyconnect.macos.acsockext, com.cloudflare.1dot1dot1, com.controld.app
network.extension.exclude.domains = apple.com, icloud.com, controld.com, dns.controld.com, verify.controld.com
dns.proxy.bootstrap.ips = 1.1.1.1, 8.8.8.8
dns.proxy.http3.enabled = true
dns.proxy.servfail.on.upstreams.failure.enabled = false
```

## System DNS Configuration

### Network Services
Both active network interfaces configured identically:
```bash
sudo networksetup -setdnsservers "Wi-Fi" 127.0.0.1
sudo networksetup -setdnsservers "USB 10/100/1000 LAN" 127.0.0.1
```

### Service Priority
```bash
networksetup -ordernetworkservices "USB 10/100/1000 LAN" "Wi-Fi" "Thunderbolt Bridge" "Bluetooth PAN"
```

## Validation & Testing

### DNS Resolution Test
```bash
# Test Control D DNS
dig +short verify.controld.com
# Expected: api.controld.com. followed by IP

# Test regular DNS
dig +short google.com
# Expected: Google IP addresses
```

### Control D Status Check
Visit: https://verify.controld.com
- Should show: "Control D is protecting your device"
- Profile: Privacy Boost
- IP Location: Masked (e.g., Miami, FL instead of actual location)

### AdGuard Status Check
- AdGuard should show active blocking statistics
- Web browsing should have ads blocked
- HTTPS filtering should be working

## Troubleshooting

### Common Issues

**Control D fails to start**:
1. Check if ctrld process is already running: `sudo lsof -i :53`
2. Kill existing process if needed: `sudo pkill ctrld`
3. Restart Control D app

**AdGuard blocking Control D**:
1. Verify DNS provider is set to "System default"
2. Check HTTPS exclusions include Control D domains
3. Restart both applications

**IPv6/UDP errors**:
- This configuration avoids IPv6 UDP issues by using DoH (TCP)
- If errors persist, temporarily disable IPv6 on network interfaces

### Reset to Working State
```bash
# Run the automation script
bash ~/Documents/dev/personal-config/scripts/macos/controld-ensure.sh

# Or manual reset
for S in "Wi-Fi" "USB 10/100/1000 LAN"; do
  sudo networksetup -setdnsservers "$S" 127.0.0.1
done
sudo dscacheutil -flushcache
sudo killall -HUP mDNSResponder
```

## VPN Compatibility

### Windscribe VPN
**Split Tunneling Exclusions**:
- App: Control D app
- Domains: controld.com, dns.controld.com, verify.controld.com
- Custom DNS: Use Control D profile IPv4 resolvers

### Proton VPN
**Advanced Settings**:
- Split Tunneling: Exclude Control D app and domains
- Custom DNS: Set to Control D IPv4 resolvers
- Disable Smart Protocol if it interferes with DoH

**Important**: Never run both VPNs simultaneously

## Automation

The configuration is maintained by:
- Script: `~/Documents/dev/personal-config/scripts/macos/controld-ensure.sh`
- LaunchAgent: `~/Library/LaunchAgents/com.personal.controld.ensure.plist`
- Auto-runs at login to ensure DNS consistency

## Performance Metrics

From active configuration (October 2025):
- **Control D**: 50 IPs filtered, Privacy Boost profile active
- **AdGuard**: 2,276 requests blocked in last 24 hours (9.7% block rate)
- **Location Masking**: Active (showing Miami, FL)
- **DNS Latency**: Low (<50ms typical)

## Future Maintenance

1. **After macOS updates**: Re-run validation script
2. **After app updates**: Verify configuration still works
3. **IPv6 testing**: Periodically test if IPv6 UDP/443 works again
4. **Repository updates**: Keep this documentation current

## Backup & Recovery

Configuration backed up to:
- This repository (documentation)
- Network diagnostics snapshots in `network-diagnostics/`
- LaunchAgent for automatic restoration

---

*This configuration represents the optimal balance between DNS privacy, content filtering, and system stability on macOS.*