# Cloud Backup Options (macOS) — Recommended

## Summary
If a cloud client (especially one using macOS File Provider / on-demand sync) is unstable, the most reliable approach is to avoid syncing **tens of thousands of tiny files** directly and instead sync **a small number of archive files**. This minimizes sync churn and reduces the chance of provider/database issues.

This repository now supports an **archive-based backup workflow** that creates a single `.tar.gz` locally and copies it into your cloud folder.

## Option A (Recommended): Google Drive as the backup target
### Why
* Google Drive (DriveFS) has been more stable in your macOS workflow than OneDrive and Proton Drive.
* The archive-based strategy keeps Google Drive sync work to “few large files” instead of “many tiny files”.

### What’s included
* `maintenance/bin/protondrive_backup_archive.sh`
    * The shared archive engine (name kept for historical reasons)
    * Supports `--profile light|full`
* `maintenance/bin/google_drive_backup_archive.sh`
    * Google Drive wrapper that targets a writable destination under **My Drive**:
      `~/Library/CloudStorage/GoogleDrive-<account>/My Drive/Backups/MaintenanceArchives/`
* LaunchAgents:
    * Daily light: `maintenance/launchd/com.speedybee.maintenance.gdrivebackup.plist`
    * Weekly full: `maintenance/launchd/com.speedybee.maintenance.gdrivebackup.full.plist`

### Manual runs
```bash
# Daily-style (light)
~/Documents/dev/personal-config/maintenance/bin/google_drive_backup_archive.sh --run

# Weekly-style (full)
~/Documents/dev/personal-config/maintenance/bin/google_drive_backup_archive.sh --run --profile full --retention 8
```

## Option B: Proton Drive (not recommended for automated high-churn backups right now)
If Proton Drive is stable for you, you can use the same archive engine to copy an archive into Proton Drive. However, if you see File Provider errors like “No URL for file upload”, it’s safer to keep Proton Drive for occasional manual archives until the provider state is healthy again.

## Option C: OneDrive (optional)
If OneDrive has been unreliable on your MacBooks, keep it out of the automated backup path unless you specifically need it.

## Recommendation
* Primary: **Google Drive** (daily light + weekly full archives)
* Secondary: Proton Drive only if/when it’s stable again
