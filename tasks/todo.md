# Stream LA: LaunchAgents audit (2026-07-09)

## Plan
- [x] Inventory ~/Library/LaunchAgents + personal-config sources
- [x] Fix/verify email-security-pipeline (Colima healthy; LastExitStatus=0)
- [x] Fix maint.servicemonitor empty-array `set -u` crash; deploy to Library/Maintenance
- [x] Archive com.personal.ctrld-network-watch (broken `scutil --watch` + DNS fight)
- [x] Archive com.speedybee.media.permute (stale; exit 126 non-executable)
- [x] Fix secops.phase3 (restore shell impl; missing secops_agent.py) — also phase1/2 stubs
- [x] Verify sync-launchagents.sh (--prune OK; 12 agents; 0 failed)
- [x] Confirm Jellyfin `JELLYFIN_API_KEY unset` is soft optional skip
- [ ] Optional: rewrite ctrld-network-watch with `scutil -w` after Control D repair
- [ ] Optional: re-enable Permute agent after `chmod +x launch-permute.sh` if wanted
- [ ] Optional: add maintenance/ plists to sync-launchagents SRC_DIRS (label drift maint vs maintenance)

# Stream 1: Control D / Windscribe IPv6 + Reliability

## Eighth confirmation (2026-07-09 ~18:30 — post-dedupe, leave alone)
- [x] `sudo ./scripts/controld-dedupe-binary.sh` → Already symlink `/usr/local/bin/ctrld` → brew; wrote `/etc/controld/status` **WORKING / local_fallback**
- [x] dig @127.0.0.1 OK; ctrld **v1.5.3**; listener not restarted
- [x] Stable architecture remains profile-aware Local Config (not free DNS); CD Mode still upstream-broken


## Seventh live-validation fix pass (2026-07-09 ~18:00 — REAL daemon death: API exclude schema)
- [x] RCA confirmed from `/etc/controld/ctrld.log`: `cannot unmarshal number into … exclude of type string` → fatal fetch → KeepAlive crash-loop; explains missing toml + dig timeout + MallocStackLogging
- [x] Secondary: bash 3.2 `$listener_ip` + Unicode ellipsis → `listener_ip: unbound variable` under `set -u` (progress line)
- [x] Fix ellipsis; nested defaults for CONTROLD_CONFIG_ABS under set -u
- [x] Detect schema incompat (start log + recent daemon log); stop KeepAlive; profile-aware Local Config fallback (`https://dns.controld.com/<id>`, never free DNS)
- [x] Wire repair script to use fallback when dig fails after schema fatal
- [x] Unit tests (59 pass): schema detect, daemon-log path, write local config, ellipsis
- [x] Lesson 0dr + AGENTS.md
- [x] Live DNS confirmed WORKING/local_fallback after `controld-dedupe-binary.sh` (brew v1.5.3 symlink; dig OK; listener left alone)
- [ ] Optional: force CD Mode retry later with `--cd-mode` after upstream API fix (not needed while Local Config works)

### Live proof (done 2026-07-09 — do not thrash a healthy listener)
```bash
# Confirmed after dedupe:
#   /etc/controld/status → WORKING / local_fallback
#   dig @127.0.0.1 → resolves
#   which -a ctrld → brew v1.5.3 + /usr/local/bin/ctrld symlink
#   DNS not restarted by dedupe (listener left alone)

./scripts/controld-status.sh
dig @127.0.0.1 google.com +short +time=2
# Only if BROKEN:
#   ./scripts/free-port53-for-controld.sh --stop-colima   # if limactl on :53
#   sudo ./scripts/repair-controld-keepalive.sh --restart privacy
# Optional CD Mode force (expected fail until upstream):
#   sudo ./scripts/repair-controld-keepalive.sh --restart privacy --cd-mode
```

### Do NOT run (still)
- Static free-DNS / `dns.controld.com/free` configs
- `--listen` with `--cd`
- Vendor full Control D uninstall without pause
- Uninstall loops while Wi-Fi is on dead 127.0.0.1

## Plan
- [x] Investigate network-mode-manager, controld-service, windscribe-connect, ipv6-manager
- [x] Fix profile-switch reliability (service install race + false API-fallback)
- [x] Root-cause KeepAlive crash-loop / dead 127.0.0.1 DNS lockout (Lesson 0dh)
- [x] Add DoH+IPv6-enabled mode for Windscribe IPv6-capable servers
- [x] Preserve DoH+IPv6-disabled (leak prevention) and DoH3+IPv6-enabled
- [x] Auto-handle IPv6 from profile policy + VPN tunnel capability
- [x] Update reconcile/verify/tests; document cross-impacts
- [x] Unit tests green (controld-service, network-mode-manager pure, controld-profile)
- [x] RCA: API exclude schema + bash ellipsis (Lesson 0dr) — code+tests landed
- [x] Live validate: WORKING / local_fallback + dig @127.0.0.1 (2026-07-09 post-dedupe)

