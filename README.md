# Personal System Configuration

A repository for personal system configurations, scripts, and documentation to make my macOS setup reproducible and backed up.

## Overview

This repository contains configuration files, shell scripts, and documentation for my personal computing environment. By keeping these files in a Git repository, I can:
- Back up important configurations and documentation
- Track changes to my system setup over time
- Easily reproduce my environment on a new machine
- Share specific configurations or scripts with others when needed
- Document solutions to problems I've solved

## Repository Structure

```
personal-config/
├── docs/                   # Documentation and guides
│   ├── ssh/               # SSH configuration documentation
│   │   ├── ssh_configuration_guide.md    # Complete SSH setup guide
│   │   ├── iTerm2_setup_guide.md         # iTerm2 integration
│   │   └── README.md                     # SSH documentation index
│   └── vpn_switching_guide.md            # VPN switching workflow
├── configs/                # Configuration files (dotfiles)
│   └── ssh/               # SSH configuration files
│       ├── config         # Main SSH configuration
│       └── agent.toml     # 1Password SSH agent settings
├── scripts/                # Automation scripts
│   ├── ssh/               # SSH-related scripts
│   │   ├── smart_connect.sh        # Intelligent SSH connection
│   │   ├── check_connections.sh    # Connection testing
│   │   ├── setup_verification.sh   # Setup validation
│   │   ├── diagnose_vpn.sh         # VPN troubleshooting
│   │   └── setup_aliases.sh        # Shell aliases
│   └── install_ssh_config.sh       # SSH configuration installer
├── tests/                  # Testing scripts
│   ├── test_ssh_config.sh  # SSH configuration validation
│   └── test_config_fish.sh # Fish shell configuration test
└── README.md               # This file
```

## 🔐 SSH Configuration (New!)

Complete SSH setup optimized for Cursor IDE development with 1Password integration and dynamic VPN/local network support.

### Quick Start
```bash
# Install SSH configuration
./scripts/install_ssh_config.sh

# Test setup
./tests/test_ssh_config.sh

# Connect to your machine
ssh cursor-mdns  # Primary method (works anywhere)
```

### Features
- **🔐 1Password SSH Agent** - Secure key management without local storage
- **🌐 Dynamic Network Support** - Automatically handles VPN on/off scenarios
- **🎨 Cursor IDE Optimized** - Perfect for remote development workflows
- **📱 mDNS/Bonjour Support** - Reliable local machine connections
- **🔧 Multiple Connection Methods** - Fallback options for reliability
- **📊 Comprehensive Diagnostics** - Built-in troubleshooting and testing

### Documentation
- **[Complete SSH Guide](docs/ssh/ssh_configuration_guide.md)** - Comprehensive setup and usage
- **[iTerm2 Integration](docs/ssh/iTerm2_setup_guide.md)** - Terminal setup guide

## Documentation

### VPN Switching Guide

The VPN Switching Guide documents the workflow for switching between Cloudflare WARP+Control D DNS and ProtonVPN configurations for different use cases. It includes step-by-step instructions, troubleshooting steps, and technical details.

### MacOS Resource Monitor MCP Server

The MacOS Resource Monitor guide explains how to run the lightweight MCP server that exposes CPU, memory, and network usage on macOS. It covers installation, usage, integration with LLM clients, and troubleshooting tips.

## Installation

### SSH Configuration
```bash
# Quick install
./scripts/install_ssh_config.sh

# Manual install
cp configs/ssh/config ~/.ssh/config
cp configs/ssh/agent.toml ~/.ssh/agent.toml
chmod 600 ~/.ssh/config ~/.ssh/agent.toml
```

### General Usage
```bash
# Clone the repository
git clone https://github.com/abhimehro/personal-config.git

# Copy configuration files to appropriate locations
# or symbolic link them from your home directory
```

## Testing

### SSH Configuration
```bash
# Comprehensive SSH tests
./tests/test_ssh_config.sh

# Manual verification
./scripts/ssh/setup_verification.sh
```

### Fish Shell Configuration
```bash
# Verify Fish shell configuration
./tests/test_config_fish.sh
```

## Usage Examples

### SSH Connections
```bash
# Smart auto-connect (detects network and connects optimally)
./scripts/ssh/smart_connect.sh

# Direct connections
ssh cursor-mdns     # Primary - works with/without VPN
ssh cursor-local    # Local network only
ssh cursor-auto     # Auto-detection backup

# Check all connection methods
./scripts/ssh/check_connections.sh
```

### Cursor IDE
1. Install Remote-SSH extension
2. Connect to host: `cursor-mdns` (recommended)
3. Enjoy seamless development with 1Password authentication

## Future Additions

This repository will continue to grow to include:
- ✅ SSH configuration for development (COMPLETE)
- Shell scripts for automation of routine tasks
- Dotfiles (.bashrc, .bash_profile, etc.)
- Application-specific configuration files
- System setup documentation for new machines
- Additional guides for software configuration

## License

These configurations and scripts are for personal use, but feel free to use or adapt them if you find them helpful.

---

_Created: April 11, 2025_  
_SSH Configuration Added: August 4, 2025_