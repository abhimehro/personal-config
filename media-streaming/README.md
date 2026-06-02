# 🎬 Ultimate Autonomous Media Streaming Pipeline

> **Status**: ✅ **FULLY OPTIMIZED** - Updated June 2026
> **Architecture**: Hybrid WebDAV + Native macOS FSKit Mount
> **Performance**: 10GB Bounded VFS Cache (Zero-Memory Bloat)

This setup provides a high-performance, autonomous media pipeline that bridges cloud storage (Google Drive + OneDrive) to Plex and Infuse without consuming excessive local disk or memory.

## 🏗️ **Architecture: The Hybrid Bridge**

1.  **🚀 Sync (Alldebrid Fetcher)**
    - **Script**: `sync-alldebrid.sh`
    - **Agent**: `com.speedybee.alldebrid.sync` (Hourly)
    - **Action**: Fetches new video links from AllDebrid, stages them for approval in `~/CloudMedia/approval_needed`.

2.  **🎞️ Convert (Permute HEVC Transcoder - MANUAL STEP)**
    - **App**: Permute 4
    - **Input**: `~/CloudMedia/permute_input/` (drag files here manually)
    - **Output**: `~/CloudMedia/staging/` (HEVC/H.265)
    - **Action**: **MANUAL**: You must open Permute 4, drag files from permute_input/, set output to staging/, and start conversion. Once complete, files auto-progress to rename/upload.

3.  **🏷️ Finalize (Renamer & Uploader)**
    - **Script**: `rename-media.sh`
    - **Agent**: `com.speedybee.media.renamer` (Watchdog)
    - **Action**: Safely processes HEVC files from `staging` into `processed` once finished, then uses FileBot to rename and handle duplicate conflicts against the live mount, queuing them in `upload_stage`.

3.  **📡 Serve (WebDAV Daemon)**
    - **WebDAV**: `media-server-daemon.sh` serves on port **8080** for **Infuse** (iOS/tvOS).
    - **VFS Cache**: Dedicated 10GB bounded cache folder.

4.  **🔌 Mount (Native macOS FSKit Filesystem)**
    - **Script**: `mount-media.sh`
    - **Agent**: `com.speedybee.media.mount` (KeepAlive Daemon)
    - **Action**: Mounts the remote using `rclone mount` directly to `~/CloudMedia/mounted/` via macOS's native kernel-free FSKit API. This completely bypasses the legacy NFS loopback protocol, avoiding hangs and local loopback server dependencies. Plex scans this local path directly.

## 📁 **Library Structure**

```
~/CloudMedia/
├── approval_needed/   # New downloads waiting for approval
├── permute_input/     # MANUAL: Files awaiting Permute 4 HEVC conversion
├── staging/           # HEVC output from Permute (auto-monitored for completion)
├── processed/         # Finished Permute files ready for FileBot
├── upload_stage/      # Files successfully renamed and queued for upload
└── mounted/           # THE SOURCE OF TRUTH (Direct FSKit Mount)
    ├── Movies/
    └── TV Shows/
```

## 🔧 **Management Commands**

Use these shortcuts in your terminal (Fish shell required):

| Shortcut | Description |
| :--- | :--- |
| `media-status` | Check if all 3 media agents are running (server, mount, renamer) |
| `media-logs` | Stream logs for server and mount |
| `media-restart` | Full restart of the media infrastructure (server, mount, renamer) |
| `list-uploads` | Show files pending approval |
| `approve-uploads` | Process and upload pending files |

## 🛠️ **Troubleshooting & Logs**

- **WebDAV Server**: `tail -f ~/Library/Logs/media-server.log`
- **Mount Status**: `tail -f ~/Library/Logs/media-mount.log`
- **Sync History**: `tail -f ~/Library/Logs/alldebrid-sync.log`

## 🔐 **Security Note**

- **WebDAV** is password-protected via 1Password (Item: `MediaServer`).
- **Password rotation**: `./scripts/rotate-media-webdav.sh` (see `docs/CREDENTIAL_ROTATION.md`).
- **Port Forwarding**: Only forward **8080** (WebDAV) and **32400** (Plex) via Windscribe for remote access.

---

_"Zero clicks, zero maintenance, ultimate streaming."_ 🎬✨
