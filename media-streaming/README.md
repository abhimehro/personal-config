# 🎬 Ultimate Autonomous Media Streaming Pipeline

> **Status**: ✅ **HYBRID PIPELINE** - Updated 2026-07-30 **Architecture**:
> Hybrid WebDAV + Native macOS FSKit Mount + **Jellyfin (native, Phase 1
> LIVE)**\
> **Performance**: 10GB Bounded VFS Cache (Zero-Memory Bloat)

This setup provides a high-performance, autonomous media pipeline that bridges
cloud storage (Google Drive + OneDrive) to **Jellyfin** (primary on LAN
**8096**) and Infuse (WebDAV backup) without consuming excessive local disk or
memory. Plex remains a legacy/optional path; it is not required for day-to-day
playback once Jellyfin is verified.

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

4. **📡 Serve (Primary Jellyfin + Backup WebDAV; Plex legacy)**
   - **Jellyfin**: Primary media server (native macOS, **8096**). Reads
     `~/CloudMedia/mounted` directly. See `jellyfin/README.md` and
     `scripts/setup-jellyfin-native.sh`. **Default remote path:** Windscribe
     `82.23.253.53:8096` → host `8096` + Published Server URI
     `http://82.23.253.53:8096` (enabled 2026-07-17).
   - **Plex**: Legacy server on **32400** until clients migrate; then optional
     retirement.
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
     `~/CloudMedia/mounted/` via macOS's native kernel-free FSKit API (fuse-t
     backend). This completely bypasses the legacy NFS loopback protocol,
     avoiding hangs and local loopback server dependencies. Jellyfin (and
     legacy Plex) scan this local path directly.
   - **Boot race safeguard**: Before mounting, `wait_for_fskit` polls for the
     fuse-t process (`/Applications/fuse-t.app/Contents/MacOS/fuse-t`) for up
     to 60s. launchd often starts this agent before FSKit is ready; without the
     gate you get a transient "fuse-t cannot start" error that KeepAlive later
     recovers from. The gate removes that noisy first failure.
   - **Note on System Settings**: The per-app File System Extensions toggle for
     fuse-t can appear OFF on macOS betas even when the group-level toggle is
     ON and the FSKit extension is active. Trust `mount | grep mounted` and a
     live fuse-t process over the cosmetic app toggle.

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

| Shortcut          | Description                                                                 |
| :---------------- | :-------------------------------------------------------------------------- |
| `media-status`    | Check core media agents (server, mount, renamer) + optional Jellyfin        |
| `media-logs`      | Stream logs for server and mount                                            |
| `media-restart`   | Full restart of the media infrastructure (server, mount, renamer)           |
| `gaming-mode`     | Toggle / suspend / restore the full media stack for GeForce NOW sessions    |
| `gaming-mode on`  | Unload media LaunchAgents (`bootout`) so KeepAlive cannot respawn them      |
| `gaming-mode off` | Reload agents via `bootstrap` + `kickstart` (reverse start order)           |
| `gaming-mode status` | Per-agent loaded / running / suspended state                             |
| `gaming-mode net …`  | Pass-through to `nm-gaming` (ControlD / network gaming profile)          |
| `list-uploads`    | Show files pending approval                                                 |
| `approve-uploads` | Process and upload pending files                                            |

**Gaming mode details**

- Script: `media-streaming/scripts/gaming-mode.sh`
- Fish wrapper: `configs/.config/fish/functions/gaming-mode.fish`
- Agents unloaded when ON: `com.speedybee.jellyfin`, `com.speedybee.media.renamer`,
  `com.speedybee.media.server`, `com.speedybee.media.mount`,
  `com.speedybee.media.mount-watchdog`
- Why `bootout` / `bootstrap` (not stop/start): these plists use `KeepAlive`, so
  a plain stop or kill immediately respawns the job. `bootout` removes the job
  from the domain; restore re-registers the plist then force-starts it.
- After `gaming-mode off`, give the mount ~10s for the FSKit gate, then run
  `media-status`.
- Network profile is **not** auto-flipped; run `nm-gaming` (or
  `gaming-mode net …`) when you also want ControlD on the gaming profile.

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
- **fuse-t / FSKit at login**: If you still see a one-shot "fuse-t cannot start"
  before the mount comes up, confirm fuse-t is installed at
  `/Applications/fuse-t.app`, that File System Extensions are allowed at the
  *group* level in System Settings, and that `mount-media.sh` still contains
  `wait_for_fskit`. Increase the 60s bound only if cold boot is slower than that
  on this machine. KeepAlive will still retry if the gate times out.
- **Gaming mode stuck down**: `gaming-mode status` then `gaming-mode off`. If an
  individual plist is missing under `~/Library/LaunchAgents/`, run
  `sync-launchagents` first.

## 🔐 **Security Note**

- **WebDAV** is password-protected via 1Password (Item: `MediaServer`).
- **Password rotation**: `./scripts/rotate-media-webdav.sh` (see
  `docs/CREDENTIAL_ROTATION.md`).
- **Port Forwarding**: Use stable TCP mappings via Windscribe:
  - **Jellyfin** (default remote): External **8096** -> internal **8096** at
    `http://82.23.253.53:8096` (Published Server URI set in Dashboard →
    Networking).
  - **Plex** (legacy): External **32400** -> internal **32400** — remove when
    unused.
  - **WebDAV backup**: External **8088** -> internal **8080**. Do not forward
    dynamic fallback ports (`8081-8083`) for remote access. If Windscribe
    assigns a different external port, keep the internal port fixed at **8080**
    and update Infuse/client settings to the assigned external port.

---

_"Zero clicks, zero maintenance, ultimate streaming."_ 🎬✨
