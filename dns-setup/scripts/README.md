# DNS Switching Scripts

Automated Control D profile switching scripts for macOS with Windscribe VPN integration.

## Overview

These scripts provide seamless switching between Control D DNS profiles:
- **Privacy Mode**: Enhanced security and privacy filtering (`2eoeqoo9ib9`)
- **Gaming Mode**: Minimal filtering for optimal gaming performance (`1igcvpwtsfg`)

## Features

✅ **Safe Switching**: Properly stops existing daemons before starting new ones  
✅ **DNS Leak Protection**: Integrates with Windscribe firewall  
✅ **System Integration**: Updates macOS DNS settings automatically  
✅ **Verification**: Confirms profile activation after switching  
✅ **Logging**: Detailed logs for troubleshooting  
✅ **VPN Awareness**: Skips VPN interfaces to prevent conflicts  

## Installation

### Deploy to ~/bin (Recommended)
```bash
# Run from personal-config directory
./dns-setup/scripts/deploy.sh
```

### Manual Installation
```bash
# Copy scripts to ~/bin
cp dns-setup/scripts/dns-* ~/bin/
chmod +x ~/bin/dns-*

# Ensure ~/bin is in PATH (already done in setup)
export PATH="$HOME/bin:$PATH"
```

## Usage

### Basic Commands
```bash
# Switch to Privacy Mode (browsing, AI apps)
sudo dns-privacy

# Switch to Gaming Mode (gaming, minimal blocking)
sudo dns-gaming
```

### Verification
```bash
# Check DNS configuration
scutil --dns | head -20

# Verify Control D profile
dig +short txt test.controld.com @127.0.0.1
```

## Windscribe Configuration

For optimal DNS leak protection:

1. **VPN Tunnel DNS**: Leave as default (inherits local Control D)
2. **App Internal DNS**: Set to **"OS Default"**
3. **Firewall**: Enable for DNS leak protection

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Application   │───▶│  Control D Local │───▶│  Windscribe VPN │
│   DNS Request   │    │  (127.0.0.1:53)  │    │     Tunnel      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Profile Details

### Privacy Mode (`2eoeqoo9ib9`)
- **Use Case**: General browsing, AI applications, research
- **Filtering**: Enhanced security, malware, tracking, ads
- **Optimal for**: Privacy-focused activities

### Gaming Mode (`1igcvpwtsfg`) 
- **Use Case**: Gaming, streaming, real-time applications
- **Filtering**: Minimal (malware only)
- **Optimizations**: Battle.net, GeForce Now, Overwatch 2

## Logs & Troubleshooting

### Log Locations
- **Privacy Mode**: `/var/log/ctrld-privacy.log`
- **Gaming Mode**: `/var/log/ctrld-gaming.log`
- **Process PID**: `/var/run/ctrld.pid`

### Common Issues

**Script requires sudo:**
```bash
# Always run with sudo
sudo dns-privacy
sudo dns-gaming
```

**Port 53 conflicts:**
```bash
# Check what's using port 53
sudo lsof -nP -iTCP:53 -sTCP:LISTEN -iUDP:53
```

**DNS not updating:**
```bash
# Manually flush DNS
dscacheutil -flushcache
sudo killall -HUP mDNSResponder
```

**Verify Control D profile:**
```bash
# Check current profile
dig +short txt test.controld.com @127.0.0.1

# Should contain active profile ID
# Privacy: 2eoeqoo9ib9
# Gaming: 1igcvpwtsfg
```

### Reset to DHCP

To restore default DNS settings:
```bash
# Reset all network services to DHCP DNS
for s in $(networksetup -listallnetworkservices | tail -n +2 | sed 's/^\*//'); do 
  sudo networksetup -setdnsservers "$s" empty || true
done

# Flush caches
dscacheutil -flushcache
sudo killall -HUP mDNSResponder
```

## Integration with VPN Providers

### Windscribe (Recommended)
- Set "App Internal DNS" to "OS Default"
- Enable Firewall for leak protection
- VPN tunnel automatically uses Control D

### ProtonVPN (Alternative)
- Use Control D gaming profile as custom DNS
- For port forwarding scenarios
- Set custom DNS: `https://dns.controld.com/1igcvpwtsfg`

## Security Notes

- Scripts require root privileges for system DNS modification
- Firewall integration prevents DNS leaks outside VPN tunnel
- Local resolver (127.0.0.1) ensures all queries go through Control D
- VPN interfaces are automatically skipped to prevent conflicts

## Maintenance

### Update Profile IDs
Edit the scripts to change profile IDs:
```bash
# In dns-privacy script
PROFILE_ID="your-privacy-profile-id"

# In dns-gaming script
PROFILE_ID="your-gaming-profile-id"
```

### Backup Configuration
Scripts are backed up in `personal-config/dns-setup/scripts/`

---

**Created**: September 2024  
**Version**: 1.0  
**Compatible**: macOS with Control D and Windscribe VPN