# Personal System Configuration

A comprehensive repository for personal system configurations, scripts, and documentation to make my macOS development and gaming setup reproducible and backed up.

## Overview

This repository contains configuration files, automation scripts, and detailed documentation for my personal computing environment. Key features:

- **🔐 Secure SSH Configuration** - 1Password integration with dynamic network support
- **🌐 Dynamic DNS Management** - Control D profile switching for privacy & gaming
- **⚙️ Development Tools** - Optimized configurations for Cursor IDE and terminal workflows
- **🎮 Gaming Optimization** - Specialized DNS profiles for gaming performance
- **📱 Network Automation** - VPN-aware configurations with automatic failover

By keeping these configurations in version control, I can:
- Back up critical system configurations
- Track changes over time with full history
- Reproduce my environment on any new machine
- Document solutions to complex networking challenges
- Share working configurations with the community

## 🎯 Quick Start

### SSH Configuration
```bash
# Install SSH configuration with 1Password integration
./scripts/install_ssh_config.sh

# Test your setup
./tests/test_ssh_config.sh

# Connect to development machine
ssh cursor-mdns  # Works anywhere (VPN on/off)
```

### DNS Management
```bash
# Switch to privacy mode (browsing, AI apps)
sudo ~/bin/ctrld-switcher.sh privacy

# Switch to gaming mode (gaming, minimal filtering)
sudo ~/bin/ctrld-switcher.sh gaming

# Check current status
~/bin/ctrld-switcher.sh status

# Start performance monitoring
~/bin/dns-monitor.sh &

# Deploy/update DNS scripts from backup
cp ~/Documents/dev/personal-config/scripts/ctrld/* ~/bin/
chmod +x ~/bin/ctrld-switcher.sh ~/bin/dns-monitor.sh
```

## 📁 Repository Structure

```
personal-config/
├── 🌐 scripts/ctrld/          # Dynamic DNS Management System
│   ├── ctrld-switcher.sh     # Profile switching automation
│   └── dns-monitor.sh        # Performance monitoring and failover
├── 🔐 configs/                # System Configuration Files
│   ├── ssh/                   # SSH configuration
│   │   ├── config             # Main SSH configuration
│   │   └── agent.toml         # 1Password SSH agent settings
│   ├── fish/                  # Fish shell configuration
│   └── .vscode-R/             # R development settings
├── 📜 scripts/                # Automation Scripts
│   ├── ssh/                   # SSH automation
│   │   ├── smart_connect.sh   # Intelligent connection
│   │   ├── check_connections.sh # Connection testing
│   │   └── diagnose_vpn.sh    # VPN troubleshooting
│   └── install_ssh_config.sh  # SSH setup automation
├── 🧪 tests/                  # Validation & Testing
│   ├── test_ssh_config.sh     # SSH configuration tests
│   └── test_config_fish.sh    # Fish shell tests
├── 📚 docs/                   # Documentation
│   └── ssh/                   # SSH setup guides
└── 🎨 cursor/                 # Cursor IDE themes
```

## ✨ Key Features

### 🌐 Dynamic DNS Management (Updated!)

Intelligent DNS switching system with Control D integration:

**Privacy Mode (`sudo ~/bin/ctrld-switcher.sh privacy`)**
- Enhanced security filtering
- Malware & tracking protection
- Optimized for browsing and AI applications
- Profile ID: `6m971e9jaf`
- DNS: 76.76.2.182, 76.76.10.182

**Gaming Mode (`sudo ~/bin/ctrld-switcher.sh gaming`)**
- Minimal filtering for maximum performance
- Gaming service optimizations (Battle.net, GeForce Now, Overwatch 2)
- Ultra-low latency DNS resolution
- Profile ID: `1xfy57w34t7`
- DNS: 76.76.2.184, 76.76.10.184

**Features:**
- ✅ **Windscribe VPN Integration** - Seamless VPN compatibility
- ✅ **Profile-Specific DoH Endpoints** - Optimized upstream resolvers
- ✅ **Automatic Network Detection** - Skips VPN interfaces intelligently
- ✅ **DNS Leak Protection** - Built-in firewall integration
- ✅ **Smart Verification** - Real-time DNS resolution testing
- ✅ **Performance Monitoring** - Continuous health checks with failover
- ✅ **One-Command Switching** - Simple `sudo ctrld-switcher.sh [profile]` commands

### 🔐 SSH Configuration

Professional SSH setup optimized for development:

**Features:**
- **🔐 1Password SSH Agent** - Secure key management without local storage
- **🌐 Dynamic Network Support** - VPN-aware connection methods
- **🎨 Cursor IDE Optimized** - Perfect remote development setup
- **📱 mDNS/Bonjour Support** - Reliable local machine discovery
- **🔧 Multiple Fallback Options** - Connection reliability guaranteed
- **📊 Comprehensive Diagnostics** - Built-in testing and troubleshooting

**Connection Methods:**
```bash
ssh cursor-mdns    # Primary (works with/without VPN)
ssh cursor-local   # Local network only
ssh cursor-auto    # Auto-detection fallback
```

## 🚀 Installation

### Complete Setup
```bash
# Clone the repository
git clone <your-repo-url> ~/personal-config
cd ~/personal-config

# Install SSH configuration
./scripts/install_ssh_config.sh

# Deploy DNS management scripts
./dns-setup/scripts/deploy.sh

# Test everything
./tests/test_ssh_config.sh
```

### DNS Management Only
```bash
# Copy scripts to ~/bin
cp ~/Documents/dev/personal-config/scripts/ctrld/* ~/bin/
chmod +x ~/bin/ctrld-switcher.sh ~/bin/dns-monitor.sh

# Switch profiles
sudo ~/bin/ctrld-switcher.sh privacy  # Enhanced privacy filtering
sudo ~/bin/ctrld-switcher.sh gaming   # Gaming optimization

# Start monitoring
~/bin/dns-monitor.sh &
```

