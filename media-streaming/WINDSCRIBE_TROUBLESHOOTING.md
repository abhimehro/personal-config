# Media Server LaunchAgent & Windscribe Troubleshooting Guide

**Date**: June 20, 2026
**Status**: ✅ LaunchAgent Running | ✅ Stable Windscribe Port Plan Documented

---

## ✅ What's Fixed

### 1. `rename-media.sh` Script Error

**Problem**: Missing variable declarations causing LaunchAgent to crash repeatedly.

**Fix Applied**: Added missing variables:

```bash
MOVIE_DEST="Movies"
CLOUD_REMOTE="media"
LOG_FILE="${HOME}/Library/Logs/media-rename.log"
```

**Result**: ✅ Script now runs successfully (confirmed in logs at 01:30:11)

### 2. Missing Media Server LaunchAgent

**Problem**: No automatic startup for the WebDAV server.

**Fix Applied**: Created `com.speedybee.media.server.plist` with:

- Automatic startup on login (`RunAtLoad`)
- Auto-restart if it crashes (`KeepAlive`)
- Proper PATH configuration for Homebrew binaries
- 30-second throttle to prevent rapid restart loops

**Location**:

- Source: `~/Documents/dev/personal-config/media-streaming/launchd/com.speedybee.media.server.plist`
- Symlink: `~/Library/LaunchAgents/com.speedybee.media.server.plist`

### 3. Enhanced `final-media-server.sh`

**Improvements**:

- Detects VPN connection status automatically
- Fails explicitly if 1Password credentials unavailable (no temporary passwords)
- Supports three modes: `--local`, `--external`, `auto` (default)
- Provides clear Infuse configuration instructions for both LAN and VPN scenarios

---

## ⚠️ Windscribe Port Forwarding Issue

### Current Status

**VPN Static IP**: `82.21.151.194`
**Local WebDAV Server**: ✅ Stable internal port `8080`
**Primary Remote Media Server**: ✅ Plex on `32400/TCP`
**Backup Remote Media Server**: WebDAV on external `8088/TCP` -> internal `8080/TCP`

### Diagnosis

Earlier references to external port `22650` are stale. The current supported WebDAV backup mapping is `82.21.151.194:8088` externally to the Mac's internal WebDAV port `8080/TCP`. Plex is separate and should use `32400/TCP` internally and externally.

### Root Causes (Most Likely)

1. **Windscribe Port Forward Not Applied**
   - Port forwards in Windscribe require the VPN to be disconnected and reconnected after configuration
   - The static IP must be active and renewed

2. **Wrong Forward Configuration**
   - Windscribe forwards work differently than traditional router forwards
   - They require the internal IP to be the VPN tunnel IP (e.g., `100.125.56.240`), NOT the LAN IP (`192.168.0.111`)

3. **macOS Firewall Blocking**
   - Even though rclone is in the firewall rules, macOS may block unsolicited inbound connections
   - Needs explicit "Allow incoming connections" setting

---

## 🔧 Step-by-Step Fix for Windscribe Port Forward

### Step 1: Check Windscribe Port Forward Configuration

1. Open **Windscribe app**
2. Go to **Preferences -> Connection -> Port Forwarding**
3. Verify the stable mappings:
   ```
   Plex:
     External Port: 32400
     Internal Port: 32400
     Protocol: TCP

   WebDAV backup:
     External Port: 8088
     Internal Port: 8080
     Protocol: TCP
   ```

### Step 2: Keep WebDAV Internal Port Stable

WebDAV must remain on internal port `8080/TCP`. Do not forward `8081-8083` for remote use. If port `8080` is occupied, the daemon should fail loudly so the port conflict can be fixed instead of silently moving to a different internal port that Windscribe is not forwarding.

If Windscribe assigns a different external port, keep the internal port at `8080` and update only the client-side external port in Infuse.

### Step 3: Reconnect VPN

After updating the port forward:

1. **Disconnect** from Windscribe
2. Wait 10 seconds
3. **Reconnect** to activate the new port forward

### Step 4: Configure rclone to Bind to VPN Interface

rclone binds to `0.0.0.0:8080` so the same daemon can serve LAN clients and traffic arriving through the Windscribe tunnel. This is intentional for the backup WebDAV path.

