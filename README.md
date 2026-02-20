# Personal System Configuration

A comprehensive repository for personal system configurations, scripts, and documentation to make my macOS development and gaming setup reproducible and backed up.

## Overview

This repository contains configuration files, automation scripts, and detailed documentation for my personal computing environment. Key features:

- **🔐 Secure SSH Configuration** - 1Password integration with dynamic network support
- **🌐 Enhanced VPN + DNS Integration** - Windscribe VPN with Control D privacy filtering
- **🛡️ Dual Protection System** - VPN encryption + DNS privacy filtering with real-time logging
- **🛠️ Automated Maintenance System** - Comprehensive system health monitoring and cleanup (NEW!)
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

### ProtonDrive one-way home backup
```bash
# Safe preview (no changes)
./scripts/protondrive_backup.sh --dry-run --no-delete

# Live mirror into ProtonDrive (uses --delete-delay unless you pass --no-delete)
./scripts/protondrive_backup.sh --run
```
Edit `./scripts/protondrive_backup.exclude` to tune exclusions (git repos, build artifacts, caches, etc.).

### Bootstrap this Mac (idempotent)
```bash
cd ~/Documents/dev/personal-config
./setup.sh
# Requires: macOS, Homebrew, 1Password CLI (`op`), rclone installed via brew
# Does:
#  - Links dotfiles (SSH, fish, Cursor/VSCode) with backup/verify
#  - Installs maintenance launchd agents
#  - Prepares Control D / Windscribe helpers
#  - Seeds rclone config from template (fill secrets via 1Password)
#  - Stages media services + LaunchAgents (WebDAV + Alldebrid)
```

### Automated Maintenance System (NEW!)
```bash
# Check system health
~/Documents/dev/personal-config/maintenance/bin/run_all_maintenance.sh health

# Quick system cleanup
~/Documents/dev/personal-config/maintenance/bin/run_all_maintenance.sh quick

# View automation status
launchctl list | grep maintenance

# View latest health report
ls ~/Library/Logs/maintenance/health_report-*.txt | tail -1 | xargs cat
```

### Enhanced VPN + DNS Integration

**Using Fish Shell Functions (Recommended):**
```bash
# After installing configs and reloading fish shell (exec fish)
nm-status          # Check current network status
nm-browse          # Switch to Control D browsing mode
nm-privacy         # Switch to Control D privacy mode
nm-gaming          # Switch to Control D gaming mode
nm-vpn             # Switch to Windscribe VPN mode
nm-regress         # Run full regression test
nm-cd-status       # Check Control D daemon status
```

**Using Scripts Directly:**
```bash
# Preferred: use the unified network mode manager
./scripts/network-mode-manager.sh controld browsing   # Enable Control D DNS mode
./scripts/network-mode-manager.sh windscribe          # Enable Windscribe VPN mode

# Full end-to-end regression (Control D → Windscribe)
./scripts/network-mode-regression.sh browsing
```

Under the hood, `controld-system/scripts/controld-manager` remains the engine that
starts `ctrld` and applies the correct Control D profile; `network-mode-manager.sh`
wraps this with IPv6 management, DNS routing, and verification.

### SSH Configuration
```bash
# Install SSH configuration with 1Password integration
./scripts/install_ssh_config.sh

# Test your setup
./tests/test_ssh_config.sh

# Connect to development machine (generic hostnames)
ssh dev-mdns   # Primary (works with/without VPN)
ssh dev-auto   # Smart alias / fallback
```

> Note: SSH dev hosts (`dev-mdns`, `dev-local`, `dev-auto`) are defined locally
> in `~/.ssh/config.local`. See the **Troubleshooting** section below if
> connections fail.

### Legacy DNS Management (v3.x)
```bash
# Alternative direct DNS switching (without VPN)
# Kept for fallback and historical reference; v4.x prefers network-mode-manager.
sudo dns-privacy     # Privacy mode
sudo dns-gaming      # Gaming mode
```

## 📁 Repository Structure

