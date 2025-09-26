# Personal System Configuration

A comprehensive repository for personal system configurations, scripts, and documentation to make my macOS development and gaming setup reproducible and backed up.

## Overview

This repository contains configuration files, automation scripts, and detailed documentation for my personal computing environment. Key features:

- **🔐 Secure SSH Configuration** - 1Password integration with GitHub authentication ✅ **WORKING**
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

### SSH Configuration ✅ **WORKING SOLUTION**
```bash
# Working SSH configuration with 1Password + GitHub
# Status: ✅ FULLY FUNCTIONAL as of September 24, 2025

# Test your GitHub SSH connection
ssh -T git@github.com
# Expected: "Hi abhimehro! You've successfully authenticated..."

# Use the working configuration
cp configs/ssh/config-working ~/.ssh/config

# See complete setup guide
open docs/ssh/SSH_1PASSWORD_GITHUB_SUCCESS.md
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
│   │   ├── config             # Main SSH configuration (complex)
│   │   ├── config-working     # ✅ WORKING GitHub + 1Password config
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
│       ├── SSH_1PASSWORD_GITHUB_SUCCESS.md  # ✅ WORKING SOLUTION
│       └── ssh_configuration_guide.md       # Comprehensive guide
└── 🎨 cursor/                 # Cursor IDE themes
```

## ✨ Key Features

### 🔐 SSH Configuration ✅ **WORKING SOLUTION**

**Status: FULLY FUNCTIONAL** - SSH + 1Password + GitHub authentication working perfectly!

**Working Configuration (`configs/ssh/config-working`):**
```ssh
Host *
    IdentityAgent ~/Library/Group\ Containers/2BUA8C4S2C.com.1password/t/agent.sock

Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
```

**Features:**
- **🔐 1Password SSH Agent** - Secure key management without local storage
- **✅ GitHub Authentication** - Verified working with user `abhimehro`
- **🔑 ED25519 Key Support** - Modern, secure key type
- **📱 Manual Import Method** - Most reliable 1Password key import process
- **🧪 Thoroughly Tested** - Complete troubleshooting history documented

**Quick Setup:**
```bash
# Copy working configuration
cp configs/ssh/config-working ~/.ssh/config

# Test GitHub connection
ssh -T git@github.com
# Should return: "Hi abhimehro! You've successfully authenticated..."

# For complete setup guide, see:
# docs/ssh/SSH_1PASSWORD_GITHUB_SUCCESS.md
```

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

## 🚀 Installation

### Complete Setup
```bash
# Clone the repository
git clone <your-repo-url> ~/personal-config
cd ~/personal-config

# Install WORKING SSH configuration
cp configs/ssh/config-working ~/.ssh/config

# Test SSH + GitHub authentication
ssh -T git@github.com

# Deploy DNS management scripts
./dns-setup/scripts/deploy.sh

# Test everything
./tests/test_ssh_config.sh
```

### SSH Configuration Only ✅ **RECOMMENDED**
```bash
# Use the WORKING configuration
cp configs/ssh/config-working ~/.ssh/config

# Ensure 1Password SSH agent is enabled
# 1Password → Settings → Developer → SSH Agent ✅

# Import your SSH key to 1Password (manual method)
# 1Password → + → SSH Key → Import SSH Key → select ~/.ssh/id_ed25519

# Test GitHub connection
ssh -T git@github.com
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

## 🧪 Testing & Verification

### SSH Configuration ✅ **WORKING**
```bash
# Test GitHub SSH authentication (PRIMARY TEST)
ssh -T git@github.com
# Expected: "Hi abhimehro! You've successfully authenticated, but GitHub does not provide shell access."

# Check SSH agent status
ssh-add -l
# Shows keys loaded via 1Password

