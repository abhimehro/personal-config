# Jellyfin Migration (Plex → Jellyfin)

**Status:** Native Jellyfin serves `~/CloudMedia/mounted` on LAN **8096**.
Direct remote HTTP access is disabled. Colima hosting remains Phase 2
(optional). Plex is legacy; WebDAV remains Infuse backup.

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

| Service                 | Port            | Notes                                                 |
| ----------------------- | --------------- | ----------------------------------------------------- |
| Jellyfin HTTP           | **8096**        | Built-in auth; loopback + LAN interfaces only         |
| Jellyfin HTTPS          | 8920            | Leave closed                                          |
| WebDAV (Infuse)         | 8080            | Unchanged                                             |
| Plex (legacy)           | 32400           | Not listening on this host; data preserved            |
| email-security-pipeline | (Colima bridge) | No host port conflict with 8096                       |

**Remote access:** Delete the old Windscribe external `8096` → internal `8096`
forward and remove its HTTP Published Server URI in Jellyfin Networking. The
LaunchAgent now limits Jellyfin HTTP to loopback and validated private IPv4
addresses on the Mac's LAN interfaces (`en5`/`en0`) and disables Jellyfin remote
access on each start. If neither interface has a private IPv4 address, Jellyfin
listens on loopback only. Restart the LaunchAgent after updating this checkout.
For future remote access, use a
trusted HTTPS ingress with a valid certificate that proxies to loopback; keep
the direct HTTP forward closed. Before restoring remote clients, update this
startup guard for that specific proxy, register it as a Known Proxy in Jellyfin,
verify its forwarded headers, and enable remote access explicitly. A strong
admin password remains required
(1Password item `MediaServer`; local file:
`~/Library/Application Support/jellyfin/local-admin.credentials`).

If startup reports that `network.xml` is missing while `system.xml` exists,
the daemon stops rather than bypassing Jellyfin's legacy network migration.
Remove the Windscribe `8096` forward and disconnect the VPN, run the stock
Jellyfin app once on the trusted LAN to generate `config/network.xml`, then
quit it. From this checkout, run:

```bash
python3 media-streaming/scripts/secure-jellyfin-network.py \
  "$HOME/Library/Application Support/jellyfin/config/network.xml"
```

Restart the LaunchAgent only after that command succeeds. Then reconnect
Windscribe.

The daemon also refuses to start if `network.xml` disables `EnableIPv4` or the
legacy `EnableIPV4`. Set the present value to `true` before restarting; the
restricted HTTP listener uses IPv4 addresses only.

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
