# 🎬 Ultimate Autonomous Media Streaming Pipeline

**Status**: ✅ **FULLY AUTOMATED** - Updated January 2026
**Total Storage**: ~3TB Cloud Union (Google Drive + OneDrive) + Alldebrid Streaming
**Platforms**: macOS (Background processing), iOS, tvOS via Infuse

## 🏗️ **Architecture: The "Zero-Click" Pipeline**

This setup provides a fully autonomous workflow from download to cloud library:

1.  **🚀 Sync (Alldebrid Fetcher)**
    *   **Script**: `sync-alldebrid.sh`
    *   **Agent**: `com.speedybee.alldebrid.sync` (Hourly)
    *   **Action**: Automatically fetches new video links from AllDebrid and places them in `~/CloudMedia/downloads`.

2.  **💿 Process (Conversion)**
    *   **Tool**: User-managed (Downie/Permute)
    *   **Action**: Permute watches `downloads`, converts them, and outputs to `~/CloudMedia/staging`.

3.  **🏷️ Finalize (Autonomous Renamer & Uploader)**
    *   **Script**: `rename-media.sh`
    *   **Agent**: `com.speedybee.media.renamer` (Continuous Watcher)
    *   **Action**: Detects files in `staging`, renames them via **FileBot** (enforcing hardcoded conventions), and uploads directly to the `media:` Union Remote (Google Drive + OneDrive).

## 📁 **Library Structure (Cloud Union)**

The pipeline automatically processes and uploads to:
```
media/ (Union Remote)
├── Movies/          # {n.colon(' - ')} ({y})
└── TV Shows/        # {n} - {s00e00} - {t}
```

## 🔧 **Core Scripts**

### **Automation Agents**
- `sync-alldebrid.sh` - Fetches from Alldebrid to local download pipeline.
- `rename-media.sh` - Watches staging folder, renames via FileBot, and uploads to Cloud.

### **Management & Setup**
- `setup-media-library.sh` - Full setup of Google Drive, OneDrive, and the unified Union Remote.
- `fix-gdrive.sh` / `setup-gdrive.sh` - Authenticate and repair cloud connections.
- `bulk-rename-cloud.sh` - Maintenance tool for bulk library organization.

## 🎯 **Quick Start Guide**

### **1. Configure Rclone**
Ensure your `alldebrid:` remote is configured via WebDAV using your API Key:
```bash
rclone config update alldebrid user [API_KEY] pass [ANY_PASSWORD]
```

### **2. Start the Pipeline**
The agents should be loaded and managed via `launchctl`:
```bash
# Verify agents are running
launchctl list | grep speedybee
```

### **3. Monitor Logs**
- **Sync Activity**: `tail -f ~/Library/Logs/alldebrid-sync.log`
- **Rename/Upload**: `tail -f ~/Library/Logs/media-renamer.log`

## 🔐 **Security & Maintenance**
- **Credentials**: No API keys are stored in scripts. All auth is handled via `~/.config/rclone/rclone.conf` (git-ignored).
- **Redundancy**: The `media:` remote is a union of Google Drive and OneDrive, ensuring your library survives a single provider outage.
- **Fail-Safe**: Any files that fail identification are automatically moved to `~/CloudMedia/failed` for manual audit.

---
*"Zero clicks, zero maintenance, ultimate streaming."* 🎬✨
