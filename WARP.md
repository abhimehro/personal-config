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
# Switch network modes (recommended - unified interface)
nm-browse        # Control D browsing profile (balanced privacy/speed)
nm-privacy       # Control D privacy profile (maximum filtering)
nm-gaming        # Control D gaming profile (low latency)
nm-vpn           # Windscribe VPN mode (IPv6 disabled, Control D stopped)
nm-status        # Show current network mode status
nm-regress       # Run full regression test (Control D → Windscribe → Control D)

# Legacy commands (direct script invocation)
./scripts/network-mode-manager.sh controld browsing
./scripts/network-mode-manager.sh windscribe
./scripts/network-mode-manager.sh status

# Low-level service commands
sudo ctrld service status
~/bin/ctrld-switch gaming      # Old method - use nm-gaming instead

# View real-time DNS logs
sudo tail -f /var/log/ctrld.log

# Restart service (required after config changes)
sudo ctrld service restart
```

### IPv6 Management (for Windscribe VPN)

```bash
# Disable IPv6 (required for Windscribe compatibility)
sudo ~/Documents/dev/personal-config/scripts/macos/ipv6-manager.sh disable

# Check IPv6 status
~/Documents/dev/personal-config/scripts/macos/ipv6-manager.sh status

# Re-enable IPv6 (if needed)
sudo ~/Documents/dev/personal-config/scripts/macos/ipv6-manager.sh enable
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

#### 1. Network Mode Manager (`scripts/network-mode-manager.sh`, `scripts/network-mode-verify.sh`)
- **Purpose**: Unified interface for switching between Control D DNS mode and Windscribe VPN mode.
- **Operation**:
  - **Control D Mode**: Enables Control D, configures system DNS to `127.0.0.1`, enables IPv6.
  - **Windscribe Mode**: Stops Control D, resets DNS to DHCP, disables IPv6 (prevents leaks).
  - **Profiles**: All three profiles (privacy, browsing, gaming) use DoH3 protocol.
- **Key Files**:
  - `scripts/network-mode-manager.sh` - Main orchestrator for mode switching.
  - `scripts/network-mode-verify.sh` - Tight verification for each mode (DNS, service, IPv6 state).
  - `scripts/network-mode-regression.sh` - Full end-to-end test suite.
  - `controld-system/scripts/controld-manager` - Profile management and DNS configuration.

#### 2. VPN + DNS Integration (`windscribe-controld/`, `controld-system/`)
- **Components**: Windscribe VPN (encryption) + Control D `ctrld` daemon (DNS filtering).
- **Configuration**: Profile configs stored under `/etc/controld/profiles/` (managed by controld-manager).
- **Features**:
  - **Separation Strategy**: Control D and Windscribe are now mutually exclusive modes, not concurrent.
  - **Fail-Operational**: `ctrld` configured with `--skip_self_checks` to avoid boot-time firewall race conditions.
  - **DoH3 Protocol**: All profiles default to DoH3 (QUIC) for security and performance.
  - **IPv6 Management**: Automatic IPv6 enable/disable based on active mode.

#### 3. Media Streaming System (`media-streaming/`)
- **Purpose**: Serves media to Infuse on iOS/tvOS/macOS.
- **Components**:
  - **rclone**: Mounts Google Drive and OneDrive.
  - **Union Remote**: Merges cloud drives into a single `media:` remote.
  - **WebDAV Server**: Serves content on port `8088` (local only).
  - **Alldebrid**: Integrated for direct stream caching.
- **Key Files**: `start-media-server.sh`, `setup-media-library.sh`.

#### 4. Service Optimization (`maintenance/`, root docs)
- **Purpose**: Reduces system overhead by disabling unused Apple services.
- **Mechanism**:
  - **Disabling**: `launchctl disable` for ~14 services (e.g., `ReportCrash`, `chronod`).
  - **Monitoring**: `service_monitor.sh` runs daily to kill respawned widgets and enforce state.
  - **Docs**: `macos-disabled-services.md`, `SERVICE_OPTIMIZATION_SUMMARY.md`.

#### 5. Automated Maintenance (`maintenance/`)
- **Architecture**: Modular scripts invoked by `launchd` agents.
- **Logging**: Centralized in `~/Library/Logs/maintenance/`.
- **Notification**: Uses `terminal-notifier` for interactive alerts.
- **Core Scripts**: `health_check.sh`, `quick_cleanup.sh`, `brew_maintenance.sh`.

#### 6. AdGuard Utilities (`adguard/`)
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
