# Proton Drive Backup - Reliable Setup (Archive-Based)

## Why this change
Proton Drive on macOS uses **on-demand sync** via Apple’s **File Provider**. Syncing tens of thousands of tiny files into the Proton Drive folder can wedge the provider and trigger upload failures like **“No URL for file upload”**. ([proton.me](https://proton.me/support/proton-drive-macos-on-demand-sync))

Proton’s own macOS client repo highlights that File Provider can get into a bad state and recommends full cleanup/unregister steps for persistent issues. ([github.com](https://github.com/ProtonDriveApps/mac-drive))

## New approach (recommended)
Instead of rsyncing 20k+ files into Proton Drive, we:

* Create **one archive** locally (fast and stable)
* Copy **one file** into Proton Drive (low-churn upload)
* Keep the last N archives (retention)

This dramatically reduces File Provider stress and improves reliability. ([proton.me](https://proton.me/support/proton-drive-macos-on-demand-sync))

## Step-by-step setup

### 1) Make the Proton destination folder offline
In Finder:

* Locations → Proton Drive
* Navigate to: `HomeBackup/Archives` (we’ll create it if missing)
* Right-click `Archives` → **Make available offline** (✅)

This reduces placeholder/dataless behavior and helps prevent timeouts. ([proton.me](https://proton.me/support/proton-drive-macos-on-demand-sync))

### 2) Use the new archive script
New script:

* `maintenance/bin/protondrive_backup_archive.sh`

Dry run:

```bash
~/Documents/dev/personal-config/maintenance/bin/protondrive_backup_archive.sh
```

Real run:

```bash
~/Documents/dev/personal-config/maintenance/bin/protondrive_backup_archive.sh --run
```

It writes an archive to a local staging folder, then copies it into:

* `~/Library/CloudStorage/ProtonDrive-abhimehro@pm.me-folder/HomeBackup/Archives/`

### 3) Update the LaunchAgent to use the archive script
Update ProgramArguments to call:

* `/Users/speedybee/Library/Maintenance/bin/protondrive_backup_archive.sh`
* `--run`

And remove `--no-delete` (not relevant for archive mode).

### 4) If Proton Drive is already wedged
If you still see “No URL for file upload”, collect diagnostics and do a full File Provider cleanup per Proton’s repo.

* Generate `fileproviderctl diagnose` output
* Use Proton’s `Scripts/macos/unregister.sh` and `Scripts/macos/uninstall.sh`

Warning: Proton’s uninstall script may clear local Proton Drive folder contents. ([github.com](https://github.com/ProtonDriveApps/mac-drive))

## Suggested schedule
Because this backup can create large archives, consider:

* Weekly at 3:15 AM (instead of daily)

You can keep daily if your data size is moderate, but weekly aligns with your stated intent. ([proton.me](https://proton.me/support/proton-drive-macos-on-demand-sync))

## Support escalation packet
If the issue persists even with archive mode:

* ProtonDriveFileProvider logs: `~/Library/Group Containers/2SB5Z68H26.ch.protonmail.protondrive/Logs/`
* `fileproviderctl check/repair` outputs
* `fileproviderctl diagnose` bundle

Send these to Proton Support for investigation. ([proton.me](https://proton.me/support/drive))
