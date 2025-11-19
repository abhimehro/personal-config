# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Repository Purpose

This is a personal system configuration repository for a macOS environment. It acts as the **single source of truth** for:
- **VPN + DNS Integration**: Windscribe VPN combined with Control D (`ctrld`) for privacy and ad-blocking.
- **Media Streaming**: A 3TB+ unified media library (Google Drive + OneDrive + Alldebrid) serving Infuse via WebDAV.
- **Service Optimization**: Automated management of background services and widgets to maximize performance.
- **SSH Configuration**: 1Password-managed SSH with dynamic network support.
- **Automated Maintenance**: Scheduled health checks, cleanup, and package management.
- **Shell Configurations**: Fish shell configs (primary) with bash/zsh backups.

## Common Development Commands

### Testing & Verification

```bash
# Test SSH configuration
./tests/test_ssh_config.sh

# Test Fish shell config syntax
./tests/test_config_fish.sh

# Validate all configuration files
./scripts/validate-configs.sh

# Verify complete VPN + DNS setup
bash windscribe-controld/windscribe-controld-setup.sh

# Run system health check
~/Documents/dev/personal-config/maintenance/bin/health_check.sh
```

### Media Streaming Management

```bash
# Start the unified WebDAV server (Google Drive + OneDrive)
~/Documents/dev/personal-config/media-streaming/scripts/start-media-server.sh

# Restart media services
pkill -f "rclone serve" && ~/Documents/dev/personal-config/media-streaming/scripts/start-media-server.sh

# Fix Google Drive authentication
~/Documents/dev/personal-config/media-streaming/scripts/fix-gdrive.sh

# Check remote status
rclone listremotes
```

### Control D (DNS) Management

```bash
# Check service status
sudo ctrld service status

# Switch profiles (privacy / browsing / gaming)
~/bin/ctrld-switch gaming
~/bin/ctrld-switch browsing
~/bin/ctrld-switch privacy

# View real-time DNS logs
sudo tail -f /var/log/ctrld.log

# Restart service (required after config changes)
sudo ctrld service restart
```

### Service Optimization

```bash
# Run service monitor manually (checks disabled services & widgets)
~/Documents/dev/personal-config/maintenance/bin/service_monitor.sh

# View service monitor logs
tail -f ~/Library/Logs/maintenance/service_monitor.log

# Kill respawning widgets manually
pkill -9 CalendarWidgetExtension
```

### SSH Configuration

```bash
# Install/Symlink SSH configuration
./scripts/install_ssh_config.sh

# Sync SSH config if it drifts
./scripts/sync_ssh_config.sh
```

## Architecture & Structure

### System Integration Pattern
This repository uses a **symlink-based configuration** model.
- **Source**: `~/Documents/dev/personal-config/`
- **Destination**: System locations (e.g., `~/.ssh/`, `~/.config/`)
- **Execution**: Scripts run from the repo path to maintain relative path integrity.

### Key Systems

#### 1. VPN + DNS Stack (`windscribe-controld/`, `controld-system/`)
- **Components**: Windscribe VPN (encryption) + Control D `ctrld` daemon (DNS filtering).
- **Configuration**: `~/.config/controld/ctrld.toml` (symlinked/managed).
- **Features**:
  - **Fail-Operational**: `ctrld` configured with `--skip_self_checks` to avoid boot-time firewall race conditions.
  - **Profiles**: Switchable profiles for Privacy, Browsing, and Gaming.
  - **Integration**: Scripts in `windscribe-controld/` ensure the VPN and DNS play nicely together.
  - **No Interference**: Profile switching avoids modifying system network settings (`networksetup`), preventing "Network Settings Interference" errors in Windscribe.

#### 2. Media Streaming System (`media-streaming/`)
- **Purpose**: Serves media to Infuse on iOS/tvOS/macOS.
- **Components**:
  - **rclone**: Mounts Google Drive and OneDrive.
  - **Union Remote**: Merges cloud drives into a single `media:` remote.
  - **WebDAV Server**: Serves content on port `8088` (local only).
  - **Alldebrid**: Integrated for direct stream caching.
- **Key Files**: `start-media-server.sh`, `setup-media-library.sh`.

#### 3. Service Optimization (`maintenance/`, root docs)
- **Purpose**: Reduces system overhead by disabling unused Apple services.
- **Mechanism**:
  - **Disabling**: `launchctl disable` for ~14 services (e.g., `ReportCrash`, `chronod`).
  - **Monitoring**: `service_monitor.sh` runs daily to kill respawned widgets and enforce state.
  - **Docs**: `macos-disabled-services.md`, `SERVICE_OPTIMIZATION_SUMMARY.md`.

#### 4. Automated Maintenance (`maintenance/`)
- **Architecture**: Modular scripts invoked by `launchd` agents.
- **Logging**: Centralized in `~/Library/Logs/maintenance/`.
- **Notification**: Uses `terminal-notifier` for interactive alerts.
- **Core Scripts**: `health_check.sh`, `quick_cleanup.sh`, `brew_maintenance.sh`.

#### 5. AdGuard Utilities (`adguard/`)
- **Purpose**: Generates and consolidates blocklists/allowlists.
- **Script**: `consolidate_adblock_lists.py` merges tracker lists and Control D bypass rules into format-compliant files for AdGuard/other blockers.

## Important Patterns

### Fail-Operational Design
The Control D service uses `--skip_self_checks` at startup.
- **Why**: macOS firewall blocks `ctrld`'s initial connectivity checks.
- **Trade-off**: We prioritize service availability over pre-start validation. The service starts immediately and establishes connections asynchronously.

### Read-Only Media Server
The WebDAV server runs with `--read-only` flag.
- **Security**: Prevents accidental deletion of cloud assets from client apps (Infuse).
- **Performance**: Uses `--dir-cache-time 30m` to minimize API calls.

### Maintenance "Launch Agent" Pattern
Scripts are not cron jobs; they are **Launch Agents**.
- Run as user (non-root).
- Defined in `~/Library/LaunchAgents/com.abhimehrotra.maintenance.*.plist`.
- Managed via `launchctl`.

## Dependencies

### Required
- **Homebrew**: `/opt/homebrew/bin/brew`
- **1Password**: SSH agent.
- **Windscribe**: VPN client.
- **ctrld**: Control D CLI/Daemon (`brew install ctrld`).
- **rclone**: Cloud storage mounter (`brew install rclone`).
- **terminal-notifier**: Notifications (`brew install terminal-notifier`).

### Development
- **Fish Shell**: Primary shell.
- **Python 3**: `/opt/homebrew/bin/python3` (Used for AdGuard scripts, Alldebrid server).
- **Node.js**: Installed but less used in this repo's context.

## Security Guidelines

- **Media Server**: Bind to local IP/LAN only. Use read-only mode for cloud mounts.
- **Secrets**:
  - Never commit `rclone.conf` or `ctrld.toml` containing tokens.
  - Use `*.backup` files for templates, stripping actual secrets.
  - **Pre-push check**: `git grep` for tokens before pushing.
- **Input Validation**: Assume all script inputs are malicious.
- **SSH**: Private keys live in 1Password, never on disk.

## Version History

- **v4.1** (Oct 2025): Service Optimization & Media Streaming System.
- **v4.0** (Oct 2025): Enhanced VPN + DNS Integration (Windscribe + Control D).
- **v3.0** (Sep 2025): Dynamic DNS Management System.
- **v2.0** (Aug 2025): SSH Configuration with 1Password.
- **v1.0** (Apr 2025): Initial repository structure.
