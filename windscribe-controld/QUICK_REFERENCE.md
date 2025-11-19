# Windscribe + Control D Quick Reference

## 🎯 Daily Commands

> **Note (v4.x):** For everyday switching between Control D DNS mode and
> Windscribe VPN mode, prefer `./scripts/network-mode-manager.sh`. The
> `controld-manager` commands below are still valid for direct profile control
> and low-level debugging.

### Profile Switching
```bash
# Privacy Profile (enhanced filtering)
sudo controld-manager switch privacy doh

# Gaming Profile (optimized performance)
sudo controld-manager switch gaming doh

# Check current status
sudo controld-manager status
```

### System Verification
```bash
# Complete system check
bash ~/Documents/dev/personal-config/windscribe-controld/windscribe-controld-setup.sh

# Quick DNS test
dig doubleclick.net +short    # Should return 127.0.0.1
dig google.com +short         # Should resolve normally
```

## 🚨 Emergency Commands

### Control D Emergency Reset
```bash
# Emergency stop with network restoration
sudo controld-manager emergency

# Safe stop
sudo controld-manager stop
```

### Complete Network Reset
```bash
# Reset all DNS to automatic
for service in $(networksetup -listallnetworkservices | tail -n +2 | sed 's/^*//'); do
  sudo networksetup -setdnsservers "$service" empty
done

# Flush DNS cache
sudo dscacheutil -flushcache && sudo killall -HUP mDNSResponder
```

## 🔧 Diagnostics

### Check System Status
```bash
# DNS configuration
scutil --dns | head -15

# Control D binding
sudo lsof -nP -iTCP:53

# VPN interfaces  
ifconfig | grep -A5 "utun"

# Current location
curl -s https://ipinfo.io/json
```

## ✅ Expected Status Indicators

- **Raycast**: Control D connected ✅
- **Location**: Miami, FL (NetActuate, Inc) 
- **Ad Blocking**: doubleclick.net → 127.0.0.1
- **VPN**: Windscribe connected with Local DNS

---
**For detailed documentation**: `~/Documents/dev/personal-config/windscribe-controld/README.md`