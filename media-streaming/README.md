# 🎬 Ultimate Autonomous Media Streaming Pipeline

> Note: Current media auth is 1Password-first. The media-server credentials file is optional fallback only and is not required for normal runtime operation.

**Status**: ✅ **FULLY AUTOMATED** - Updated January 2026
**Total Storage**: ~3TB Cloud Union (Google Drive + OneDrive) + Alldebrid Streaming
**Platforms**: macOS (Background processing), iOS, tvOS via Infuse

## 🏗️ **Architecture: The "Zero-Click" Pipeline**

This setup provides a fully autonomous workflow from download to cloud library:

1.  **🚀 Sync (Alldebrid Fetcher)**
    - **Script**: `sync-alldebrid.sh`
    - **Agent**: `com.speedybee.alldebrid.sync` (Hourly)
    - **Action**: Automatically fetches new video links from AllDebrid and places them in `~/CloudMedia/downloads`.

2.  **💿 Process (Conversion)**
    - **Tool**: User-managed (Downie/Permute)
    - **Action**: Permute watches `downloads`, converts them, and outputs to `~/CloudMedia/staging`.

3.  **🏷️ Finalize (Autonomous Renamer & Uploader)**
    - **Script**: `rename-media.sh`
    - **Agent**: `com.speedybee.media.renamer` (Continuous Watcher)
    - **Action**: Detects files in `staging`, renames them via **FileBot** (enforcing hardcoded conventions), and uploads directly to the `media:` Union Remote (Google Drive + OneDrive).

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

## 🗝️ **Optional Fallback Credential File Format**

The media-server startup scripts (`archive/scripts/start-media-server-fast.sh` and `archive/scripts/start-media-server.sh`) write and read credentials from `~/.config/media-server/credentials` using **shell-quoted assignment** syntax:

```
MEDIA_WEBDAV_USER='infuse'
MEDIA_WEBDAV_PASS='generated-secret'
```

The file is sourced directly by bash (`source "$CREDS_FILE"`), so the `KEY='value'` quoting is intentional and correct for that use case.

**Parsing values in tests or other scripts:** Because values are wrapped in single quotes, a plain `cut -d'=' -f2-` yields `'infuse'` rather than `infuse`. Use bash parameter expansion to strip only the surrounding quotes:

```bash
# Recommended: bash parameter expansion (strips only surrounding quotes)
raw=$(grep '^MEDIA_WEBDAV_USER=' credentials | cut -d'=' -f2-)
[[ $raw == \'*\' ]] && value=${raw:1:-1} || value=$raw

# Simpler alternative — tr (removes ALL single quotes; avoid if values may contain them):
raw=$(grep '^MEDIA_WEBDAV_USER=' credentials | cut -d'=' -f2-)
value=$(echo "$raw" | tr -d "'")
```

> **Note:** Generated passwords use `[a-zA-Z0-9]` characters only (see `openssl rand` pipeline in `start-media-server-fast.sh`), so both approaches are safe for auto-generated credentials. The parameter-expansion form is preferred for correctness.

**Scripts that generate this format:**

- `media-streaming/archive/scripts/start-media-server.sh` (delegates to `start-media-server-fast.sh`)
- `media-streaming/archive/scripts/start-media-server-vpn-fix.sh`

**Scripts and tests that consume this format:**

- `media-streaming/archive/scripts/diagnose-infuse-connection.sh`
- `media-streaming/archive/scripts/start-media-server-vpn-fix.sh`
- `media-streaming/archive/scripts/test-infuse-connection.sh`

---

_"Zero clicks, zero maintenance, ultimate streaming."_ 🎬✨
