# Plex → Jellyfin — Execution Plan (Stream 3)

## Phase 0 — Evaluate (done 2026-07-09)

- Confirmed library path: rclone `media:` union → fuse-t/FSKit →
  `~/CloudMedia/mounted`
- Confirmed WebDAV backup: `com.speedybee.media.server` on `:8080` (auth
  required; leave as Infuse backup)
- Confirmed mount agent: `com.speedybee.media.mount` KeepAlive
- Plex: Preferences exist under Application Support but **no listener on
  :32400** this host — nothing to cut over; leave data alone
- Colima: **healthy** (2026-07-09 re-check). Bind-mount probe of fuse-t library
  **PASS** (`alpine ls` + 64KB read). Still **defer** Colima hosting to Phase 2
  to avoid shared-VM contention with email-security-pipeline

## Phase 1 — Native Jellyfin (DONE 2026-07-09)

1. ✅ `brew install --cask jellyfin` (10.11.11)
2. ✅ Fixed `jellyfin-daemon.sh` to pass
   `--webdir …/Contents/Resources/jellyfin-web` + `--service`
3. ✅ `setup-jellyfin-native.sh` → LaunchAgent `com.speedybee.jellyfin`
4. ✅ Local bootstrap (`bootstrap-jellyfin-local.py`): built-in admin,
   RemoteAccess off, Movies + TV Shows libraries
5. ✅ `validate-jellyfin.sh` exit 0 (mount + /health + Items)
6. ✅ PlaybackInfo resolves fuse-t path with `SupportsDirectPlay=true`

### Credentials / first login

- Wizard creates the admin user via `POST /Startup/User` (non-empty password).
  Credentials are whatever you set during bootstrap / first-run wizard — they
  are **not** stored in this repo.
- If you forgot them: Jellyfin Dashboard → Users, or reset via Jellyfin docs; do
  not commit passwords.

### Transcoding / VideoToolbox

- Prefer Homebrew `ffmpeg` (VideoToolbox-capable) via
  `jellyfin-daemon.sh --ffmpeg`; **do not** `brew install jellyfin-ffmpeg` for
  Phase 1.
- Revisit only if hardware encode fails in Dashboard → Playback.

### API key

- `validate-jellyfin.sh` soft-skips API-key checks when `JELLYFIN_API_KEY` is
  unset — that is expected, not a failure.

### Cross-system: Colima

- email-security-pipeline depends on Colima. Keep Jellyfin **native** so the
  shared VM is not fighting media + mail.
- Control D coexistence: Lima `override.yaml` must ignore guest `:53`
  (`free-port53-for-controld.sh --patch-colima-ignore`) so limactl does not
  steal host DNS from ctrld.

## Phase 2 — Colima (deferred / optional)

- Compose: `docker-compose.jellyfin.yml`
- Only after measuring Colima headroom with email-security-pipeline
- Probe already green; no architectural blocker

## Phase 3 — Remote / retire Plex

**Remote Jellyfin: suspended pending trusted HTTPS ingress**

- Delete the old Windscribe external **8096** → internal **8096** TCP forward.
- Remove the public HTTP Published Server URI from Jellyfin Networking.
- The native LaunchAgent binds HTTP only to loopback and validated private LAN
  IPv4 addresses and disables remote access. Restore remote clients only after a
  trusted HTTPS ingress is configured; do not forward Jellyfin's HTTP port.

**Still open (human):**

- [ ] Retire Plex clients / delete Plex data / remove `32400` forward — only
      with explicit approval
- [ ] Configure a trusted HTTPS ingress before restoring remote Jellyfin access