# Verify SSH config syntax
ssh -F ~/.ssh/config -T git@github.com
```

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

## 📊 Success Metrics

### SSH Configuration ✅ **VERIFIED WORKING**
- ✅ **GitHub Authentication** - SSH connection successful
- ✅ **1Password Integration** - SSH agent properly configured  
- ✅ **Configuration Backup** - Working config saved to repository
- ✅ **Documentation Complete** - Full troubleshooting history available
- ✅ **Reproducible Setup** - Can be deployed on new machines

**Key Details:**
- **Date Verified:** September 24, 2025
- **GitHub Username:** `abhimehro`
- **SSH Key Type:** ED25519
- **Authentication Method:** 1Password SSH Agent
- **Status:** Production ready ✅

## 🛠️ Troubleshooting

### SSH Issues (SOLVED ✅)
The SSH configuration has been fully resolved! For historical troubleshooting information, see:
- `docs/ssh/SSH_1PASSWORD_GITHUB_SUCCESS.md` - Complete solution documentation
- `docs/ssh/ssh_configuration_guide.md` - Comprehensive setup guide

**Common SSH Solutions:**
```bash
# If SSH fails, use the working configuration
cp configs/ssh/config-working ~/.ssh/config

# Ensure 1Password SSH agent is enabled
# 1Password → Settings → Developer → SSH Agent

# Test connection
ssh -T git@github.com
```

### DNS Issues
```bash
# Check what's using port 53
sudo lsof -nP -iTCP:53 -sTCP:LISTEN -iUDP:53

# Reset DNS to defaults
for s in $(networksetup -listallnetworkservices | tail -n +2 | sed 's/^*//'); do
  sudo networksetup -setdnsservers "$s" empty || true
done

# Check Control D status
~/bin/ctrld-switcher.sh status

# Restart Control D
sudo ~/bin/ctrld-switcher.sh restart
```

## 🎮 Use Cases

### Development Workflow ✅ **OPTIMIZED**
1. **Connect to GitHub**: `ssh -T git@github.com` (works perfectly!)
2. **Clone repositories**: `git clone git@github.com:username/repo.git`
3. **Privacy Mode**: `sudo ~/bin/ctrld-switcher.sh privacy`
4. **Code with enhanced security filtering**

### Gaming Session
1. **Gaming Mode**: `sudo ~/bin/ctrld-switcher.sh gaming`
2. **Minimal filtering for maximum performance**
3. **Optimized for Battle.net, Steam, Nvidia GeForce Now, Overwatch 2**

## 🔒 Security & Privacy

- **🔐 Secrets Management**: Uses 1Password for SSH keys ✅ **WORKING**
- **🌐 DNS Leak Protection**: Built-in firewall integration prevents leaks
- **🛡️ Profile Isolation**: Separate DNS policies for different use cases
- **📊 Verification**: Real-time testing ensures configuration integrity
- **🔄 Version Control**: All changes tracked with full history

## 📈 Version History

- **v4.1** (September 24, 2025) - ✅ **SSH + 1Password + GitHub WORKING SOLUTION**
- **v4.0** (September 2025) - Advanced Control D DNS Management with Performance Monitoring
- **v3.0** (September 2025) - Dynamic DNS Management System
- **v2.0** (August 2025) - SSH Configuration with 1Password
- **v1.0** (April 2025) - Initial repository structure

## 📄 License

Personal use configurations. Feel free to adapt and use any parts that are helpful for your own setup.

---

## 🎉 **SUCCESS SUMMARY**

**SSH + 1Password + GitHub Authentication: FULLY WORKING ✅**

- **Configuration**: `configs/ssh/config-working` 
- **Status**: Production ready as of September 24, 2025
- **GitHub User**: `abhimehro` authenticated successfully
- **Method**: 1Password SSH agent integration
- **Documentation**: Complete troubleshooting history available

**Your complete development and gaming network is now perfectly automated!**

_Last Updated: September 24, 2025_  
_SSH Configuration: v2.1 ✅ WORKING_  
_DNS Management System: v4.0_