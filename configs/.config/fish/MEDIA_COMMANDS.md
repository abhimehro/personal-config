# Media Pipeline Commands Reference

This document lists all available fish shell commands for the media pipeline.

## Quick Reference Table

| Command              | Abbreviation | Script                          | Description                                      |
| -------------------- | ------------ | ------------------------------- | ------------------------------------------------ |
| `alldebrid-sync`     |              | sync-alldebrid.sh               | Sync files from Alldebrid to CloudMedia          |
| `alldebrid-sync-dry` |              | sync-alldebrid.sh --dry-run     | Preview what would be synced                     |
| `ad-approve`         |              | approve-download                | Approve a pending Alldebrid download candidate   |
| `ad-list`            |              | approve-download --list         | List pending download candidates                 |
| `ad-reject`          |              | approve-download --reject       | **Reject** a pending candidate (permanent)        |
| `ad-rejected`        |              | approve-download --list-rejected| List all rejected files                          |
| `ad-unreject`        |              | approve-download --unreject     | **Unreject** a file (allows re-selection)        |
| `ad-status`          |              | approve-download --status       | Show approval status (pending/approved/rejected) |
| `ad-fetch`           |              | approve-download --fetch        | Approve all pending and trigger sync             |
| `mmount`             |              | mount-media.sh                  | Mount media drives                               |
| `mserver`            |              | media-server-daemon.sh          | Start/stop media server                          |
| `finalize`           |              | final-media-server.sh           | Finalize media processing                        |
| `rename-media`       |              | rename-media.sh                 | Rename media files using FileBot                 |
| `rm-approve`         |              | rename-media.sh --approve-ready | Approve files ready for upload                   |
| `rm-pending`         |              | rename-media.sh --list-pending  | List pending rename proposals                    |
| `rotate-webdav`      |              | rotate-media-webdav.sh          | Rotate WebDAV credentials                        |
| `setup-gdrive`       |              | setup-gdrive.sh                 | Setup Google Drive                               |
| `setup-media`        |              | setup-media-library.sh          | Setup media library                              |
| `check-stale`        |              | check-stale-mounts.sh           | Check for stale media mounts                     |
| `sync-media-agents`  |              | sync-launchagents.sh            | Sync LaunchAgents for media services             |
| `bulk-rename`        |              | bulk-rename-cloud.sh            | Bulk rename files in cloud storage               |
| `approve-downloads`  |              | approve-downloads.sh            | **LEGACY**: Move files to permute_input          |
| `list-downloads`     |              | approve-downloads.sh --list     | **LEGACY**: List files for permute               |

---

## Rejection Workflow (Permanent Denial)

The system provides **permanent rejection** to ensure denied files are never re-queued.

### How Rejection Works

1. **Reject a pending candidate**: The filename is added to `~/CloudMedia/approval_needed/.alldebrid_ignore`
2. **Reject by filename**: Any file (even not yet queued) can be added to the ignore list
3. **Filtering**: The `sync-alldebrid.sh` script filters out all files in the ignore list before selection
4. **Permanent**: Once in the ignore list, a file will **NEVER** be selected again, even if it appears in Alldebrid

### Rejection Commands

```fish
# Reject a pending candidate (by candidate ID or filename)
ad-reject "Movie.Name.2024.mkv"

# List all rejected files
ad-rejected

# Unreject a file (allows it to be selected again)
ad-unreject "Movie.Name.2024.mkv"

# Reject multiple files at once
ad-reject "Movie1.mkv"
ad-reject "Movie2.mkv"
ad-reject "Movie3.mkv"
```

### Answers to Your Specific Questions

**Q: Are there commands/aliases for denying or rejecting downloads?**
A: **Yes!** `ad-reject`, `ad-rejected`, and `ad-unreject`

**Q: What happens when I deny a download candidate?**
A: The filename is added to `.alldebrid_ignore`, the candidate file is removed from pending, and you get a notification.

**Q: Does the workflow advance to the next item awaiting approval?**
A: **Yes!** After rejecting, the script removes the candidate and the next sync will select a new candidate (from the remaining non-ignored files).

**Q: Is the denied item recorded somewhere so it won't be presented for approval again?**
A: **Yes!** All rejected files are stored in `~/CloudMedia/approval_needed/.alldebrid_ignore`. The `sync-alldebrid.sh` script filters these out before candidate selection (in the `IGNORE_FILE` filtering section).

**Q: How do we prevent re-pulling, re-queuing, or reprocessing of denied videos?**
A: The rejection is **permanent by design**:
   - The python selector script (`select-best-alldebrid-candidate.py`) checks the ignore list before scoring candidates
   - Any file matching the ignore list (by filename OR identity) is skipped during candidate selection
   - Files that are too large (>15GB) are automatically added to the ignore list
   - The ignore list persists across reboots and script runs

### Important Notes

- **Rejection is permanent** until you explicitly `ad-unreject` the file
- **Identity-based matching**: The system also matches by "identity" (e.g., `euphoria-s02e05`) to catch files with slightly different names
- **Auto-rejection**: Files over 15GB are automatically rejected to prevent system stress
- **View rejected files**: Use `ad-rejected` or `cat ~/CloudMedia/approval_needed/.alldebrid_ignore`
- **Unreject to retry**: If you change your mind, use `ad-unreject` to remove from the ignore list

