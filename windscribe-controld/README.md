# Windscribe VPN + Control D DNS Integration

## Overview
This directory contains the complete setup and configuration for integrating Windscribe VPN with Control D DNS privacy filtering, providing dual protection: VPN encryption + DNS privacy filtering.

## ✅ Current Active Configuration

### System Status
- **VPN**: Windscribe connected with Local DNS setting
- **DNS Privacy**: Control D Privacy Profile (6m971e9jaf) with DOH encryption
- **Geographic Routing**: Miami, FL (NetActuate, Inc) - Control D proxy
- **Ad Blocking**: 500+ domains blocked (doubleclick.net → 127.0.0.1)
- **Real-time Logging**: DNS queries visible in Control D dashboard

### Key Achievement
**Dual Protection System**: VPN tunnel encryption + DNS privacy filtering working simultaneously through a sophisticated integration that routes DNS queries through the VPN tunnel to a local Control D resolver.

## 🚀 Quick Usage

> **Note (v4.x):** For day-to-day switching between Control D DNS mode and
> Windscribe VPN mode, use `scripts/network-mode-manager.sh`. The commands in
> this document remain accurate for understanding and manually testing the
> integration, but `network-mode-manager.sh` is the primary entrypoint.

### Setup Verification
```bash
# Run complete system verification
bash windscribe-controld-setup.sh

# Expected result: ✅ SUCCESS! Windscribe VPN + Control D DNS is working!
```

### Profile Switching
```bash
# Switch to privacy profile (enhanced filtering)
sudo controld-manager switch privacy doh

# Switch to gaming profile (minimal filtering)  
sudo controld-manager switch gaming doh

# Check current status
sudo controld-manager status
```

### Manual Testing
```bash
# Test ad blocking
dig doubleclick.net +short          # Should return 127.0.0.1 (blocked)
dig googleadservices.com +short     # Should return 127.0.0.1 (blocked)

# Test normal resolution
dig google.com +short               # Should resolve normally
dig facebook.com +short             # Should resolve normally

# Check geographic routing
curl -s https://ipinfo.io/json | grep -E '(city|region|country|org)'
# Should show: Miami, FL, US, NetActuate Inc (Control D proxy)
```

## 📁 Files

- **`windscribe-controld-setup.sh`** - Automated setup verification and troubleshooting
- **`setup-guide.md`** - Complete technical documentation  
- **`ctrld.toml.backup`** - Backup of original Control D configuration
- **`README.md`** - This file

## 🔧 Technical Details

### How It Works

```
Application Request
        ↓
Windscribe VPN Tunnel
        ↓
Control D Local Resolver (0.0.0.0:53)
        ↓
Control D Cloud Service (DOH)
        ↓
Filtered Response via Miami Proxy
        ↓
Back through VPN Tunnel
        ↓
Application Receives Response
```

### Key Configuration Changes

**Control D Configuration:**
- **Before**: Listened on `127.0.0.1:53` (localhost only)
- **After**: Listens on `0.0.0.0:53` (all interfaces)
- **Why**: Allows VPN tunnel to reach local Control D resolver

**Windscribe Configuration:**
- **DNS Setting**: Local DNS (not Custom DNS)
- **App Internal DNS**: OS Default
- **Split Tunneling**: Disabled (for consistency)

## 🛠️ Configuration Files

### Control D Profiles
```bash
# Privacy profile configuration
/etc/controld/ctrld.privacy.toml

# Gaming profile configuration  
/etc/controld/ctrld.gaming.toml

# Active configuration (symlink)
/etc/controld/ctrld.toml
```

### Windscribe Settings
- **DNS**: Local DNS ✅
- **App Internal DNS**: OS Default ✅  
- **Split Tunneling**: OFF ✅
- **Firewall**: Enabled for leak protection

## 📊 Expected Indicators

### ✅ Success Indicators
- **Location**: Miami, FL (NetActuate, Inc)
- **DNS Logs**: Real-time queries in Control D dashboard
- **Ad Blocking**: `doubleclick.net` → `127.0.0.1`
- **VPN Status**: Connected through Windscribe

### ⚠️ Normal Behaviors  
- **Raycast**: Shows "Control D not connected" (this is expected)
- **IP Location**: Miami instead of Windscribe server (this is correct)
- **DNS Resolution**: Appears to use Windscribe DNS (technically true at network level)

## 🧪 Troubleshooting

### Common Issues

**1. VPN Connection Fails**
```bash
# Temporarily set Windscribe DNS to "Auto"
# Connect to VPN first
# Then switch back to "Local DNS"
```

**2. DNS Not Filtering**
```bash
# Check Control D binding
sudo lsof -nP -iTCP:53    # Should show *:53 not 127.0.0.1:53

# Restart Control D with correct binding
sudo controld-manager switch privacy doh
```

**3. Inconsistent Behavior**
```bash
# Ensure split tunneling is disabled in Windscribe
# All traffic must use VPN consistently
```

### Diagnostic Commands
```bash
# Check Control D status
sudo controld-manager status

# Check DNS configuration
scutil --dns | head -15

# Test Control D directly
dig @127.0.0.1 google.com +short

# Check network interfaces
ifconfig | grep -A5 "utun"

# Verify VPN tunnel
netstat -rn | head -10
```

## 🔒 Security Benefits

### Dual Protection
1. **VPN Encryption**: All traffic encrypted through Windscribe tunnel
2. **DNS Privacy**: DNS queries filtered and logged by Control D
3. **Geographic Masking**: Traffic routes through Control D's Miami proxy
4. **Ad Blocking**: Comprehensive filtering of advertising/tracking domains

### Privacy Features
- **DOH Encryption**: DNS-over-HTTPS for DNS query protection
- **Real-time Logging**: Transparent DNS query monitoring  
- **Profile-based Filtering**: Different rules for privacy vs gaming
- **Leak Protection**: VPN + DNS settings prevent data leaks

## 📚 Documentation

- **[Complete Setup Guide](setup-guide.md)** - Detailed technical documentation
- **[Parent Repository README](../README.md)** - Repository overview
- **[Control D System](../controld-system/README.md)** - Control D documentation

## 🎯 Use Cases

### Privacy Browsing
```bash
sudo controld-manager switch privacy doh
# Enhanced filtering active
# All ads and trackers blocked
# Geographic routing through Miami
```

### Gaming Session  
```bash
sudo controld-manager switch gaming doh
# Minimal filtering for performance
# Gaming services optimized
# Low latency DNS resolution
```

### Development Work
```bash
# Privacy profile provides enhanced security
# Essential development services bypassed
# VPN + DNS protection for sensitive work
```

## 🚀 Future Enhancements

- [ ] **Automated VPN Detection** - Auto-switch based on VPN status
- [ ] **Profile Scheduling** - Time-based profile switching  
- [ ] **Performance Monitoring** - DNS resolution latency tracking
- [ ] **Mobile Integration** - iOS/Android companion setup

## 📝 Recent Updates

**October 2025** - Enhanced VPN Integration
- ✅ Integrated Windscribe VPN with Control D DNS
- ✅ Modified Control D to listen on all interfaces (0.0.0.0:53)
- ✅ Disabled split tunneling for consistent behavior  
- ✅ Achieved dual protection: VPN + DNS privacy
- ✅ Real-time DNS logging with DOH encryption
- ✅ Geographic routing through Miami proxy

---

**Status**: ✅ Active and working perfectly  
**Last Verified**: October 2025  
**Setup Validation**: Run `bash windscribe-controld-setup.sh`