### SSH Configuration Only
```bash
# Quick install
./scripts/install_ssh_config.sh

# Manual install
cp configs/ssh/config ~/.ssh/config
cp configs/ssh/agent.toml ~/.ssh/agent.toml
chmod 600 ~/.ssh/config ~/.ssh/agent.toml
```

## 🔧 Configuration

### Environment Setup
```bash
# Add required environment variables
export PATH="$HOME/bin:$PATH"  # For DNS scripts

# Optional: Set Control D profile IDs
export CTRLD_PRIVACY_PROFILE="2eoeqoo9ib9"
export CTRLD_GAMING_PROFILE="1igcvpwtsfg"
```

### VPN Integration

**Windscribe Configuration:**
- **VPN Tunnel DNS**: Leave default (inherits Control D)
- **App Internal DNS**: Set to "OS Default"
- **Firewall**: Enable for DNS leak protection

**ProtonVPN Alternative:**
- Use Control D custom DNS when needed
- Gaming: `https://dns.controld.com/1igcvpwtsfg`
- Privacy: `https://dns.controld.com/2eoeqoo9ib9`

## 🧪 Testing & Verification

### DNS System
```bash
# Test current DNS resolution
dig +short google.com @127.0.0.1

# Check active profile
dig +short txt test.controld.com @127.0.0.1

# Verify system DNS configuration
scutil --dns | head -20

# Check Control D status
~/bin/ctrld-switcher.sh status

# Monitor performance
~/bin/dns-monitor.sh
```

### SSH Configuration
```bash
# Comprehensive SSH tests
./tests/test_ssh_config.sh

# Test all connection methods
./scripts/ssh/check_connections.sh

# Manual connection verification
./scripts/ssh/setup_verification.sh
```

## 📊 Monitoring & Maintenance

### DNS Logs
```bash
# View DNS switching logs
sudo tail -f ~/Library/Logs/ctrld/ctrld-switcher.log

# Check daemon status
sudo lsof -nP -iTCP:53 -sTCP:LISTEN -iUDP:53

# Monitor DNS performance
~/bin/dns-monitor.sh
```

### System Health
```bash
# Network diagnostics
./scripts/ssh/diagnose_vpn.sh

# DNS resolution testing
for server in 127.0.0.1 8.8.8.8 1.1.1.1; do
  echo "Testing $server:"
  dig +short google.com @$server
done
```

## 🎮 Use Cases

### Development Workflow
1. **Connect**: `ssh cursor-mdns`
2. **Privacy Mode**: `sudo ~/bin/ctrld-switcher.sh privacy`
3. **Code with enhanced security filtering**

### Gaming Session
1. **Gaming Mode**: `sudo ~/bin/ctrld-switcher.sh gaming`
2. **Minimal filtering for maximum performance**
3. **Optimized for Battle.net, Steam, Nvidia GeForce Now, Overwatch 2**

### VPN Switching
1. **Windscribe VPN**: Default setup with Control D integration
2. **Proton VPN**: When port forwarding or different geo-location needed
3. **DNS profiles work seamlessly with both**

## 🔒 Security & Privacy

- **🔐 Secrets Management**: Uses 1Password for SSH keys, environment variables for configs
- **🌐 DNS Leak Protection**: Built-in firewall integration prevents leaks
- **🛡️ Profile Isolation**: Separate DNS policies for different use cases
- **📊 Verification**: Real-time testing ensures configuration integrity
- **🔄 Version Control**: All changes tracked with full history

## 🛠️ Troubleshooting

### Common Issues

**DNS switching problems:**
```bash
# Check what's using port 53
sudo lsof -nP -iTCP:53 -sTCP:LISTEN -iUDP:53

# Reset DNS to defaults
for s in $(networksetup -listallnetworkservices | tail -n +2 | sed 's/^\*//'); do
  sudo networksetup -setdnsservers "$s" empty || true
done

# Check Control D status
~/bin/ctrld-switcher.sh status

# Restart Control D
sudo ~/bin/ctrld-switcher.sh restart
```

**SSH connection issues:**
```bash
# Comprehensive diagnostics
./scripts/ssh/diagnose_vpn.sh

# Test individual connection methods
./scripts/ssh/check_connections.sh
```

### Support Resources

- **[DNS Setup Guide](ctrld-switching.md)** - Complete DNS documentation
- **[SSH Configuration Guide](docs/ssh/ssh_configuration_guide.md)** - SSH setup instructions
- **[Deployment Summary](dns-setup/DEPLOYMENT_SUMMARY.md)** - Technical implementation details

## 🚧 Future Enhancements

- [ ] **Automated VPN Detection** - Dynamic VPN provider switching
- [ ] **Profile Scheduling** - Time-based DNS profile switching
- [ ] **Network Location Awareness** - Location-based configuration switching
- [ ] **Performance Monitoring** - DNS resolution latency tracking
- [ ] **Mobile Device Integration** - iOS/Android configuration sync
- [ ] **Backup Automation** - Scheduled configuration backups

## 📈 Version History

- **v4.0** (September 2025) - Advanced Control D DNS Management with Performance Monitoring
- **v3.0** (September 2025) - Dynamic DNS Management System
- **v2.0** (August 2025) - SSH Configuration with 1Password
- **v1.0** (April 2025) - Initial repository structure

## 📄 License

Personal use configurations. Feel free to adapt and use any parts that are helpful for your own setup.

---

**🎉 Your complete development and gaming network is now perfectly automated!**

_Last Updated: September 20, 2025_  
_DNS Management System: v4.0_  
_SSH Configuration: v2.0_
