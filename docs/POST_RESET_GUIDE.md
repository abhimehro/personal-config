# Post-Reset macOS Restoration Guide

A comprehensive guide for restoring your macOS development environment after a system reset using the personal-config repository.

**Last Updated**: December 2025  
**Tested On**: macOS Sequoia 15.x

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Phase 1: Pre-Flight Audit](#phase-1-pre-flight-audit)
3. [Phase 2: Bootstrap Restoration](#phase-2-bootstrap-restoration)
4. [Phase 3: Shell Configuration](#phase-3-shell-configuration)
5. [Phase 4: Service Activation](#phase-4-service-activation)
6. [Phase 5: Backup Verification](#phase-5-backup-verification)
7. [Manual Intervention Checklist](#manual-intervention-checklist)
8. [Git Workflow for Maintenance](#git-workflow-for-maintenance)
9. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before starting the restoration, ensure these tools are installed:

```bash
# 1. Install Homebrew (if not present)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. Install essential tools
brew install fish terminal-notifier git

# 3. Install 1Password CLI
brew install --cask 1password/tap/1password-cli

# 4. Install optional development tools
brew install chruby-fish  # Ruby version manager for Fish
brew install eza bat fd ripgrep  # Modern CLI tools
```

### Verification

```bash
# Verify installations
which brew fish op terminal-notifier
# All should return valid paths
```

---

## Phase 1: Pre-Flight Audit

Before making any changes, audit the current system state.

### Clone or Verify Repository

```bash
cd ~/Documents/dev
# Clone if new system
git clone https://github.com/abhimehro/personal-config.git

# Or pull latest if exists
cd personal-config && git pull origin main
```

### Run Configuration Audit

```bash
# Compare local vs repository configurations
./scripts/compare_shell_configs.sh

# Extract enhancement candidates for porting
./scripts/compare_shell_configs.sh --extract-enhancements
```

**Expected Output:**
- Fish config comparison (symlink status)
- Zsh config comparison (if exists)
- Portable patterns for cross-shell porting

---

## Phase 2: Bootstrap Restoration

The main `setup.sh` script handles most restoration tasks.

### Execute Bootstrap

```bash
cd ~/Documents/dev/personal-config
./setup.sh
```

**This script performs:**
1. **Config Symlinks**: SSH, Fish, Cursor, VS Code
2. **Maintenance System**: 7 LaunchD agents installed
3. **Network Tools**: Control D and Windscribe helpers
4. **rclone Config**: Template seeded for media services
5. **Media Scripts**: WebDAV server and Alldebrid helpers

### Verify Installation

```bash
# Check symlinks
./scripts/verify_all_configs.sh

# Check LaunchD agents
launchctl list | grep maintenance
```

---

## Phase 3: Shell Configuration

### Set Fish as Default Shell

```bash
# Add Fish to allowed shells
grep -q /opt/homebrew/bin/fish /etc/shells || \
  echo /opt/homebrew/bin/fish | sudo tee -a /etc/shells

# Set as default
chsh -s /opt/homebrew/bin/fish

# Install Fisher and plugins
./scripts/bootstrap_fish_plugins.sh
```

### Sync Zsh Configuration (Optional)

If you have a local Zsh configuration to track:

```bash
# Sync local .zshrc to repository (with backup)
./scripts/sync_zsh_config.sh

# Or copy without creating symlink
./scripts/sync_zsh_config.sh --no-symlink

# Extract enhancements only (no file changes)
./scripts/sync_zsh_config.sh --extract-only
```

### Review Enhancement Candidates

After syncing, review portable patterns:

```bash
cat configs/.zshrc.enhancements.md
```

**Common patterns to port:**

| Zsh Pattern | Fish Equivalent |
|-------------|-----------------|
| `export PATH="$PATH:dir"` | `fish_add_path --global --append dir` |
| `export VAR=value` | `set -gx VAR value` |
| `eval "$(tool init bash)"` | `tool init fish \| source` |
| `source file` | `source file` |

### Reload Fish Configuration

```bash
# In Fish shell
source ~/.config/fish/config.fish
# Or
exec fish
```

---

## Phase 4: Service Activation

### LaunchD Agents Status

```bash
# View all maintenance agents
launchctl list | grep maintenance

# Expected output (7 agents):
# com.abhimehrotra.maintenance.brew
# com.abhimehrotra.maintenance.healthcheck
# com.abhimehrotra.maintenance.monthly
# com.abhimehrotra.maintenance.protondrivebackup
# com.abhimehrotra.maintenance.systemcleanup
# com.abhimehrotra.maintenance.weekly
```

### Control D DNS Service

```bash
# Start Control D service
sudo ctrld service start \
  --config ~/.config/controld/ctrld.toml \
  --skip_self_checks

# Verify
sudo ctrld service status
dig @127.0.0.1 example.com +short
```

### Manual Test Runs

```bash
# Test health check
~/Library/Maintenance/bin/health_check.sh

# Test system cleanup (dry-run)
~/Library/Maintenance/bin/quick_cleanup.sh
```

---

## Phase 5: Backup Verification

### ProtonDrive Backup

```bash
# Verify ProtonDrive is mounted
ls ~/Library/CloudStorage/ProtonDrive-*

# Test backup (dry-run)
./scripts/protondrive_backup.sh --dry-run --no-delete

# Run actual backup
./scripts/protondrive_backup.sh --run --no-delete
```

### Check Backup Logs

```bash
# View latest backup log
tail -100 ~/Library/Logs/maintenance/protondrive_backup.out

# View LaunchD agent status
launchctl list | grep protondrivebackup
```

---

## Manual Intervention Checklist

These actions require GUI interaction or sensitive credentials:

### Authentication (Required)

| Step | Action | Status |
|------|--------|--------|
| 1 | Open 1Password, authenticate with biometrics | ☐ |
| 2 | 1Password Settings > Developer > Enable SSH Agent | ☐ |
| 3 | Verify SSH: `ssh -T git@github.com` | ☐ |

### Application Setup (Required)

| Step | Action | Status |
|------|--------|--------|
| 4 | Open ProtonDrive app, sign in | ☐ |
| 5 | Open Windscribe, authenticate | ☐ |
| 6 | Cursor: Cmd+Shift+P > "Shell Command: Install 'cursor'" | ☐ |

### System Permissions (Required)

| Step | Action | Status |
|------|--------|--------|
| 7 | System Settings > Privacy > Full Disk Access | ☐ |
| 8 | Grant access to Terminal.app or Warp | ☐ |

### Credentials Injection (If using rclone)

```bash
# Inject secrets from 1Password to rclone config
op inject \
  -i ~/.config/rclone/rclone.conf.template \
  -o ~/.config/rclone/rclone.conf
```

---

## Git Workflow for Maintenance

### Handling Dependabot PRs

```bash
# Fetch all branches
git fetch origin

# List Dependabot branches
git branch -r | grep dependabot

# Option 1: Merge via GitHub web UI (recommended)
# Option 2: Local merge
git checkout main
git merge origin/dependabot/npm_and_yarn/...
git push origin main
```

### Committing Local Improvements

```bash
cd ~/Documents/dev/personal-config

# Stage changes
git add configs/.config/fish/config.fish
git add configs/.zshrc

# Commit with descriptive message
git commit -m "feat: add [description of enhancement]"

# Push to remote
git push origin main
```

### Branch Management

```bash
# Current branch workflow
# 1. Make changes on feature branch
# 2. Push and create PR on GitHub
# 3. Review and merge via GitHub
# 4. Pull locally: git pull origin main
```

---

## Troubleshooting

### Fish Not Loading Config

```bash
# Verify symlink
ls -la ~/.config/fish
# Should show: fish -> /path/to/personal-config/configs/.config/fish

# Manually source
source ~/.config/fish/config.fish
```

### LaunchD Agent Not Running

```bash
# Check if loaded
launchctl list | grep maintenance

# Reload agent
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.abhimehrotra.maintenance.*.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/

# Check logs
tail -50 ~/Library/Logs/maintenance/*.err
```

### SSH Connection Issues

```bash
# Verify 1Password SSH agent
ssh-add -l

# Test connection
./scripts/ssh/check_connections.sh

# Diagnose VPN issues
./scripts/ssh/diagnose_vpn.sh
```

### ProtonDrive Not Mounted

1. Open ProtonDrive app
2. Sign in if needed
3. Wait for sync to complete
4. Verify: `ls ~/Library/CloudStorage/ProtonDrive-*`

### Control D Not Resolving

```bash
# Check if service is running
sudo lsof -i :53

# Restart service
sudo ctrld service restart

# Test resolution
dig @127.0.0.1 google.com +short
```

---

## Quick Reference Commands

```bash
# Full system bootstrap
./setup.sh

# Verify all configs
./scripts/verify_all_configs.sh

# Compare shell configs
./scripts/compare_shell_configs.sh

# Sync Zsh config
./scripts/sync_zsh_config.sh

# Check maintenance status
launchctl list | grep maintenance

# Run health check
~/Library/Maintenance/bin/health_check.sh

# ProtonDrive backup (dry-run)
./scripts/protondrive_backup.sh --dry-run --no-delete

# Control D status
nm-status  # Fish function
# or
./scripts/network-mode-manager.sh status
```

---

## Files Reference

| File | Purpose |
|------|---------|
| `setup.sh` | Main bootstrap script |
| `scripts/sync_all_configs.sh` | Create config symlinks |
| `scripts/verify_all_configs.sh` | Verify symlinks |
| `scripts/compare_shell_configs.sh` | Audit shell config divergence |
| `scripts/sync_zsh_config.sh` | Track Zsh config in repo |
| `scripts/bootstrap_fish_plugins.sh` | Install Fisher and plugins |
| `maintenance/install.sh` | Install LaunchD agents |
| `scripts/protondrive_backup.sh` | One-way home backup |

---

## Recovery Scenarios

### Complete System Reset

1. Install prerequisites (Homebrew, Fish, 1Password CLI)
2. Clone repository
3. Run `./setup.sh`
4. Complete manual intervention checklist
5. Verify with `./scripts/verify_all_configs.sh`

### Config Corruption

```bash
# Re-sync configs (with backup)
./scripts/sync_all_configs.sh

# Verify
./scripts/verify_all_configs.sh
```

### Lost LaunchD Agents

```bash
# Reinstall maintenance system
./maintenance/install.sh
```

---

**Document Version**: 1.0  
**Created**: December 2025  
**Repository**: [personal-config](https://github.com/abhimehro/personal-config)
