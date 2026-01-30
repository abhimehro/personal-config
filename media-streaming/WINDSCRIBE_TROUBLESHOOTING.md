# Media Server LaunchAgent & Windscribe Troubleshooting Guide

**Date**: January 29, 2026
**Status**: ✅ LaunchAgent Created | ⚠️ Windscribe Port Forward Needs Configuration

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
**VPN Connected**: ✅ Yes (Public IP: 82.21.151.194)
**Local Server**: ✅ Running on port 8080
**External Access**: ❌ **PORT 22650 NOT REACHABLE**

### Diagnosis
The connection to `82.21.151.194:22650` times out, which indicates the port forward is **not working** despite being configured in Windscribe.

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
2. Go to **Preferences → Connection → Port Forwarding**
3. Verify the configuration:
   ```
   External Port: 22650
   Internal Port: 8080
   Protocol: TCP
   ```

### Step 2: Use Correct Internal IP (CRITICAL)

**The internal IP should be your VPN tunnel IP, NOT your LAN IP!**

Your VPN tunnel IP is: `100.125.56.240` (from `utun420` interface)

Update the Windscribe port forward to:
```
External: 82.21.151.194:22650 → Internal: 100.125.56.240:8080
```

### Step 3: Reconnect VPN

After updating the port forward:
1. **Disconnect** from Windscribe
2. Wait 10 seconds
3. **Reconnect** to activate the new port forward

### Step 4: Configure rclone to Bind to VPN Interface

Currently, rclone binds to `0.0.0.0:8080` (all interfaces). To ensure traffic comes through the VPN tunnel, we can bind specifically to the VPN IP:

Run the updated server script with:
```bash
~/Documents/dev/personal-config/media-streaming/scripts/final-media-server.sh --external
```

Or modify the script to bind to `100.125.56.240:8080` when VPN is detected.

### Step 5: Test External Connectivity

From another device (phone on cellular, NOT your WiFi):
```bash
curl -u "infuse:MALARIA7bunch!katarina" "http://82.21.151.194:22650/"
```

Or open in a browser: `http://82.21.151.194:22650/`

---

## 🎯 Recommended Infuse Dual-Configuration

### Configuration 1: LAN (Primary)
- **Name**: "Home Media (Local)"
- **Protocol**: WebDAV
- **Address**: `192.168.0.111`
- **Port**: `8080`
- **Username**: `infuse`
- **Password**: `MALARIA7bunch!katarina`

**Use when**: At home on the same WiFi network

### Configuration 2: VPN (Secondary) - AFTER PORT FORWARD FIX
- **Name**: "Media (Remote)"
- **Protocol**: WebDAV
- **Address**: `82.21.151.194`
- **Port**: `22650`
- **Username**: `infuse`
- **Password**: `MALARIA7bunch!katarina`

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

- [ ] Fix Windscribe port forward to use VPN tunnel IP (`100.125.56.240`)
- [ ] Disconnect and reconnect Windscribe VPN
- [ ] Test external connectivity from cellular device
- [ ] Load the media server LaunchAgent
- [ ] Configure dual connections in Infuse
- [ ] Test both LAN and VPN connections

---

## ⚡ Quick Reference

| Component | Status | Notes |
|-----------|--------|-------|
| rename-media.sh | ✅ FIXED | Now has all required variables |
| sync-alldebrid.sh | ✅ OK | Running hourly via LaunchAgent |
| final-media-server.sh | ✅ ENHANCED | Auto-detects VPN, 1Password enforced |
| LaunchAgent: renamer | ✅ RUNNING | Watch mode active |
| LaunchAgent: alldebrid | ✅ LOADED | Syncs hourly |
| LaunchAgent: server | 🆕 CREATED | Ready to load |
| LAN Access | ✅ WORKING | 192.168.0.111:8080 |
| VPN Access | ⚠️ BROKEN | Port 22650 not forwarding |

---

**Generated**: 2026-01-29 by RayFusion AI Assistant
