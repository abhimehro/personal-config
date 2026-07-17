# Jellyfin Migration (Plex → Jellyfin)

**Status (2026-07-09):** Phase 1 **live**. Native Jellyfin 10.11.11 serves
`~/CloudMedia/mounted` on LAN **8096**. Colima hosting remains Phase 2
(optional). Plex/WebDAV untouched for rollback.

## Architecture (keep)

```
AllDebrid → CloudMedia pipeline → rclone union "media:"
                                      ↓
                         fuse-t / FSKit mount (read-only)
                                      ↓
                         ~/CloudMedia/mounted/{Movies,TV Shows}
                                      ↓
                    ┌─────────────────┴─────────────────┐
                    │                                   │
              Jellyfin (primary)                 WebDAV :8080
              LAN :8096                          (Infuse backup)
```

**Do not redesign** the rclone union, VFS cache, or WebDAV LaunchAgent. They
already work; Jellyfin is a new consumer of the same mount.

## Why native macOS (not Colima) for Phase 1

| Option                               | Verdict                                                                                                                              |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------ |
| **Native Jellyfin** (`.app` / cask)  | **Preferred / live.** Reads host fuse-t mount directly. LaunchAgent `com.speedybee.jellyfin`.                                        |
| **Colima + Docker**                  | Optional Phase 2. Colima is healthy and bind-mount of `~/CloudMedia/mounted` works, but shares CPU/RAM with email-security-pipeline. |
| **rclone serve** as Jellyfin library | Avoid. Double-hop hurts seeking.                                                                                                     |

### macOS cask gotcha

Official cask ships web UI at `Jellyfin.app/Contents/Resources/jellyfin-web`.
`jellyfin-daemon.sh` must pass `--webdir` to that path (plus `--service`) or the
server crash-loops looking for `Contents/MacOS/jellyfin-web`.

## Ports / coexistence

| Service                 | Port            | Notes                                                      |
| ----------------------- | --------------- | ---------------------------------------------------------- |
| Jellyfin HTTP           | **8096**        | Built-in auth; LAN + Windscribe remote (default path)      |
| Jellyfin HTTPS          | 8920            | Leave closed                                               |
| WebDAV (Infuse)         | 8080            | Unchanged                                                  |
| Plex (legacy)           | 32400           | Not listening on this host; data preserved                 |
| email-security-pipeline | (Colima bridge) | No host port conflict with 8096                            |

**Remote (default path, enabled 2026-07-17):** Windscribe maps
`82.23.253.53:8096` → host `8096/TCP`. Published Server URI:
`http://82.23.253.53:8096` (keep a LAN URI for home). Forwarding is on the
Windscribe side — Jellyfin has no Plex-style remote-access wizard.

**SECURITY:** Strong admin password required (1Password item `MediaServer`;
local file: `~/Library/Application Support/jellyfin/local-admin.credentials`).
HTTP over the static IP is intentional for the current VPN forward; harden with
HTTPS reverse proxy later if needed.

## Library settings for fuse-t / rclone mounts

- Prefer **scheduled** scans over real-time watchers (FUSE watchers are flaky).
- Mount is **read-only** — keep artwork in Jellyfin metadata DB / cache, not
  media folders.
- First scan is slow; subsequent plays use the existing 10GB VFS cache.

## Ops

```bash
# Status / validate
bash ~/dev/personal-config/media-streaming/scripts/validate-jellyfin.sh
# With item count:
JELLYFIN_API_KEY="$(tr -d '\n' < ~/Library/Application\ Support/jellyfin/local-api-key.txt)" \
  bash ~/dev/personal-config/media-streaming/scripts/validate-jellyfin.sh

# Re-bootstrap libraries (idempotent; uses existing local creds)
python3 ~/dev/personal-config/media-streaming/scripts/bootstrap-jellyfin-local.py

# Restart
launchctl kickstart -k "gui/$(id -u)/com.speedybee.jellyfin"
```

## Transcoding

Prefer Homebrew `ffmpeg` on PATH (VideoToolbox). `jellyfin-daemon.sh` passes
`--ffmpeg` to that binary. **Do not** install `jellyfin-ffmpeg` for Phase 1.

## Rollback

1. `launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.speedybee.jellyfin.plist`
2. Mount + WebDAV agents remain — Infuse/WebDAV clients keep working
3. Optional: remove `~/Library/Application Support/jellyfin` only for a clean
   re-wizard (destructive to Jellyfin config, not media)

## Phase 2 (Colima) — later

```bash
# Probe (already verified 2026-07-09):
docker --context colima run --rm -v "$HOME/CloudMedia/mounted:/media:ro" alpine ls /media

docker --context colima compose -f media-streaming/jellyfin/docker-compose.jellyfin.yml up -d
```
