# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Repository Purpose

This is a personal system configuration repository for a macOS environment. It contains:
- **VPN + DNS Integration**: Windscribe VPN with Control D privacy filtering (primary system)
- **SSH Configuration**: 1Password-managed SSH with dynamic network support for Cursor IDE
- **Automated Maintenance**: Scheduled system health checks, cleanup, and package management
- **Shell Configurations**: Fish shell configs with bash/zsh backups

**Key Principle**: All configurations are version-controlled for reproducibility and backup. This repo serves as the single source of truth for system configs.

## Common Development Commands

### Testing & Verification

```bash
# Test SSH configuration
./tests/test_ssh_config.sh

# Test Fish shell config syntax
./tests/test_config_fish.sh

# Verify complete VPN + DNS setup
bash windscribe-controld/windscribe-controld-setup.sh

# Validate all configuration files
./scripts/validate-configs.sh
```

### SSH Configuration Management

```bash
# Install SSH configuration (creates symlinks to this repo)
./scripts/install_ssh_config.sh

# Verify SSH setup
./scripts/verify_ssh_config.sh

# Sync SSH config if it drifts from repo
./scripts/sync_ssh_config.sh

# Test connection methods
ssh cursor-mdns    # Primary (VPN-aware via mDNS)
ssh cursor-local   # Local network only
ssh cursor-auto    # Auto-detection fallback
```

### VPN + DNS System

```bash
# Switch Control D profiles
sudo controld-manager switch privacy doh    # Enhanced privacy filtering
sudo controld-manager switch gaming doh     # Gaming optimization with minimal filtering
sudo controld-manager status                # Check current profile

# Test DNS filtering
dig doubleclick.net +short                  # Should return 0.0.0.0 (blocked)
dig google.com +short                       # Should resolve normally

# Verify Windscribe + Control D integration
bash windscribe-controld/windscribe-controld-setup.sh
```

### Maintenance System

```bash
# Run health check (includes disk, memory, system load, network, battery)
~/Documents/dev/personal-config/maintenance/bin/health_check.sh

# Run quick system cleanup
~/Documents/dev/personal-config/maintenance/bin/quick_cleanup.sh

# View latest health report
ls ~/Library/Logs/maintenance/health_report-*.txt | tail -1 | xargs cat

# Check automation status
launchctl list | grep maintenance

# View logs interactively
~/Documents/dev/personal-config/maintenance/bin/view_logs.sh summary
~/Documents/dev/personal-config/maintenance/bin/view_logs.sh health_check
```

### Git Workflow

```bash
# Standard workflow - always work on main branch
git add <files>
git commit -m "Brief description"
git push origin main

# Before pushing, check for sensitive data
git grep -I -nE '(oauth|client_secret|api[_-]?key|token|bearer\s+[A-Za-z0-9._-]+|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})' || true
```

## Architecture & Structure

### System Integration Pattern

This repository follows a **symlink-based configuration management** pattern:
- **Source of Truth**: All configs live in `~/Documents/dev/personal-config/`
- **Active Configs**: Symlinked from home directory to this repo
- **Benefits**: Version control + atomic updates + easy rollback

Example: `~/.ssh/config` → `~/Documents/dev/personal-config/configs/ssh/config`

### Key Systems

#### 1. VPN + DNS Integration (Primary Network Stack)
- **Location**: `windscribe-controld/`
- **Purpose**: Dual protection with VPN encryption + DNS privacy filtering
- **Architecture**: 
  - Windscribe VPN provides encrypted tunnel
  - Control D DNS runs inside VPN tunnel for privacy filtering
  - Two profiles: "privacy" (aggressive filtering) and "gaming" (minimal latency)
  - Real-time DNS logging with DOH (DNS-over-HTTPS)
- **Critical Files**:
  - `windscribe-controld-setup.sh`: Automated verification script
  - `setup-guide.md`: Complete technical documentation
  - `ctrld.toml.backup`: Configuration backup

#### 2. SSH Configuration (Development Workflow)
- **Location**: `configs/ssh/`, `scripts/ssh/`
- **Purpose**: Secure SSH with 1Password key management for remote development
- **Architecture**:
  - 1Password SSH agent manages keys (no local private keys stored)
  - Dynamic network detection: tries mDNS (.local), then IP fallbacks
  - Connection multiplexing for performance
  - VPN-aware: adapts connection method based on network state
- **Critical Files**:
  - `configs/ssh/config`: Main SSH configuration
  - `configs/ssh/agent.toml`: 1Password SSH agent settings
  - `scripts/install_ssh_config.sh`: Setup script that creates symlinks

#### 3. Automated Maintenance System
- **Location**: `maintenance/`
- **Purpose**: Scheduled system health monitoring, cleanup, and package updates
- **Architecture**:
  - Launch agents run scheduled tasks (daily/weekly/monthly)
  - Uses `terminal-notifier` for interactive notifications with click-to-view logs
  - Centralized logging in `~/Library/Logs/maintenance/`
  - Modular scripts in `maintenance/bin/` with shared library in `maintenance/lib/`
- **Key Scripts**:
  - `health_check.sh`: System health monitoring (disk, memory, services, network, battery)
  - `quick_cleanup.sh`: Cache and temp file cleanup
  - `brew_maintenance.sh`: Homebrew packages + cask updates with service management
  - `weekly_maintenance.sh`: Orchestrator for comprehensive weekly tasks
  - `monthly_maintenance.sh`: Deep system maintenance

### Configuration Hierarchy

1. **Primary**: Active daily-use systems (VPN+DNS, SSH, Maintenance)
2. **Secondary**: Fallback/diagnostic tools (legacy DNS scripts, diagnostics)
3. **Archive**: Historical reference (old AdGuard configs, migration docs)

### Security Model

