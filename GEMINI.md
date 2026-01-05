# Personal Configuration & System Automation

## 🔍 Project Overview

This repository is a comprehensive **System Automation and Configuration Management** suite for macOS. It goes beyond simple dotfiles to provide a robust infrastructure for:

- **Network Privacy & Performance:** Orchestrating ControlD (DNS) and Windscribe (VPN) with sophisticated switching logic.
- **System Maintenance:** Automated health checks, cleanup, and service optimization.
- **Media Streaming:** A fully automated stack for local and cloud-based media consumption (Infuse, rclone, Alldebrid).
- **Developer Environment:** Consistent configurations for Shell (Fish), SSH (1Password-backed), and Editors (Cursor/VS Code).

## 🏗️ Architecture

The system is built on **idempotent bash scripts** and **launchd agents**, adhering to a "symlink-based" configuration model.

| Directory | Purpose |
| :--- | :--- |
| `configs/` | Source of truth for all dotfiles (`.ssh`, `.config/fish`, etc.). Symlinked to `$HOME`. |
| `scripts/` | Core automation logic (syncing configs, network management). |
| `maintenance/` | A self-contained system for monitoring and cleaning the OS. |
| `controld-system/` | Specialized logic for managing the `ctrld` DNS daemon. |
| `media-streaming/` | Configurations and scripts for the media stack (rclone, WebDAV). |
| `.github/` | CI/CD and repository governance. |

## 🚀 Key Commands

### Bootstrap & Setup
*   **Full Install:** `./setup.sh` (Idempotent; safe to run repeatedly).
*   **Sync Configs:** `./scripts/sync_all_configs.sh` (Updates symlinks).
*   **Verify Configs:** `./scripts/verify_all_configs.sh`.

### Network Management
**DO NOT** manually edit network settings. Use the `network-mode-manager`.

*   **Switch to ControlD (DNS):** `./scripts/network-mode-manager.sh controld [browsing|privacy|gaming]`
*   **Switch to Windscribe (VPN):** `./scripts/network-mode-manager.sh windscribe`
*   **Check Status:** `./scripts/network-mode-manager.sh status`
*   **Run Regression Test:** `make control-d-regression`

### System Maintenance
*   **Health Check:** `./maintenance/bin/run_all_maintenance.sh health`
*   **Quick Cleanup:** `./maintenance/bin/run_all_maintenance.sh quick`
*   **Full Run:** `./maintenance/bin/run_all_maintenance.sh weekly`

## 🛠️ Development Conventions

*   **Scripts:** All scripts are written in `bash` and use `set -euo pipefail` for strict error handling.
*   **Secrets:** **NEVER** commit secrets. Use **1Password CLI (`op`)** injection for runtime secrets or untracked local files.
*   **Symlinks:** We prefer symlinking from this repo to `$HOME` rather than copying. This ensures git tracks the actual state of the system.
*   **Idempotency:** Scripts should check state before acting (e.g., "if link exists, skip").

## ⚠️ Critical Notes

1.  **Network Logic:** The `network-mode-manager.sh` script actively manages IPv6 and system DNS. Changing these manually may break the "leak protection" features.
2.  **Maintenance Locks:** The maintenance system uses lock files (`/tmp/run_all_maintenance.lock`). If a run crashes, you may need to clear this manually (though the script attempts to handle stale locks).
3.  **Media Stack:** Relies on `rclone` and `webdav`. Ensure the `op` CLI is authenticated if you need to re-seed configs.
