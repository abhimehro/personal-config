# 🎬 Ultimate Autonomous Media Streaming Pipeline

> **Status**: ✅ **FULLY OPTIMIZED** - Updated June 2026 **Architecture**:
> Hybrid WebDAV + Native macOS FSKit Mount **Performance**: 10GB Bounded VFS
> Cache (Zero-Memory Bloat)

This setup provides a high-performance, autonomous media pipeline that bridges
cloud storage (Google Drive + OneDrive) to Plex and Infuse without consuming
excessive local disk or memory.

## 🏗️ **Architecture: The Hybrid Bridge**

1. **🚀 Sync (Alldebrid Fetcher with Pre-Approval Gate)**
   - **Script**: `sync-alldebrid.sh`
   - **Agent**: `com.speedybee.alldebrid.sync` (Hourly)
   - **Action**: Fetches new video links from AllDebrid, creates candidate
     metadata in `~/CloudMedia/approval_needed/.pending/`. Files are categorized
     by size:
     - **< 2GB**: Auto-approved, moved to `.approved/` for immediate download
     - **2GB - 15GB**: Requires manual approval via `approve-download` script
     - **> 15GB**: Rejected and logged to `.alldebrid_ignore`

2. **🎞️ Convert (Permute HEVC Transcoder - MANUAL STEP)**
   - **App**: Permute 4
   - **Input**: `~/CloudMedia/permute_input/` (drag files here manually)
   - **Output**: `~/CloudMedia/staging/` (HEVC/H.265)
   - **Action**: **MANUAL**: You must open Permute 4, drag files from
     permute_input/, set output to staging/, and start conversion. Once
     complete, files auto-progress to rename/upload.

3. **🏷️ Finalize (Renamer & Uploader)**
   - **Script**: `rename-media.sh`
   - **Agent**: `com.speedybee.media.renamer` (Watchdog)
   - **Action**: Safely processes HEVC files from `staging` into `processed`
     once finished, then uses FileBot to rename and handle duplicate conflicts
     against the live mount, queuing them in `upload_stage`.

4. **📡 Serve (Primary Plex + Backup WebDAV)**
   - **Plex**: Primary media server. Remote access uses TCP **32400** internally
     and externally through Windscribe.
   - **WebDAV**: Backup Infuse-compatible server. `media-server-daemon.sh`
     serves on stable internal TCP port **8080** by default.
   - **Windscribe WebDAV mapping**: External TCP **8088** -> internal TCP
     **8080**. If Windscribe assigns a different external port, keep the
     internal port at **8080** and update the client-side external port only.
   - **VFS Cache**: Dedicated 10GB bounded cache folder.

5. **🔌 Mount (Native macOS FSKit Filesystem)**
   - **Script**: `mount-media.sh`
   - **Agent**: `com.speedybee.media.mount` (KeepAlive Daemon)
   - **Action**: Mounts the remote using `rclone mount` directly to
     `~/CloudMedia/mounted/` via macOS's native kernel-free FSKit API. This
     completely bypasses the legacy NFS loopback protocol, avoiding hangs and
     local loopback server dependencies. Plex scans this local path directly.

## 📁 **Library Structure**

```
~/CloudMedia/
├── approval_needed/          # Pre-download approval system
│   ├── .pending/              # Candidates awaiting your approval
│   ├── .approved/             # Approved for download
│   ├── .downloading/          # Currently downloading
│   └── .alldebrid_ignore      # Rejected files (> 15GB)
├── permute_input/            # MANUAL: Files awaiting Permute 4 HEVC conversion
├── staging/                  # HEVC output from Permute (auto-monitored for completion)
├── processed/                # Finished Permute files ready for FileBot
├── upload_stage/             # Files successfully renamed and queued for upload
└── mounted/                  # THE SOURCE OF TRUTH (Direct FSKit Mount)
    ├── Movies/
    └── TV Shows/
```

## 🔧 **Management Commands**

Use these shortcuts in your terminal (Fish shell required):

| Shortcut          | Description                                                       |
| :---------------- | :---------------------------------------------------------------- |
| `media-status`    | Check if all 3 media agents are running (server, mount, renamer)  |
| `media-logs`      | Stream logs for server and mount                                  |
| `media-restart`   | Full restart of the media infrastructure (server, mount, renamer) |
| `list-uploads`    | Show files pending approval                                       |
| `approve-uploads` | Process and upload pending files                                  |

