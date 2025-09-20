# Control D DNS Profile Switching Guide

## Overview
Advanced DNS management system using Control D with automated profile switching, performance monitoring, and failover protection.

## Quick Commands

```bash
# Switch to privacy profile (maximum protection)
sudo ~/bin/ctrld-switcher.sh privacy

# Switch to gaming profile (low latency)
sudo ~/bin/ctrld-switcher.sh gaming

# Check current status
~/bin/ctrld-switcher.sh status

# Stop Control D completely
sudo ~/bin/ctrld-switcher.sh stop

# Restart current profile
sudo ~/bin/ctrld-switcher.sh restart

# Start performance monitoring
~/bin/dns-monitor.sh &
```

## Profile Details

### Privacy Profile
- **Profile ID**: `6m971e9jaf`
- **Primary DNS**: `76.76.2.182`
- **Secondary DNS**: `76.76.10.182`
- **Use Case**: Browsing, AI applications, maximum privacy protection
- **Features**: Enhanced filtering, malware protection, tracking prevention

### Gaming Profile
- **Profile ID**: `1xfy57w34t7`
- **Primary DNS**: `76.76.2.184`
- **Secondary DNS**: `76.76.10.184`
- **Use Case**: Gaming, low-latency applications
- **Features**: Minimal filtering, optimized for gaming services (Battle.net, Steam, GeForce Now)

## Verification

### DNS Resolution Test
```bash
# Test current DNS resolution
dig @127.0.0.1 google.com +short

# Check active profile
dig @127.0.0.1 txt test.controld.com
```

### System DNS Configuration
```bash
# Check network interfaces
networksetup -listallnetworkservices

# View DNS settings for specific interface
networksetup -getdnsservers 