- **SSH Keys**: Managed by 1Password SSH agent, never stored locally
- **Secrets**: Environment variables or 1Password references only
- **Git Hygiene**: Pre-push secret scanning required (see Git workflow above)
- **DNS Leak Protection**: Windscribe firewall + Control D verification
- **Zero-Trust**: Assume all inputs malicious, validate everything

## Important Patterns

### Script Execution Context
Scripts in this repo run from **their original location** in `~/Documents/dev/personal-config/`, not from symlinked locations. This ensures relative paths work correctly.

### Launch Agent Pattern
Maintenance scripts are invoked by macOS launch agents:
- Defined in `~/Library/LaunchAgents/com.abhimehrotra.maintenance.*.plist`
- Run as user (not root) for safety
- Standard output/error logged to `~/Library/Logs/maintenance/`
- Use `launchctl` to manage (load/unload/kickstart)

### Notification Pattern
Interactive notifications via `terminal-notifier`:
- Click notification → opens relevant log in TextEdit
- Error summaries consolidate issues across all tasks
- Requires `terminal-notifier` installed via Homebrew

### Testing Philosophy
Every major system has a test script in `tests/`:
- Exit code 0 = success, non-zero = failure
- Use verbose output with emojis (✅/❌) for human readability
- Prefer `set -e` for fail-fast behavior

## Dependencies

### Required
- **Homebrew**: Package manager for macOS (`/opt/homebrew/bin/brew`)
- **1Password**: SSH agent for key management
- **Windscribe**: VPN client
- **Control D**: DNS privacy filtering (`controld` daemon)
- **terminal-notifier**: Interactive notifications for maintenance system

### Development Tools
- **Fish Shell**: Primary shell (with bash/zsh as backups)
- **Git**: Version control (`nano` as default editor)
- **Python 3**: Located at `/opt/homebrew/bin/python3`
- **Node.js & npm**: Located at `/opt/homebrew/bin/`

### Not Installed
- `cargo` (Rust toolchain)
- `docker-compose` (Docker not used)

## Working with This Repository

### Making Changes to Configs

1. **Edit in repo**: Always edit files in `~/Documents/dev/personal-config/configs/`
2. **Sync if needed**: For SSH, run `./scripts/sync_ssh_config.sh` if changes don't take effect
3. **Test**: Run relevant test script from `tests/`
4. **Commit**: Follow Git workflow above
5. **Push**: After verifying no secrets exposed

### Adding New Configurations

When adding new system configurations:
1. Create directory in `configs/` or new top-level directory if it's a system
2. Write installation script in `scripts/` that creates symlinks
3. Write test script in `tests/` to validate setup
4. Document in README.md with Quick Start commands
5. Add to this WARP.md in the Architecture section

### Modifying Maintenance Scripts

Maintenance scripts follow a pattern:
1. Source `maintenance/lib/common.sh` for shared functions
2. Load config from `maintenance/conf/config.env`
3. Log to `~/Library/Logs/maintenance/`
4. Send notification with terminal-notifier on completion
5. Test manually before updating launch agent schedule

## Documentation Strategy

- **README.md**: User-facing, focused on "how to use"
- **WARP.md** (this file): Developer-facing, focused on "how it works"
- **Component READMEs**: Deep dives on specific systems (e.g., `maintenance/README.md`)
- **Setup Guides**: Step-by-step technical setup (e.g., `windscribe-controld/setup-guide.md`)
- **Inline Comments**: Explain "why" not "what" in scripts

Keep documentation consistent with Cursor rules:
- Verify all docs reflect latest changes
- Check for broken links and outdated references
- Maintain clear, concise writing style

## Troubleshooting Common Issues

### SSH Connection Failures
1. Run `./tests/test_ssh_config.sh` to diagnose
2. Check 1Password SSH agent is enabled and unlocked
3. Verify network connectivity: `./scripts/ssh/diagnose_vpn.sh`
4. Test each connection method individually

### DNS Not Filtering
1. Verify Windscribe is connected
2. Run `bash windscribe-controld/windscribe-controld-setup.sh`
3. Check if system is using Control D: `scutil --dns | grep 100.79.16.10`
4. Ensure Windscribe is set to "Custom DNS: 100.79.16.10"

### Maintenance Scripts Not Running
1. Check launch agents: `launchctl list | grep maintenance`
2. Verify script permissions: `chmod +x maintenance/bin/*.sh`
3. Check logs: `ls ~/Library/Logs/maintenance/ | tail -10`
4. Reload agent: `launchctl kickstart -k gui/$(id -u)/com.abhimehrotra.maintenance.<name>`

### Fish Shell Issues
1. Test config syntax: `./tests/test_config_fish.sh`
2. Fall back to bash/zsh if needed (configs exist as backups)
3. Previous issues with Fish + Warp have been resolved, but backups remain

## Security Guidelines

Following user's security-first development philosophy:

### Code Review Mindset
- Treat every input as malicious until validated
- Explain security measures in terms of real-world attacks they prevent
- Flag code that could become a vulnerability if misused
- When in doubt, choose the more secure option

### Secrets Management
- **Never** commit secrets, API keys, or tokens to Git
- Use environment variables or 1Password references
- Run secret scan before every push (see Git workflow)
- If secret is exposed, rotate immediately and rewrite Git history

### Script Safety
- Use `set -e` to fail fast on errors
- Quote all variables to prevent injection
- Validate user input before use
- Run potentially destructive operations with confirmation
- Test in non-destructive mode first when possible

## Version History

- **v4.0** (October 2025): Enhanced VPN + DNS Integration with Windscribe + Control D
- **v3.0** (September 2025): Dynamic DNS Management System
- **v2.0** (August 2025): SSH Configuration with 1Password
- **v1.0** (April 2025): Initial repository structure