---

## Workflow: Alldebrid Download Pipeline (NEW System)

This is the **primary** download pipeline that replaces the old manual process.

### 1. Sync from Alldebrid

```fish
# Check what would be downloaded (safe preview)
alldebrid-sync-dry

# Actually sync and download
alldebrid-sync
```

The sync script will:

- Check VPN/Windscribe is connected
- Verify disk space (>20GB free)
- Scan Alldebrid for video files
- Select the best candidate based on quality scores
- For files under 2GB: auto-approve and download
- For larger files: create a pending candidate and wait for approval

### 2. Approve Downloads

If files require approval (larger than 2GB), you'll be notified. Use these commands:

```fish
# List all pending candidates
ad-list

# Show approval status (counts of pending/approved/rejected)
ad-status

# Approve a specific file
ad-approve "filename.mkv"

# Approve all pending and trigger immediate sync
ad-fetch

# Or approve all without triggering sync
ad-approve --fetch
```

### 3. Pipeline Gates

The system has these safety limits:

- **Max pending candidates**: 5 (prevents backlog)
- **Max file size**: 15GB (prevents system stress)
- **Auto-approve threshold**: 2GB (small files bypass approval)
- **Max downloading**: 1 file at a time
- **Max approved waiting**: 1 file
- **Min disk space**: 20GB free

If any limit is reached, the pipeline will pause with a clear message.

---

## Workflow: Media Processing Pipeline

After files are downloaded to `~/CloudMedia/approval_needed/`, they need to be processed.

### Option A: Automatic (Recommended)

Files in `approval_needed/` are automatically moved to staging by the rename-media watch system.

### Option B: Manual Processing

```fish
# Check what's waiting
rm-pending

# Approve files ready for upload
rm-approve

# Or process all files in staging
rename-media

# Process with auto-upload
rename-media --auto-upload

# Process in watch mode (monitors for new files)
rename-media --watch
```

### Server Management

```fish
# Start the media server
mserver

# Mount media drives
mmount

# Finalize processing and upload
finalize

# Rotate WebDAV credentials
rotate-webdav
```

---

## Setup Commands

```fish
# Setup Google Drive remote
setup-gdrive

# Setup media library structure
setup-media

# Sync LaunchAgents (after config changes)
sync-media-agents

# Check for stale media mounts
check-stale
```

---

## Utility Functions

These are defined as fish functions (not aliases):

```fish
# Check status of all media agents
media-status

# Restart all media agents
media-restart

# Stream logs for media server and mount
media-logs
```

---

## Legacy Commands (Deprecated)

These are from the old manual workflow and are kept for backwards compatibility:

```fish
# LEGACY: Move files from approval_needed/ to permute_input/
# This was for the old manual Permute 4 HEVC conversion workflow
approve-downloads

# LEGACY: List files waiting for permute
list-downloads
```

**Note**: The NEW system (`approve-download`, `alldebrid-sync`) handles pre-download approval and automatic processing. The legacy commands are only needed if you're still using the manual Permute 4 workflow.

---

## Common Scenarios

### "I want to see what's in Alldebrid without downloading"

```fish
alldebrid-sync-dry
```

### "I want to download everything under 2GB automatically"

```fish
alldebrid-sync
```

(The script auto-approves files under 2GB)

### "I have files waiting for approval, what are they?"

```fish
ad-list
```

### "I want to approve a file for download"

```fish
ad-approve "Movie.Name.2024.mkv"
```

### "I want to approve all pending files"

```fish
ad-fetch
```

### "I want to check the status of the pipeline"

```fish
ad-status
```

### "I want to see what's being processed"

```fish
rm-pending
```

### "I want to restart all media services"

```fish
media-restart
```

---

## Troubleshooting

### "The pipeline seems stuck"

```fish
# Check for pending candidates
ad-list

# Check pipeline limits
ad-status

# Check agent status
media-status
```

### "I'm not getting notifications"

Notifications use `terminal-notifier` or `osascript`. Check that one of these is installed:

```fish
which terminal-notifier osascript
```

### "Files aren't downloading"

Check the log:

```fish
tail -50 ~/Library/Logs/alldebrid-sync.log
```

### "I hit a gate/limit"

The script will log which limit was hit. Use `ad-status` to see current counts.

---

## File Locations

| Location                                  | Purpose                                                |
| ----------------------------------------- | ------------------------------------------------------ |
| `~/CloudMedia/approval_needed/`           | Files downloaded from Alldebrid waiting for processing |
| `~/CloudMedia/approval_needed/.pending/`  | Pre-download candidates waiting for approval           |
| `~/CloudMedia/approval_needed/.approved/` | Approved candidates ready to download                  |
| `~/CloudMedia/staging/`                   | Files waiting to be renamed                            |
| `~/CloudMedia/processed/`                 | Successfully processed files                           |
| `~/CloudMedia/upload_stage/`              | Files ready for cloud upload                           |
| `~/Library/Logs/alldebrid-sync.log`       | Alldebrid sync log                                     |
| `~/Library/Logs/media-rename.log`         | Media rename log                                       |
