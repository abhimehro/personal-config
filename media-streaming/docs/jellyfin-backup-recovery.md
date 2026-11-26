# CloudMedia recovery

The user LaunchAgent `com.speedybee.jellyfin.backup` runs at 02:45 local time.
It writes one AES-256-GCM CMS archive per weekday number (seven rotating slots)
in each of these locations:

- `~/Library/Application Support/CloudMedia Recovery/snapshots/`
- The existing Google Drive `My Drive/HomeBackup/CloudMedia Recovery/`

The private key is
`~/Library/Application Support/CloudMedia Recovery/recovery.pem`. Save it
separately in an independent password manager or offline vault. Do not commit it
or upload it beside the archives. A lost Mac plus a lost key makes the Drive
archives unusable. Keep the matching recipient.crt for future backups.

Each archive contains an online SQLite backup of data/jellyfin.db, config, root,
plugin files and settings, playlists, and the device identifier when available.
It excludes media, regenerable artwork/cache, and standalone admin credentials.
SQLite is transaction-consistent; the supporting files are copied individually.
Logs are ~/Library/Logs/jellyfin-backup.{out,err}. A verified File Provider
readback is not a receipt from the remote Google Drive service.

## Test or restore in a private staging directory

1. Download an archive and retrieve the matching private key. Create an empty
   private directory with mode 0700 outside a synced folder; work there with
   umask 077.
2. Run
   `/opt/homebrew/bin/openssl cms -decrypt -binary -inform DER -in "/path/to/archive.cms" -inkey "/path/to/recovery.pem" -out snapshot.zip`.
3. Run `unzip -t snapshot.zip`, then extract it into that empty directory. Run
   `sqlite3 -readonly data/jellyfin.db 'PRAGMA integrity_check;'` and expect
   `ok`.
4. For live recovery, unload the Jellyfin agent, retain the entire current
   server folder as a rollback copy, and restore into a fresh server folder. Do
   not overlay SQLite WAL or SHM files from another database. Keep plugins
   offline during initial validation if their sync direction or account mapping
   is unknown.
5. Load the agent. Verify /health, authenticated library counts, user playback
   history, and an Infuse sync before discarding any rollback copy.
