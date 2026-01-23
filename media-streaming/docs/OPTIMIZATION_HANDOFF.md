# ELIR Handoff: Media Pipeline Optimization

**Date:** 2026-01-23
**Focus:** Backpressure control, Disk Safety, and Automation "Glue"

## 📋 Purpose Statement
This update optimizes the media pipeline by introducing **flow control** and **atomic operations**.
- It prevents storage exhaustion by pausing new downloads while uploads are in progress.
- It fixes the "Permute doesn't see files" issue by using atomic moves (downloading to a temp folder, then "instantly" appearing in the watch folder).
- It removes the manual step between Permute and FileBot by auto-sweeping the `processed` folder.

## 🛡️ Security & Safety Narrative

### Threats & Risks Addressed
| Threat | Protection | Mechanism |
| :--- | :--- | :--- |
| **Disk Exhaustion** | **Space Awareness** | `sync-alldebrid.sh` now checks for <20GB free space before ANY download. |
| **Bandwidth/IO Saturation** | **Locking/Backpressure** | Downloads are PAUSED if an upload is active (detected via `~/.media_upload.lock`). |
| **Partial File Processing** | **Atomic Moves** | Files are downloaded to `.downloading/` hidden folder first, then `mv`'d to `downloads/` only when complete. |

### Failure Modes
| Scenario | Consequence | Mitigation |
| :--- | :--- | :--- |
| **Upload Crash** | Lock file might persist (`.media_upload.lock`) | The lock is just a file; manually delete it if the system gets stuck for >2 hours. (Future: Add stale lock check). |
| **Permute Fails** | Files sit in `processed` | `rename-media.sh` specifically watches `processed` now and retries moving them to `staging`. |

## ✅ Verification Checklist

Before trusting this fully, verify:
1.  **Locking**: Start an upload (or `touch ~/.media_upload.lock`) and run `./sync-alldebrid.sh`. It should say "Upload in progress... Pausing".
2.  **Atomic Move**: Watch the `downloads` folder while a large file downloads. It should **not** appear until 100% complete.
3.  **Flow**: Drop a file in `processed` and ensure it automatically jumps to `staging` and then gets processed.

## 🔧 Maintenance Notes

- **The Lock File**: Located at `$HOME/.media_upload.lock`.
- **Configurable Thresholds**:
    - Min Disk Space: `20GB` (in `sync-alldebrid.sh`)
    - Sync Interval: `3600s` (via LaunchAgent)

## 🚀 How to Apply Changes

Since `rename-media.sh` runs as a daemon, you **must** restart it to pick up the new logic:

```bash
# Unload and Reload the Renamer Service
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.speedybee.media.renamer.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.speedybee.media.renamer.plist

# Optional: Run the sync manually to test (it might pause if lock exists)
./scripts/sync-alldebrid.sh
```