## Security gates (human approval required)
- No Control D full uninstall/reinstall performed
- No destructive network lockout changes
- Reversible script/config diffs only
- Repair script may call `ctrld service uninstall` only as last resort to clear KeepAlive (reinstalls on next start)
- **Binary upgrade (`ctrld upgrade` / brew) requires explicit user approval** — not run by agent

## Live validation (run in a Terminal with sudo)
```bash
# 0) If limactl holds :53 (Colima), free it FIRST — otherwise repair cannot bind
./scripts/free-port53-for-controld.sh              # diagnose
./scripts/free-port53-for-controld.sh --stop-colima
# permanent (optional): ./scripts/free-port53-for-controld.sh --patch-colima-ignore && colima start

# 1) Break the KeepAlive crash-loop and restore DNS (only if dig @127.0.0.1 fails)
sudo ./scripts/repair-controld-keepalive.sh --restart privacy

# 2) Full mode matrix (re-validates A/B/C after this fix)
./scripts/validate-controld-ipv6-modes.sh privacy
```

## Fifth live-validation fix pass (2026-07-09 ~17:10 — relative ctrld.toml / no logs)
- [x] RCA: force-uninstall + delete toml + start without abs `--config` → relative `ctrld.toml` → no logs → self-uninstall
- [x] Native start: `--cd` + `--config=/etc/controld/ctrld.toml` (**NO `--listen`** — see sixth pass / Lesson 0do)
- [x] Stop deleting CD-generated toml; DHCP-first repair; quarantine `~/.config/controld` static free DNS
- [x] Unit tests for absolute --config / no thrash; Lesson 0dn
- [x] Superseded by sixth pass (0do): `--listen` was the real no-log killer

## Sixth live-validation fix pass (2026-07-09 ~17:15 — `--listen` no-config-mode)
- [x] RCA: `--listen` + `--cd` → ctrld `isNoConfigStart` → fatal before CD write; relative Generating notice is false positive
- [x] Remove `--listen` from native argv; log real argv; privileged repair start as root + dig before localhost DNS
- [x] controld-manager discovers `CONTROLD_REPO` (installed `/usr/local/bin` cannot use `../..`)
- [x] Unit tests: omit `--listen`, assert abs `--config` + argv log (43 pass)
- [ ] User sudo fish restore once — see block below

### Fish restore (run once — privileged CD Mode)
```fish
# 0) Safety: never leave dead 127.0.0.1
networksetup -getdnsservers Wi-Fi
# if shows 127.0.0.1 AND dig @127.0.0.1 fails:
networksetup -setdnsservers Wi-Fi Empty
networksetup -setdnsservers "USB 10/100/1000 LAN" Empty

# 1) :53 must be free of limactl (Colima OK if Lima override patched)
lsof -nP -iUDP:53 -iTCP:53
# if limactl: ~/dev/personal-config/scripts/free-port53-for-controld.sh --stop-colima
# permanent: …/free-port53-for-controld.sh --patch-colima-ignore ; and colima stop && colima start

# 2) Privileged repair (does CD Mode start AS ROOT — do not hand off doomed non-root start)
cd ~/dev/personal-config
sudo ./scripts/repair-controld-keepalive.sh --restart privacy

# 3) Proof
dig @127.0.0.1 google.com +short +time=2
sudo head -1 /etc/controld/ctrld.toml
# expect: # AUTO-GENERATED VIA CD FLAG - DO NOT MODIFY
sudo grep -E 'endpoint|type' /etc/controld/ctrld.toml | head -6
# privacy expect: type = 'doh3' and endpoint = 'https://dns.controld.com/6m971e9jaf'
lsof -nP -iUDP:53 -iTCP:53   # expect ctrld, not limactl
./scripts/validate-controld-ipv6-modes.sh privacy
```

### Do NOT run
- `ctrld service start --cd … --listen …` (no-config-mode fatal — Lesson 0do)
- Repeated `ctrld service uninstall` / repair loops while DNS is on 127.0.0.1
- `ctrld start --config=…` without `--cd` (static Local Config Mode / free DNS)
- Vendor Control D full uninstall/reinstall until this path is tried once
- Restoring `~/.config/controld/ctrld.toml` free-DNS static file
- Patching only `~/.colima/default/colima.yaml` for :53 (use Lima `override.yaml`)
- Relying on stale `/usr/local/bin/controld-manager` without `CONTROLD_REPO` / `setup-controld.sh`