**Note**: Pre-approval gate active. Use `approve-download --list` to see pending
candidates, `approve-download --status` for counts, or
`approve-download <filename>` to approve specific files.

## 🧹 **Remote Storage Cleanup**

The cleanup system identifies and helps remove problematic files from remote
storage (incomplete uploads, duplicates, files with suspicious names like UUID
hashes).

### Commands

| Command                                      | Description                                                |
| :------------------------------------------- | :--------------------------------------------------------- |
| `audit-remote-uploads [Movies\|TV Shows]`    | Scan remote and generate manifest of problematic files     |
| `cleanup-remote [Movies\|TV Shows]`          | Dry-run: show manifest, ask for confirmation to delete ALL |
| `cleanup-remote --select [Movies\|TV Shows]` | Interactive: select specific files by number to delete     |

### Suspicious File Patterns

Files are flagged as suspicious if they match:

- **UUID/Hash patterns**: Pure hex strings like
  `0a72807b7623e46a762d3bfed395cae7`
- **Small size**: Files under 100MB (excluding `_hd` and `_shd` quality markers)
- **Temp/Partial files**: `.part`, `temp`, `partial` in filename
- **Hidden files**: Starting with `.` (except `.DS_Store`)

### 🛡️ Stale Mount Safeguards

To prevent the stale mount issue that caused false disk usage reporting:

1. **Enhanced mount-media.sh** with multiple safeguards:
   - Validates mount point is empty before mounting
   - Cleans up stale directory entries from previous failed mounts
   - Verifies successful unmount before proceeding
   - Retries operations up to 3 times if files are busy

2. **New check-stale-mounts.sh** script:
   - Monitors for stale fuse mounts
   - Checks common mount points for directory entries without active mounts
   - Can attempt automatic cleanup with `--fix` flag

3. **Watchdog LaunchAgent** (`com.speedybee.media.mount-watchdog.plist`):
   - Runs every hour (3600 seconds)
   - Automatically checks and cleans stale mounts
   - Logs to `~/Library/Logs/stale-mount-watchdog.log`

**Manual Check**:

```bash
# Check for stale mounts
bash ~/dev/personal-config/media-streaming/scripts/check-stale-mounts.sh

# Check and attempt to fix
bash ~/dev/personal-config/media-streaming/scripts/check-stale-mounts.sh --fix
```

**Note**: The mount script now refuses to mount if the mount point is not empty,
preventing directory entry corruption.

### Quality Marker Exclusion

Files containing `_hd -`, `_shd.`, `_shd -`, or `_hd.` are **excluded** from
suspicious detection as these are legitimate quality indicators for media files.

### Workflow

1. **Audit first**: Run `audit-remote-uploads Movies` to see what would be
   flagged
2. **Review**: Check the manifest for false positives
3. **Selective cleanup**: Use `cleanup-remote --select Movies` to pick specific
   files
4. **Confirm**: Type `yes` when prompted to permanently delete selected files

**Safety**: All cleanup operations require explicit user confirmation before any
deletion occurs.

## 🛠️ **Troubleshooting & Logs**

- **WebDAV Server**: `tail -f ~/Library/Logs/media-server.log`
- **Mount Status**: `tail -f ~/Library/Logs/media-mount.log`
- **Sync History**: `tail -f ~/Library/Logs/alldebrid-sync.log`

## 🔐 **Security Note**

- **WebDAV** is password-protected via 1Password (Item: `MediaServer`).
- **Password rotation**: `./scripts/rotate-media-webdav.sh` (see
  `docs/CREDENTIAL_ROTATION.md`).
- **Port Forwarding**: Use stable TCP mappings via Windscribe:
  - **Plex**: External **32400** -> internal **32400**. Plex is the primary
    remote media server.
  - **WebDAV backup**: External **8088** -> internal **8080**. Do not forward
    dynamic fallback ports (`8081-8083`) for remote access. If Windscribe assigns
    a different external port, keep the internal port fixed at **8080** and
    update Infuse/client settings to the assigned external port.

---

_"Zero clicks, zero maintenance, ultimate streaming."_ 🎬✨
