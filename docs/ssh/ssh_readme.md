> **NOTE (2026):** This document describes the original 1Password-only SSH setup
> with `cursor-*` hostnames. Current generic hostnames (`dev-*`) and Proton Pass
> workflows are documented in the main `README.md` under _SSH Configuration_ and
> _Proton Pass SSH_.

# SSH Configuration

## 🔐 1Password + Cursor IDE SSH Setup

This directory contains a complete SSH configuration optimized for Cursor IDE development with 1Password SSH agent integration and dynamic VPN/local network support.

## 📁 Structure

```
ssh/
├── configs/ssh/              # Configuration files
│   ├── config               # Main SSH configuration
│   └── agent.toml          # 1Password SSH agent settings
├── scripts/ssh/              # Automation scripts
│   ├── smart_connect.sh     # Intelligent connection
│   ├── check_connections.sh # Connection testing
│   ├── setup_verification.sh # Setup validation
│   ├── diagnose_vpn.sh      # VPN troubleshooting
│   └── setup_aliases.sh     # Shell aliases
├── docs/ssh/                 # Documentation
│   ├── ssh_configuration_guide.md # Complete guide
│   ├── iTerm2_setup_guide.md      # iTerm2 integration
│   └── README.md                  # This file
└── tests/                    # Testing
    └── test_ssh_config.sh   # Configuration validation
```

## ⚡ Quick Start

```bash
# Install configuration
./scripts/install_ssh_config.sh

# Test setup
./tests/test_ssh_config.sh

# Connect automatically
~/.ssh/smart_connect.sh
```

## 🎯 Connection Methods

| Command            | Target                  | Best For                                                              |
| ------------------ | ----------------------- | --------------------------------------------------------------------- |
| `ssh cursor-mdns`  | `<mdns-hostname>.local` | **Primary** - Any network                                             |
| `ssh cursor-local` | `<local-hostname>`      | Local network only                                                    |
| `ssh cursor-auto`  | Auto-detection          | Cursor IDE backup                                                     |
| `ssh cursor-vpn`   | `<vpn-ip-address>`      | VPN connections (set HostName/Port locally; keep placeholders in git) |

## 🎨 IDE Usage

**For Cursor IDE:**

- **Primary:** `cursor-mdns`
- **Backup:** `cursor-auto`

**For iTerm2:**

- See [iTerm2 Setup Guide](iTerm2_setup_guide.md)

## 📋 Features

- ✅ **1Password SSH Agent** - Secure key management
- ✅ **Dynamic Network Support** - VPN on/off scenarios
- ✅ **Connection Multiplexing** - Fast reconnections
- ✅ **Automatic Fallback** - Multiple connection methods
- ✅ **Comprehensive Testing** - Built-in diagnostics
- ✅ **IDE Optimized** - Perfect for development

## 🛠️ Troubleshooting

```bash
# Check all connections
~/.ssh/check_connections.sh

# Verify setup
~/.ssh/setup_verification.sh

# VPN issues
~/.ssh/diagnose_vpn.sh

# Full configuration test
./tests/test_ssh_config.sh
```

## 📚 Documentation

- **[Complete Guide](ssh_configuration_guide.md)** - Comprehensive documentation
- **[iTerm2 Setup](iTerm2_setup_guide.md)** - Terminal integration
- **[Original README](README.md)** - Setup session notes

---

**Created:** 2025-08-04
**Status:** ✅ Production Ready