```
personal-config/
├── 🛠️ maintenance/            # Automated Maintenance System (NEW!)
│   ├── bin/                   # Executable maintenance scripts
│   │   ├── run_all_maintenance.sh  # Master orchestration script
│   │   ├── health_check.sh    # System health monitoring
│   │   └── quick_cleanup.sh   # Quick system cleanup
│   ├── conf/                  # Configuration files
│   ├── lib/                   # Shared libraries
│   └── README.md              # Maintenance system guide
├── 🌐 windscribe-controld/     # Enhanced VPN + DNS Integration
│   ├── windscribe-controld-setup.sh  # Automated setup & verification
│   ├── setup-guide.md         # Complete integration guide
│   └── ctrld.toml.backup      # Configuration backup
├── 🌐 dns-setup/              # Dynamic DNS Management System
│   ├── scripts/               # DNS switching automation
│   │   ├── dns-privacy        # Privacy profile switcher
│   │   ├── dns-gaming         # Gaming profile switcher
│   │   ├── deploy.sh          # Script deployment tool
│   │   └── README.md          # Comprehensive DNS guide
│   ├── DEPLOYMENT_SUMMARY.md  # Complete setup documentation
│   └── backups/               # Network configuration backups
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

### 🌐 Dynamic DNS Management (New!)

Intelligent DNS switching system with Control D integration:

**Privacy Mode (`dns-privacy`)**
- Enhanced security filtering
- Malware & tracking protection
- Optimized for browsing and AI applications
- Profile ID: `2eoeqoo9ib9`

**Gaming Mode (`dns-gaming`)**
- Minimal filtering for maximum performance
- Gaming service optimizations (Battle.net, GeForce Now, Overwatch 2)
- Ultra-low latency DNS resolution
- Profile ID: `1igcvpwtsfg`

**Features:**
- ✅ **Windscribe VPN Integration** - Seamless VPN compatibility
- ✅ **Profile-Specific DoH Endpoints** - Optimized upstream resolvers
- ✅ **Automatic Network Detection** - Skips VPN interfaces intelligently
- ✅ **DNS Leak Protection** - Built-in firewall integration
- ✅ **Smart Verification** - Real-time DNS resolution testing
- ✅ **One-Command Switching** - Simple `sudo dns-*` commands

### 🔐 SSH Configuration

Professional SSH setup optimized for development:

**Features:**
- **🔐 1Password SSH Agent** - Secure key management without local storage
- **🌐 Dynamic Network Support** - VPN-aware connection methods
- **🎨 Cursor IDE Optimized** - Perfect remote development setup
- **📱 mDNS/Bonjour Support** - Reliable local machine discovery
- **🔧 Multiple Fallback Options** - Connection reliability guaranteed
- **📊 Comprehensive Diagnostics** - Built-in testing and troubleshooting

**Connection Methods (generic hostnames):**
```bash
ssh dev-mdns    # Primary (works with/without VPN)
ssh dev-local   # Local network only
ssh dev-auto    # Auto-detection fallback
```

## 🚀 Installation

### Complete Setup (Recommended)
```bash
# Clone the repository
git clone <your-repo-url> ~/Documents/dev/personal-config
cd ~/Documents/dev/personal-config

# Install all configuration files (symlinks to home directory)
./scripts/install_all_configs.sh

# This will:
# - Create symlinks for SSH, Fish shell, Cursor, VS Code configs
# - Backup any existing configuration files
# - Verify all symlinks are correctly established
# - Set up Control D fish functions

# Reload fish shell to use new functions
exec fish

# Test Control D functions
nm-status          # Check network status
```

### Configuration Management (Symlink-Based)

This repository uses a **symlink-based configuration** model where repository files are linked to your home directory. This ensures:
- ✅ Repository updates automatically reflect in your home directory
- ✅ Single source of truth for all configurations
- ✅ Easy backup and restore via git

**Symlinked Configurations:**
- `~/.ssh/config` → `configs/ssh/config`
- `~/.ssh/agent.toml` → `configs/ssh/agent.toml`
- `~/.config/fish/` → `configs/.config/fish/`
- `~/.cursor/` → `.cursor/`
- `~/.vscode/` → `.vscode/`

**Management Commands:**
```bash
# Sync all configs (create/update symlinks)
./scripts/sync_all_configs.sh

# Verify all symlinks are correct
./scripts/verify_all_configs.sh

# Complete installation (sync + verify)
./scripts/install_all_configs.sh
```

### Individual Component Setup

#### SSH Configuration Only
```bash
# Quick install
./scripts/install_ssh_config.sh

# Or use the sync script
./scripts/sync_ssh_config.sh
./scripts/verify_ssh_config.sh
```

### DNS Management Only
```bash
# Deploy DNS scripts to ~/bin
./dns-setup/scripts/deploy.sh

