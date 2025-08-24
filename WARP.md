# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

# Personal Configuration Repository Guide

This repository provides SSH configuration for macOS development environments, optimized for Cursor IDE and 1Password integration. It includes automated setup scripts, comprehensive testing, and support for dynamic VPN/local network scenarios.

## Environment Assumptions

- **macOS** (primary target platform)
- **Warp shell**: bash (Preferences → Shell → /bin/bash - preferred due to Fish/Warp compatibility issues)
- **1Password 8+** with SSH Agent enabled (Settings → Developer → SSH Agent)
- **Development tools**: Git, SSH, Homebrew with Node/npm and Python3 at `/opt/homebrew/bin`
- **gcloud CLI** installed with default project `perplexity-clone-project`
- **macOS Remote Login** enabled on target machines (System Settings → General → Sharing → Remote Login)

## TL;DR - Quick Start

```bash path=null start=null
# Clone and setup
git clone https://github.com/abhimehro/personal-config.git
cd personal-config

# Install SSH configuration (creates backups, copies files, links scripts)
./scripts/install_ssh_config.sh

# Validate installation
./tests/test_ssh_config.sh

# Connect using smart auto-detection
~/.ssh/smart_connect.sh

# Manual connection options
ssh cursor-mdns    # Primary (mDNS/Bonjour) - most reliable
ssh cursor-local   # Local network only
ssh cursor-auto    # Auto-detection with short timeout

# Diagnostic tools
~/.ssh/check_connections.sh     # Test all connection methods
~/.ssh/setup_verification.sh    # End-to-end validation
~/.ssh/diagnose_vpn.sh          # VPN-specific troubleshooting
```

1Password SSH agent verification:
```bash path=null start=null
ls -l ~/Library/Group\ Containers/2BUA8C4S2C.com.1password/t/agent.sock
SSH_AUTH_SOCK=~/Library/Group\ Containers/2BUA8C4S2C.com.1password/t/agent.sock ssh-add -l
```

## Repository Architecture

```
personal-config/
├── docs/
│   ├── ssh/                           # Complete SSH setup guides
│   │   ├── ssh_configuration_guide.md # Full setup and usage guide
│   │   ├── iTerm2_setup_guide.md      # Terminal integration
│   │   └── README.md                  # SSH documentation index
│   └── vpn_switching_guide.md         # VPN workflow documentation
├── configs/
│   ├── ssh/
│   │   ├── config                     # Main SSH configuration
│   │   └── agent.toml                 # 1Password SSH agent settings
│   └── fish/
│       └── config.fish                # Fish shell config (optional in Warp)
├── scripts/
│   ├── ssh/                           # SSH automation scripts
│   │   ├── smart_connect.sh           # Intelligent connection with fallbacks
│   │   ├── check_connections.sh       # Test all connection methods
│   │   ├── setup_verification.sh      # Comprehensive setup validation
│   │   ├── diagnose_vpn.sh           # VPN troubleshooting
│   │   └── setup_aliases.sh          # Optional shell aliases
│   └── install_ssh_config.sh          # Main installation script
├── tests/
│   ├── test_ssh_config.sh             # SSH configuration test suite
│   └── test_config_fish.sh            # Fish config syntax validation
├── README.md                          # Complete repository documentation
└── SUMMARY.md                         # What's included summary
```

**Installation Flow:**
1. `install_ssh_config.sh` backs up existing `~/.ssh/config`
2. Copies `configs/ssh/*` to `~/.ssh/`
3. Sets proper permissions (600)
4. Creates `~/.ssh/control/` directory for ControlMaster
5. Links scripts to `~/.ssh/` for easy access

## SSH Workflow and Connection Hosts

**SSH Host Definitions:**
- `cursor-mdns` → `Abhis-MacBook-Air.local` (Primary - works with/without VPN)
- `cursor-local` → `abhis-macbook-air` (Local network only)
- `cursor-vpn` → `**************` (Placeholder - replace with your VPN/Tailscale IP)
- `cursor-auto` → `Abhis-MacBook-Air.local` (Quick autodetect with short timeouts)

**Connection Priority:**
1. **mDNS (cursor-mdns)**: Most reliable for same-machine connections
2. **Local hostname (cursor-local)**: Good for local network
3. **VPN (cursor-vpn)**: For cross-machine connections (requires HostName configuration)

**Key Configuration Paths:**
- `~/.ssh/config` and `~/.ssh/agent.toml` (installed from `configs/ssh/`)
- IdentityAgent: `~/Library/Group Containers/2BUA8C4S2C.com.1password/t/agent.sock`
- Control sockets: `~/.ssh/control/`

**Test Validation:**
- Verifies `ssh -G cursor-mdns` syntax
- Confirms 1Password agent socket exists and responds
- Validates hostname resolution for `Abhis-MacBook-Air.local` and `abhis-macbook-air`

## Common Commands

