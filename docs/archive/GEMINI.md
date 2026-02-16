# Personal System Configuration

This repository hosts the personal system configuration, dotfiles, and automation scripts for a macOS environment. It is designed to be a "source of truth" for the user's development, gaming, and media setups.

## 📂 Project Overview

* **Type:** System Configuration / Dotfiles / Automation
* **OS:** macOS (Darwin)
* **Key Technologies:** Bash, Fish Shell, Homebrew, 1Password (`op`), Control D, Windscribe, Rclone.
* **Management Strategy:** Symlink-based (Repo -> Home Directory).

## 🏗️ Core Structure

* **`configs/`**: The core dotfiles.
  * `ssh/`: SSH config and agent settings (1Password integrated).
  * `.config/fish/`: Fish shell configuration and functions.
  * `.vscode/`, `.cursor/`: Editor settings.
* **`scripts/`**: Utility and automation scripts.
  * `sync_all_configs.sh`: Creates symlinks from repo to home.
  * `network-mode-manager.sh`: Manages DNS/VPN states.
* **`maintenance/`**: Automated system health and cleanup system.
* **`controld-system/`**: Control D DNS configuration and profiles.
* **`media-streaming/`**: Media server setup (Rclone, WebDAV, Alldebrid).

## 🚀 Key Commands

### Setup & Configuration

| Command | Description |
| :--- | :--- |
| `./setup.sh` | **Bootstrap**: Full idempotent setup (links dotfiles, installs agents). |
| `./scripts/sync_all_configs.sh` | **Sync**: Updates symlinks from repo to home directory. |
| `./scripts/verify_all_configs.sh` | **Verify**: Checks validity of all config symlinks. |

### Network & DNS (Fish Functions)

*Requires `exec fish` after sync.*

| Command | Description |
| :--- | :--- |
| `nm-status` | Check current network status (Control D vs Windscribe). |
| `nm-browse` | Switch to **Control D Browsing** mode (balanced). |
| `nm-privacy` | Switch to **Control D Privacy** mode (max security). |
| `nm-gaming` | Switch to **Control D Gaming** mode (performance). |
| `nm-vpn` | Switch to **Standalone Windscribe VPN** mode. |
| `nm-vpn <profile>` | Switch to **Combined Mode** (VPN + Control D Profile). |
| `nmvp`, `nmvg`, `nmvb` | Shortcuts for Combined Mode (Privacy, Gaming, Browsing). |

### Maintenance

| Command | Description |
| :--- | :--- |
| `~/Library/Maintenance/bin/health_check.sh` | Run an immediate system health check. |
| `~/Library/Maintenance/bin/quick_cleanup.sh` | Perform a quick system cleanup. |
| `launchctl list \| grep maintenance` | Check status of maintenance background agents. |

## 🛠️ Development Conventions

* **Source of Truth:** All edits should be made in this repository, not in the home directory directly (files are symlinked).
* **Secrets:** Never commit secrets. Use **1Password** (`op` CLI) for sensitive data handling (SSH keys, API tokens).
* **Scripting:**
  * Automation scripts are generally `bash`.
  * Interactive shell functions are `fish`.
* **Documentation:** Extensive Markdown documentation exists in subdirectories (e.g., `maintenance/README.md`, `controld-system/README.md`). Always update docs when changing functionality.

## ⚠️ Critical Notes

* **SSH:** Config managed via `configs/ssh/config`. Keys are loaded via 1Password Agent.
* **Network:** The `network-mode-manager.sh` is the underlying engine for DNS/VPN switching.
* **Backups:** ProtonDrive is used for one-way home backups (scripted in `maintenance`).