Run the LaunchAgent-managed daemon for normal use:

```bash
launchctl kickstart -k gui/$(id -u)/com.speedybee.media.server
```

Use `final-media-server.sh --external` only as an interactive diagnostic helper.

### Step 5: Test External Connectivity

From another device (phone on cellular, NOT your WiFi):

```bash
curl -u "infuse:${MEDIA_WEBDAV_PASS}" "http://82.21.151.194:8088/"
```

Or open in a browser: `http://82.21.151.194:8088/`

---

## 🎯 Recommended Infuse Dual-Configuration

### Configuration 1: LAN (Primary)

- **Name**: "Home Media (Local)"
- **Protocol**: WebDAV
- **Address**: `192.168.0.111`
- **Port**: `8080`
- **Username**: `infuse`
- **Password**: `${MEDIA_WEBDAV_PASS}`

**Use when**: At home on the same WiFi network

### Configuration 2: VPN (Secondary) - AFTER PORT FORWARD FIX

- **Name**: "Media (Remote)"
- **Protocol**: WebDAV
- **Address**: `82.21.151.194`
- **Port**: `8088`
- **Username**: `infuse`
- **Password**: `${MEDIA_WEBDAV_PASS}`

**Use when**: Away from home, traveling, or on cellular

---

## 🚀 Starting/Loading LaunchAgents

### Load Media Server Agent (One-Time Setup)

```bash
launchctl load ~/Library/LaunchAgents/com.speedybee.media.server.plist
```

### Verify All Agents Are Running

```bash
launchctl list | grep speedybee
```

Expected output:

```
PID    STATUS    LABEL
11168  0         com.speedybee.media.renamer
-      0         com.speedybee.alldebrid.sync
[PID]  0         com.speedybee.media.server
```

### Manual Control Commands

**Stop server**:

```bash
launchctl unload ~/Library/LaunchAgents/com.speedybee.media.server.plist
```

**Start server**:

```bash
launchctl load ~/Library/LaunchAgents/com.speedybee.media.server.plist
```

**Restart server**:

```bash
launchctl kickstart -k gui/$(id -u)/com.speedybee.media.server
```

### Check Logs

**Media server**:

```bash
tail -f ~/Library/Logs/media-server.log
```

**Media renamer**:

```bash
tail -f ~/Library/Logs/media-renamer.log
```

**Alldebrid sync**:

```bash
tail -f ~/Library/Logs/alldebrid-sync.log
```

---

## 📋 Next Steps Checklist

- [ ] Confirm Windscribe Plex mapping: external `32400/TCP` -> internal `32400/TCP`
- [ ] Confirm Windscribe WebDAV backup mapping: external `8088/TCP` -> internal `8080/TCP`
- [ ] Disconnect and reconnect Windscribe VPN after changing mappings
- [ ] Test Plex remote access
- [ ] Test WebDAV external connectivity from a cellular device
- [ ] Confirm the media server LaunchAgent is running
- [ ] Configure Infuse backup connections for LAN `8080` and remote `8088`

---

## ⚡ Quick Reference

| Component              | Status      | Notes                                |
| ---------------------- | ----------- | ------------------------------------ |
| rename-media.sh        | ✅ FIXED    | Now has all required variables       |
| sync-alldebrid.sh      | ✅ OK       | Running hourly via LaunchAgent       |
| final-media-server.sh  | ✅ ENHANCED | Auto-detects VPN, 1Password enforced |
| LaunchAgent: renamer   | ✅ RUNNING  | Watch mode active                    |
| LaunchAgent: alldebrid | ✅ LOADED   | Syncs hourly                         |
| LaunchAgent: server    | ✅ RUNNING  | Serves backup WebDAV on stable 8080  |
| LAN Access             | ✅ WORKING  | `YOUR_LAN_IP:8080`                   |
| Plex Remote Access     | ✅ CONFIG   | `82.21.151.194:32400` -> `32400`     |
| WebDAV VPN Access      | ✅ CONFIG   | `82.21.151.194:8088` -> `8080`       |

---

**Updated**: 2026-06-20 by Raycast AI