**Setup and Installation:**
```bash path=null start=null
./scripts/install_ssh_config.sh
chmod 600 ~/.ssh/config ~/.ssh/agent.toml
```

**Validation and Testing:**
```bash path=null start=null
./tests/test_ssh_config.sh
~/.ssh/setup_verification.sh
```

**Connectivity and Connection:**
```bash path=null start=null
~/.ssh/check_connections.sh
~/.ssh/smart_connect.sh
ssh -vvv cursor-mdns    # Debug connection
```

**Network Testing:**
```bash path=null start=null
ping Abhis-MacBook-Air.local
ping abhis-macbook-air
```

**1Password Agent Management:**
```bash path=null start=null
SSH_AUTH_SOCK=~/Library/Group\ Containers/2BUA8C4S2C.com.1password/t/agent.sock ssh-add -l
```

**Troubleshooting:**
```bash path=null start=null
# Clear stuck ControlMaster sockets
rm -f ~/.ssh/control/* 2>/dev/null || true

# Update VPN hostname placeholder (local changes only)
sed -i '' -e 's/**************/YOUR_VPN_HOSTNAME/g' configs/ssh/config
./scripts/install_ssh_config.sh
```

**Git Operations:**
```bash path=null start=null
git add WARP.md
git commit -m "docs(warp): add Warp guide for personal-config"
git push
```

## Network Scenarios

**Local Network (VPN OFF):**
- Use: `ssh cursor-mdns` or `ssh cursor-local`
- Test: `ping Abhis-MacBook-Air.local`

**VPN Connected:**
- Preferred: `ssh cursor-mdns` (usually still works)
- Alternative: `ssh cursor-vpn` (for cross-machine connections; requires HostName setup)

**Debugging Network Issues:**
- `~/.ssh/check_connections.sh` - Test all methods
- `~/.ssh/diagnose_vpn.sh` - VPN-specific diagnostics
- `ssh -vvv cursor-mdns` - Verbose SSH debugging

## Security and Host Key Handling

- **Key Management**: All SSH keys managed by 1Password; no private keys stored locally
- **Host Key Checking**: 
  - `StrictHostKeyChecking accept-new` on configured hosts (minimizes prompts)
  - Global default remains `ask` for security
- **Known Hosts**: Hashed and stored in `~/.ssh/known_hosts`
- **Control Sockets**: Stored in `~/.ssh/control/` with proper permissions
- **Secrets**: Keep `**************` placeholders in source; override locally as needed

## Path Inconsistencies and Solutions

**SSH Configuration Paths:**
- Canonical location: `configs/ssh/` (matches installer and documentation)
- If legacy `configs/.ssh/` files exist, consolidate:
```bash path=null start=null
# Consolidate SSH config location
git mv configs/.ssh/* configs/ssh/ 2>/dev/null || true
```

**Fish Configuration Test:**
- Test expects: `.config/fish/config.fish`
- Actual location: `configs/fish/config.fish`
- Note: Warp defaults to bash; Fish tests are optional

Fix test path if needed:
```bash path=null start=null
sed -i '' 's|\$REPO_ROOT/.config/fish/config.fish|\$REPO_ROOT/configs/fish/config.fish|' tests/test_config_fish.sh
```

## Optional: Warp Workflows Integration

Create `.warp/workflows.yaml` in repository root for quick access to common commands:

```yaml path=null start=null
workflows:
  - name: Install SSH configuration
    command: ./scripts/install_ssh_config.sh
    tags: [setup, ssh]

  - name: Test SSH configuration
    command: ./tests/test_ssh_config.sh
    tags: [test, ssh]

  - name: Smart connect (auto)
    command: ~/.ssh/smart_connect.sh
    tags: [ssh, connect]

  - name: Check connections
    command: ~/.ssh/check_connections.sh
    tags: [ssh, diagnose]

  - name: Diagnose VPN
    command: ~/.ssh/diagnose_vpn.sh
    tags: [vpn, diagnose]
```

Access via Warp Command Palette → Workflows.

## Development Workflow

1. **Initial Setup**: Clone repository and run `./scripts/install_ssh_config.sh`
2. **Validation**: Execute `./tests/test_ssh_config.sh` to verify configuration
3. **Connection**: Use `~/.ssh/smart_connect.sh` for intelligent connection or direct `ssh cursor-mdns`
4. **Cursor IDE**: Connect using Remote-SSH extension with host `cursor-mdns`
5. **Troubleshooting**: Use diagnostic scripts in `scripts/ssh/` directory

## References and Documentation

- **[Complete SSH Configuration Guide](docs/ssh/ssh_configuration_guide.md)** - Comprehensive setup and usage
- **[iTerm2 Integration Guide](docs/ssh/iTerm2_setup_guide.md)** - Terminal setup instructions  
- **[Repository Overview](README.md)** - Complete project documentation
- **[VPN Switching Guide](docs/vpn_switching_guide.md)** - VPN workflow documentation