# Switch profiles
sudo dns-privacy  # Enhanced privacy filtering
sudo dns-gaming   # Gaming optimization
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

### Media automation (Infuse + Alldebrid + cloud union)
- **Data roots**: iCloud Desktop/Documents (`~/Library/Mobile Documents/com~apple~CloudDocs/Media`) via rclone union of `gdrive:Media` + `onedrive:Media` (no local duplication).
- **WebDAV server**: LaunchAgent `com.abhimehrotra.media.webdav` runs `/Users/abhimehrotra/Library/Media/bin/start-media-server.sh` on port **8088** (read-only).
- **Alldebrid helper**: LaunchAgent `com.abhimehrotra.media.alldebrid` mounts to `/Users/abhimehrotra/mnt/alldebrid` and serves on **8080**.
- **Secrets**:
  - `~/.config/rclone/rclone.conf` (seed from `media-streaming/configs/rclone.conf.template`, fill via `op inject`).
  - `~/.config/media-server/credentials` (untracked; copy `media-streaming/configs/media-credentials.example` and inject creds with 1Password).
- **Cache & logs**: `~/Library/Application Support/MediaCache` (kept out of iCloud) and `~/Library/Logs/media/*.out|*.err`.
- **Control**: `launchctl list | grep media` to verify; manual start: `~/Library/Media/bin/start-media-server.sh`.

### MCP tooling
- Templates live in `mcp-configs/README.md` and `mcp-configs/mcp-servers.template.json`.
- Copy the template to a local `servers.local.json`, fill keys from 1Password, and keep it gitignored (patterns already in `.gitignore`).
- When running commands that need secrets resolved from 1Password, use `op run -- <command>` (e.g., `op run -- uv run python main.py --dry-run --profiles dummy`).

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

## ⚡ Performance Benchmarking

This repository includes a performance benchmarking infrastructure for tracking script execution speed and detecting performance regressions.

### Quick Start

```bash
# Install hyperfine (required dependency)
brew install hyperfine

# Run all benchmarks
make benchmark

# Run specific benchmark
./tests/benchmarks/benchmark_scripts.sh nm-status
```

### Available Benchmark Targets

| Target | Script | Description |
|--------|--------|-------------|
| `nm-status` | `network-mode-manager.sh status` | Network mode status check |
| `sync-all` | `sync_all_configs.sh` | Configuration sync operations |
| `verify-all` | `verify_all_configs.sh` | Configuration verification |
| `all` | All scripts above | Run all benchmarks (default) |

### Benchmark Configuration

- **Warmup Runs**: 2 iterations to prime caches
- **Benchmark Runs**: 5 iterations for statistical accuracy
- **Baseline Storage**: `tests/benchmarks/baselines/*.json`

### Usage Examples

```bash
# Benchmark network mode status check
./tests/benchmarks/benchmark_scripts.sh nm-status

# Benchmark config sync performance
./tests/benchmarks/benchmark_scripts.sh sync-all

# Benchmark verification speed
./tests/benchmarks/benchmark_scripts.sh verify-all

# Run all benchmarks via Makefile
make benchmark
```

### Baseline Results

Results are saved as JSON files in `tests/benchmarks/baselines/` for:
- Performance regression tracking
- Before/after optimization comparisons
- CI/CD integration potential

## 📊 Monitoring & Maintenance

### DNS Logs
```bash
# View DNS switching logs
sudo tail -f /var/log/ctrld-privacy.log
sudo tail -f /var/log/ctrld-gaming.log

# Check daemon status
sudo lsof -nP -iTCP:53 -sTCP:LISTEN -iUDP:53
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
1. **Connect**: `ssh dev-mdns`
2. **Privacy Mode**: `sudo dns-privacy`
3. **Code with enhanced security filtering`

### Gaming Session
1. **Gaming Mode**: `sudo dns-gaming`
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
```

**SSH connection issues:**
```bash
# Comprehensive diagnostics
./scripts/ssh/diagnose_vpn.sh

