# 🎬 Ultimate Autonomous Media Streaming Pipeline

> **Status**: ✅ **FULLY OPTIMIZED** - Updated May 2026
> **Architecture**: Hybrid WebDAV + NFS + Native macOS Mount
> **Performance**: 10GB Bounded VFS Cache (Zero-Memory Bloat)

This setup provides a high-performance, autonomous media pipeline that bridges cloud storage (Google Drive + OneDrive) to Plex and Infuse without consuming excessive local disk or memory.

## 🏗️ **Architecture: The Hybrid Bridge**

1.  **🚀 Sync (Alldebrid Fetcher)**
    - **Script**: `sync-alldebrid.sh`
    - **Agent**: `com.speedybee.alldebrid.sync` (Hourly)
    - **Action**: Fetches new video links from AllDebrid, stages them for approval in `~/CloudMedia/approval_needed`.

2.  **🏷️ Finalize (Renamer & Uploader)**
    - **Script**: `rename-media.sh`
    - **Agent**: `com.speedybee.media.renamer` (Watchdog)
    - **Action**: Moves approved files from `staging` to the `media:` Union Remote (Google Drive + OneDrive).

3.  **📡 Serve (Dual-Protocol Daemons)**
    - **WebDAV**: `media-server-daemon.sh` serves on port **8080** for **Infuse** (iOS/tvOS).
    - **NFS**: `media-nfs-daemon.sh` serves on port **12049** specifically for **Plex** (macOS).
    - **VFS Cache**: Both use a shared 10GB bounded cache to prevent memory exhaustion.

4.  **🔌 Mount (Native macOS Filesystem)**
    - **Script**: `mount-media.sh`
    - **Agent**: `com.speedybee.media.mount` (Watchdog)
    - **Action**: Mounts the NFS share to `~/CloudMedia/mounted/`. Plex scans this local path directly.

## 📁 **Library Structure**

```
~/CloudMedia/
├── approval_needed/   # New downloads waiting for approval
├── upload_stage/      # Files ready for renaming/upload
└── mounted/           # THE SOURCE OF TRUTH (NFS Mount)
    ├── Movies/
    └── TV Shows/
```

## 🔧 **Management Commands**

Use these shortcuts in your terminal (Fish shell required):

| Shortcut | Description |
| :--- | :--- |
| `media-status` | Check if all 5 agents are running |
| `media-logs` | Stream logs for server, nfs, and mount |
| `media-restart` | Full restart of the media infrastructure |
| `list-uploads` | Show files pending approval |
| `approve-uploads` | Process and upload pending files |

## 🛠️ **Troubleshooting & Logs**

- **NFS Server**: `tail -f ~/Library/Logs/media-nfs-server.log`
- **WebDAV Server**: `tail -f ~/Library/Logs/media-server.log`
- **Mount Status**: `tail -f ~/Library/Logs/media-mount.log`
- **Sync History**: `tail -f ~/Library/Logs/alldebrid-sync.log`

## 🔐 **Security Note**

- **WebDAV** is password-protected via 1Password (Item: `MediaServer`).
- **NFS** is bound to `localhost` and is **not** password protected; do **not** forward port 12049 to the internet.
- **Port Forwarding**: Only forward **8080** (WebDAV) and **32400** (Plex) via Windscribe for remote access.

---

_"Zero clicks, zero maintenance, ultimate streaming."_ 🎬✨