## Fourth live-validation fix pass (2026-07-09 ~16:40 — free :53 still fails)
- [x] RCA: readiness aborted in ~1.7s on single pgrep miss; recovery stop-thrashed; Colima patch wrote wrong file
- [x] Grace + dead-streak readiness; force reinstall `service start --cd --config=/etc/controld/ctrld.toml` (**no `--listen`** — Lesson 0do)
- [x] Lima `override.yaml` with `guestIPMustBeZero: false` — **proven**: Colima up, `lsof :53` empty, ha log `Not forwarding TCP 127.0.0.1:53`
- [x] Fixed `ctrld-network-watch` (`scutil -w` not `--watch`)
- [x] Unit tests 31 pass; Lesson 0dl
- [ ] User sudo: superseded by sixth-pass fish restore above

## Third live-validation fix pass (2026-07-09 ~16:20 — Colima :53 steal)
- [x] RCA: limactl (Colima) TCP *:53 blocks ctrld bind; dig timeout ≠ API failure
- [x] Fail-fast foreign :53 detection + DHCP fail-safe on listener-not-ready
- [x] free-port53-for-controld.sh + repair preflight
- [x] Unit tests green (28 pass incl. limactl holder + DHCP reset)
- [x] Colima stopped; host :53 free; Wi-Fi DNS = DHCP (connectivity OK)
- [ ] User sudo: `sudo ./scripts/repair-controld-keepalive.sh --restart privacy`
- [ ] Live validate after repair
- [ ] Optional permanent: `--patch-colima-ignore` then `colima start`

## Live validation (prior — KeepAlive / false API)
```bash
# 1) Break the KeepAlive crash-loop and restore DNS (only if dig @127.0.0.1 fails)
sudo ./scripts/repair-controld-keepalive.sh --restart privacy

# 2) Full mode matrix (re-validates A/B/C after this fix)
./scripts/validate-controld-ipv6-modes.sh privacy

# 3) Optional full regression
./scripts/network-mode-regression.sh browsing

# 4) Combined IPv4-only / static (leak prevention)
# bash/zsh:
WINDSCRIBE_IPV6=0 ./scripts/windscribe-connect.sh privacy Atlanta
# fish:
env WINDSCRIBE_IPV6=0 ./scripts/windscribe-connect.sh privacy Atlanta

# 5) Combined IPv6-capable (or force)
# bash/zsh:
WINDSCRIBE_IPV6=1 ./scripts/windscribe-connect.sh privacy "Toronto"
# fish:
env WINDSCRIBE_IPV6=1 ./scripts/windscribe-connect.sh privacy "Toronto"
```

## Second live-validation fix pass (2026-07-09 ~14:00 bugs)
- [x] A: Separate listener-not-ready from API failure; longer dig wait; no false static fallback
- [x] B: Protocol short-circuit requires profile AND protocol; force doh3↔doh restart
- [x] C: Reconcile heuristics — intentional doh-ipv4 (IPv6 off) is healthy without VPN
- [x] D: Fish docs for `env WINDSCRIBE_IPV6=0|1 …`
- [x] E: whoami/AAAA classified as expected soft noise in verify/docs
- [x] Unit tests for false API classification + protocol short-circuit
- [ ] Live re-validate (needs sudo in user Terminal)

# Stream 3: Media Server Migration (Plex → Jellyfin)

## Decision (2026-07-09)
- **Migrate: YES (Phase 1 native)** — library mount healthy; Plex not serving on this host.
- **Keep** rclone fuse-t mount + WebDAV `:8080` unchanged.
- **Colima for Jellyfin: Phase 2 deferred (optional)** — Colima is healthy *and* bind-mount of `~/CloudMedia/mounted` works (alpine ls + 64KB read @ ~1.2MB/s). Native Phase 1 chosen to avoid shared-VM contention with email-security-pipeline; compose file ready when desired.
- **Do not** expose `:8096` via Windscribe until LAN + auth review.

## Plan
- [x] Evaluate architecture (rclone → fuse-t → CloudMedia; WebDAV backup; Plex legacy)
- [x] Probe Colima bind-mount of fuse-t library (PASS)
- [x] Install Jellyfin (Homebrew cask) + LaunchAgent
- [x] Complete local-only startup wizard (built-in auth; credentials local file, rotate to 1Password)
- [x] Add Movies + TV Shows libraries from mount
- [x] Validate HTTP + mount byte probe + Items API
- [x] Update docs/lessons for Colima probe result; leave Plex/WebDAV untouched

## Security gates (human approval required — not done this run)
- [ ] Windscribe / public forward of 8096
- [ ] Delete Plex library/data or retire Plex clients
- [ ] Move Jellyfin to Colima compose (Phase 2)