# Test individual connection methods
./scripts/ssh/check_connections.sh
```

### Support Resources

- **[DNS Setup Guide](dns-setup/scripts/README.md)** - Complete DNS documentation
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

- **v4.1** (November 2025) - Network mode manager + regression harness; refined verification & docs; archived legacy Windscribe glue.
- **v4.0** (October 2025) - Enhanced VPN + DNS Integration with Windscribe + Control D
- **v3.0** (September 2025) - Dynamic DNS Management System
- **v2.0** (August 2025) - SSH Configuration with 1Password
- **v1.0** (April 2025) - Initial repository structure

## 📄 License

Personal use configurations. Feel free to adapt and use any parts that are helpful for your own setup.

---

**🎉 Your complete development and gaming network is now perfectly automated!**

_Last Updated: November 19, 2025_
_VPN + DNS Integration: v4.1_
_DNS Management System: v3.0_
_SSH Configuration: v2.0_

## 🔧 Configuration Details

### SSH Configuration (1Password-managed)

- Single source of truth for SSH config and agent settings lives in this repo:
  - `configs/ssh/config`
  - `configs/ssh/agent.toml`
- Local symlinks:
  - `~/.ssh/config` → `~/Documents/dev/personal-config/configs/ssh/config`
  - `~/.ssh/agent.toml` → `~/Documents/dev/personal-config/configs/ssh/agent.toml`
- 1Password integration:
  - Include `~/.ssh/1Password/config`
  - IdentityAgent: `~/Library/Group Containers/2BUA8C4S2C.com.1password/t/agent.sock`
- Multiplexing control dir:
  - `~/.ssh/control` (700)

**Maintenance:**
- Verify: `scripts/verify_ssh_config.sh`
- Sync: `scripts/sync_ssh_config.sh`

**Notes:**
- Keep 1Password unlocked with SSH agent integration enabled.
- No private keys are stored in `~/.ssh`; all keys are 1Password-managed.

### Proton Pass SSH (optional second agent)

- Proton vaults:
  - `Personal` (general items)
  - `SSH Keys` (dedicated vault for SSH keys)
- Helper scripts (all under `scripts/ssh/`):
  - `op_to_proton_import.sh` – paste a private key from 1Password → import into Proton (`SSH Keys` vault) with a secure temp file workflow.
  - `proton_ssh_helpers.sh` – wrapper for:
    - `start-agent` – `pass-cli ssh-agent start --vault-name "SSH Keys"`
    - `load-into-agent` – `pass-cli ssh-agent load --vault-name "SSH Keys"`
    - `import-key` – calls `op_to_proton_import.sh`.
- Fish functions (auto-loaded from `~/.config/fish/conf.d/proton_pass_ssh.fish`):
  - `pp_ssh_agent_start` – start Proton SSH agent for `SSH Keys` vault.
  - `pp_use_proton_agent` – point current shell at Proton’s agent socket.
  - `pp_load_proton_into_agent` – load Proton keys into whatever agent `SSH_AUTH_SOCK` points at.
  - `pp_which_agent` – show active agent + listed keys.
  - Abbreviations: `pp-start`, `pp-load`, `pp-import` (wrappers around the above).
- SSH host aliases (in `configs/ssh/config`):
  - `github-proton` – same as `github.com` but bound to Proton’s `IdentityAgent`.
  - `proton-*` – any host matching this pattern prefers Proton’s agent.

**Usage examples:**
```bash
# Import a key from 1Password into Proton (SSH Keys vault)
./scripts/ssh/op_to_proton_import.sh "GitHub main SSH key"

# Start Proton SSH agent (dedicated tab)
./scripts/ssh/proton_ssh_helpers.sh start-agent

# In a different shell, point SSH to Proton agent
pp-start         # or: pp_ssh_agent_start in one tab
pp-use-proton    # then: ssh -T git@github-proton
```

### Fish Shell Configuration

**Control D Network Mode Functions:**

After installing configs and reloading fish shell (`exec fish`), you'll have access to these convenient functions:

| Function | Description |
|----------|-------------|
| `nm-status` | Check current network status (Control D vs Windscribe) |
| `nm-browse` | Switch to Control D browsing mode (balanced privacy) |
| `nm-privacy` | Switch to Control D privacy mode (maximum security) |
| `nm-gaming` | Switch to Control D gaming mode (minimal filtering) |
| `nm-vpn` | Switch to Windscribe VPN mode (disables Control D) |
| `nm-regress` | Run full regression test (Control D → Windscribe) |
| `nm-cd-status` | Check Control D daemon status |

**Environment Variable:**
- `NM_ROOT` is automatically set to `$HOME/Documents/dev/personal-config`

**Configuration Location:**
- `~/.config/fish/` → `configs/.config/fish/` (symlinked)
- Functions: `~/.config/fish/functions/nm-*.fish`
- Config: `~/.config/fish/config.fish`
