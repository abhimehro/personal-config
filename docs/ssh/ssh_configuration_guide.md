# SSH Configuration for Cursor IDE & 1Password

## 🎯 Overview

This SSH configuration provides seamless integration between Cursor IDE, 1Password SSH agent, and dynamic VPN/local network scenarios. It automatically handles connections whether you're on VPN or local network, with optimized settings for IDE usage.

## ✨ Features

- **🔐 1Password SSH Agent Integration** - Secure key management without storing keys locally
- **🌐 Dynamic VPN/Local Network Support** - Automatically adapts to network changes
- **🎨 Cursor IDE Optimized** - Perfect for remote development workflows
- **📱 mDNS/Bonjour Support** - Reliable local machine connections
- **🔧 Multiple Connection Methods** - Fallback options for reliability
- **📊 Comprehensive Diagnostics** - Built-in troubleshooting and testing

## 🏗️ Architecture

### SSH Host Configurations

| Host | Target | Use Case | Network |
|------|--------|----------|---------|
| `cursor-mdns` | `<mdns-hostname>.local` | **Primary** - Most reliable | Any |
| `cursor-local` | `<local-hostname>` | Local network only | Local |
| `cursor-vpn` | `<vpn-ip-address>` | VPN connections | VPN |
| `cursor-auto` | `<mdns-hostname>.local` | Smart detection | Any |

### Connection Priority

1. **🥇 mDNS** (`cursor-mdns`) - Most reliable for local machine connections
2. **🥈 Local hostname** (`cursor-local`) - Good for local network
3. **🥉 VPN** (`cursor-vpn`) - For remote connections (different machines)

## 🚀 Quick Start

### Installation

```bash
# Clone your personal-config repository
git clone https://github.com/REPO_OWNER/REPO_NAME.git
cd personal-config

# Run installation script
./scripts/install_ssh_config.sh

# Verify installation
./tests/test_ssh_config.sh
```

### Immediate Usage

```bash
# Smart auto-connect (recommended)
~/.ssh/smart_connect.sh

# Direct connections
ssh cursor-mdns     # Primary method
ssh cursor-local    # Local network
ssh cursor-auto     # Auto-detection

# Check all connection methods
~/.ssh/check_connections.sh
```

### Cursor IDE Setup

1. **Install Remote-SSH extension**
2. **Connect to host:** `cursor-mdns` (recommended)
3. **Alternative hosts:** `cursor-local`, `cursor-auto`

## 📋 Prerequisites

### Required Software

- **macOS** (this configuration is macOS-specific)
- **1Password 8+** with SSH agent enabled
- **SSH client** (built into macOS)
- **Cursor IDE** with Remote-SSH extension

### 1Password Setup

1. **Open 1Password** → Settings → Developer
2. **Enable SSH Agent** ✅
3. **Add SSH keys** to your vault (Personal/Private)
4. **Verify:** Run `ssh-add -l` to see available keys

### Network Requirements

- **Target machine** must have SSH enabled (System Preferences → Sharing → Remote Login)
- **Firewall** configured to allow SSH connections
- **Network connectivity** between machines

## 🛠️ Configuration Files

### `/configs/ssh/config`
Main SSH configuration with host definitions, 1Password integration, and optimization settings.

### `/configs/ssh/agent.toml`
1Password SSH agent configuration specifying which vaults and keys to use.

## 🔧 Scripts

### Core Scripts

- **`smart_connect.sh`** - Intelligent connection with automatic fallback
- **`check_connections.sh`** - Test all connection methods
- **`setup_verification.sh`** - Comprehensive setup validation
- **`diagnose_vpn.sh`** - VPN-specific troubleshooting

### Utility Scripts

- **`setup_aliases.sh`** - Create convenient shell aliases
- **`install_ssh_config.sh`** - Automated installation

## 🧪 Testing

```bash
# Run comprehensive tests
./tests/test_ssh_config.sh

# Manual verification
~/.ssh/setup_verification.sh

# Check specific connections
~/.ssh/check_connections.sh
```

## 🌐 Network Scenarios

### Scenario 1: Local Network (VPN OFF)
- **Best:** `ssh cursor-mdns` or `ssh cursor-local`
- **Target:** Local hostname resolution
- **Optimizations:** Compression disabled for speed

### Scenario 2: VPN Connected (Windscribe/etc)
- **Best:** `ssh cursor-mdns` (still works!)
- **Alternative:** `ssh cursor-vpn` (for different machines)
- **Optimizations:** Compression enabled, extra keepalives

### Scenario 3: mDNS/Bonjour Fallback
- **Always works:** `ssh cursor-mdns`
- **Target:** Bonjour service discovery
- **Use case:** When hostname resolution fails

## 🔍 Troubleshooting

### Common Issues

**Connection timeouts:**
```bash
# Check network connectivity
~/.ssh/check_connections.sh

# Test specific method
ping <mdns-hostname>.local
```

**1Password authentication fails:**
```bash
# Verify SSH agent
ssh-add -l

# Check 1Password settings
# 1Password → Settings → Developer → SSH Agent
```

**Host key verification errors:**
- Automatically handled with `StrictHostKeyChecking accept-new`
- Old keys are safely replaced

**VPN connection issues:**
```bash
# Run VPN diagnostics
~/.ssh/diagnose_vpn.sh
```

### Debug Mode

For detailed connection information:
```bash
ssh -vvv cursor-mdns
```

## 🎨 IDE Integration

### Cursor IDE

**Recommended setup:**
1. **Primary host:** `cursor-mdns`
2. **Backup host:** `cursor-auto`
3. **Connection multiplexing:** Enabled (30-minute persist)
4. **Authentication:** Automatic via 1Password

### iTerm2

See [iTerm2 Setup Guide](iTerm2_setup_guide.md) for detailed configuration.

## 🔒 Security

### Key Management
- **No local key storage** - All keys managed by 1Password
- **Automatic key rotation** supported
- **Secure vault storage** with 1Password encryption

### Network Security
- **Host key verification** with automatic updates
- **Modern encryption** (ED25519 preferred)
- **Connection multiplexing** for efficiency

### Best Practices
- **Regular key rotation** through 1Password
- **VPN usage** for remote connections
- **Firewall configuration** on target machines

## 📚 Additional Resources

- **[iTerm2 Setup Guide](iTerm2_setup_guide.md)** - Complete iTerm2 integration
- **[1Password SSH Guide](https://developer.1password.com/docs/ssh/)** - Official documentation
- **[SSH Config Manual](https://man.openbsd.org/ssh_config)** - SSH configuration reference

## 🤝 Contributing

This is a personal configuration, but improvements and suggestions are welcome:

1. **Test changes** with `./tests/test_ssh_config.sh`
2. **Document updates** in this README
3. **Verify compatibility** across different network scenarios

## 📝 Changelog

- **2025-08-04:** Initial SSH configuration with 1Password integration
- **2025-08-04:** Added dynamic VPN/local network support
- **2025-08-04:** Created comprehensive testing and documentation

---

**Status:** ✅ Production Ready  
**Last Updated:** August 4, 2025  
**Compatibility:** macOS with 1Password 8+