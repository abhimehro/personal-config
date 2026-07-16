# Windscribe Port Forwarding - Complete Setup Guide

> **Static IP (2026-07):** Dallas `82.23.253.53` (replaces expired Atlanta
> `82.21.151.194`). Connect with
> `./scripts/windscribe-connect.sh privacy` (defaults to `connect static Dallas`).
> For IPv6, use Atlanta/Peachtree non-static:
> `WINDSCRIBE_IPV6=1 ./scripts/windscribe-connect.sh privacy`.

## 🎉 Good News: Windscribe Auto-Configures Internal IP!

After further investigation, I need to clarify how Windscribe port forwarding works:

**You DO NOT need to manually specify the VPN tunnel IP (100.125.56.240).**

When you select your **MacBook Air** as the device in Windscribe's port forwarding settings, Windscribe **automatically maps** the internal port to the correct VPN tunnel IP. The device selection is the key - Windscribe knows your device's VPN tunnel IP on their end.

---

## ✅ Correct Windscribe Port Forward Configuration

### For Jellyfin (primary media server — opt-in remote):

| Setting           | Value                          |
| ----------------- | ------------------------------ |
| **Static IP**     | 82.23.253.53                   |
| **Name**          | Jellyfin                       |
| **Protocol**      | **TCP**                        |
| **Device**        | MacBook Air (from device list) |
| **External Port** | 8096                           |
| **Internal Port** | 8096                           |

> **SECURITY:** Jellyfin has no Plex-style “Remote Access” toggle that opens
> ports for you. Remote reachability is entirely the Windscribe forward + your
> firewall. Do **not** enable this forward until LAN playback and admin auth are
> verified (`media-streaming/jellyfin/MIGRATION_PLAN.md` Phase 3). After
> enabling, set **Dashboard → Networking → Published Server URIs** to
> `http://82.23.253.53:8096` (and keep LAN URI if you use both).

### For WebDAV (Infuse backup):

| Setting           | Value                          |
| ----------------- | ------------------------------ |
| **Static IP**     | 82.23.253.53                   |
| **Name**          | MediaServer                    |
| **Protocol**      | **TCP** (WebDAV uses TCP only) |
| **Device**        | MacBook Air (from device list) |
| **External Port** | 8088                           |
| **Internal Port** | 8080                           |

### For SSH:

| Setting           | Value                          |
| ----------------- | ------------------------------ |
| **Static IP**     | 82.23.253.53                   |
| **Name**          | SSH                            |
| **Protocol**      | **TCP** (SSH uses TCP only)    |
| **Device**        | MacBook Air (from device list) |
| **External Port** | 36555                          |
| **Internal Port** | 22                             |

### Plex (legacy — optional)

Plex is no longer the primary server on this host. If you still run it, the old
mapping was External **32400** → Internal **32400**. Prefer Jellyfin **8096**
instead; remove the Plex forward once clients have migrated.

---

## 🔧 How Windscribe Port Forwarding Works

When you configure port forwarding in Windscribe:

1. You select your **device** (MacBook Air) from the list
2. Windscribe associates that device with your **VPN tunnel IP** (100.125.56.240)
3. When external traffic arrives at `82.23.253.53:8088`:
   - Windscribe routes it to your VPN tunnel: `100.125.56.240:8080`
   - Your Mac's `utun420` interface receives the traffic
   - rclone server (listening on `*:8080`) accepts the connection

**You don't manually configure the VPN tunnel IP** - Windscribe handles that mapping automatically when you select the device!

---

## ⚠️ Why Your Port Forward Might Not Be Working

### 1. **Port Forward Not Active/Applied**

After creating or modifying a port forward:

- You MUST disconnect from Windscribe
- Wait 10-15 seconds
- Reconnect to Windscribe
- The port forward only activates after a fresh connection

### 2. **Hairpin NAT / Loopback Issue**

You **cannot test** the external connection from your own Mac. This is a limitation of NAT:

- Your Mac is "inside" the VPN tunnel
- Traffic to 82.23.253.53:8088 from your Mac tries to loop back through Windscribe
- Most VPN providers (including Windscribe) don't support hairpin NAT

**Testing must be done from an external device:**

- iPhone/iPad on **cellular data** (NOT WiFi)
- Another computer on a different network
- Cloud server (AWS EC2, DigitalOcean, etc.)

### 3. **Firewall or macOS Security**

Even though rclone is in the firewall rules, macOS might still block unsolicited inbound connections:

**Check firewall settings:**

```bash
/usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate
/usr/libexec/ApplicationFirewall/socketfilterfw --getblockall
```

**If needed, temporarily disable to test:**

```bash
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate off
```

(Remember to re-enable after testing: `--setglobalstate on`)

---

## 🧪 Testing Checklist

### Step 1: Verify Local Server is Running

```bash
# From your Mac (should work)
curl -u "infuse:${MEDIA_WEBDAV_PASS}" http://127.0.0.1:8080/
```

Expected: HTTP 200 OK with HTML response

### Step 2: Verify LAN Access

```bash
# From another device on same WiFi (should work)
curl -u "infuse:${MEDIA_WEBDAV_PASS}" http://192.168.0.111:8080/
```

Expected: HTTP 200 OK

### Step 3: Verify Windscribe Connection

```bash
# From your Mac
curl -s ifconfig.me
```

Expected: `82.23.253.53`

### Step 4: Test External Port Forward

**MUST BE DONE FROM EXTERNAL DEVICE (phone on cellular, NOT WiFi):**

```bash
curl -u "infuse:${MEDIA_WEBDAV_PASS}" http://82.23.253.53:8088/
```

Expected: HTTP 200 OK with HTML response

Or simply open in mobile browser:

```
http://82.23.253.53:8088/
```

(Will prompt for username/password)

---

## 🔍 Troubleshooting If External Access Still Fails

### 1. Check Windscribe Port Forward Status

In Windscribe app:

- Go to **Preferences → Connection → Port Forwarding**
- Look for your MediaServer entry
- Status should show **Active** or **Enabled**

### 2. Verify Device Association

- Make sure "MacBook Air" is selected (not "Manual Device")
- Windscribe needs to recognize your device to map the tunnel IP

### 3. Check Windscribe Logs

Windscribe may have debug logs showing port forward activity:

```bash
# Check if Windscribe has logs
ls ~/Library/Application\ Support/Windscribe/
```

### 4. Try Restarting Windscribe Completely

```bash
# Quit Windscribe app
killall Windscribe

# Wait 5 seconds

# Relaunch Windscribe
open -a Windscribe

# Reconnect to VPN with static IP (Dallas):
#   ./scripts/windscribe-connect.sh privacy
#   # or: windscribe-cli connect static Dallas
```

### 5. Contact Windscribe Support

If after all these steps external access still fails:

- The static IP or port forward feature might need to be re-provisioned
- Windscribe support can verify server-side configuration
- They can see if traffic is reaching your tunnel IP

---

## 📱 Infuse Configuration (Both Connections)

### Primary: LAN (192.168.0.111:8080)

✅ **This already works perfectly!**

- Use when: At home on WiFi
- Best performance, no VPN overhead
- No re-caching needed when switching between devices on same network

### Secondary: Remote (82.23.253.53:8088)

⏳ **Needs external testing to confirm**

- Use when: Away from home, on cellular, traveling
- Requires Windscribe VPN connected on your Mac
- Port forward must be active and properly configured

**Both use the same credentials** (from 1Password):

- Username: `infuse`
- Password: `${MEDIA_WEBDAV_PASS}`

---

## 🔐 Your SSH Configuration

**Good news**: Your SSH port forward should work the same way!

Current SSH setup (from your description):

```
External: 82.23.253.53:36555 -> Internal: MacBook Air:22
```

This is correctly configured! The same principles apply:

- Windscribe maps the device to the VPN tunnel IP automatically
- External SSH access: `ssh user@82.23.253.53 -p 36555`
- Cannot be tested from your own Mac (hairpin NAT limitation)

**To test SSH externally:**

```bash
# From external device (phone, cloud server, etc.)
ssh speedybee@82.23.253.53 -p 36555
```

---

## 📋 Summary & Next Steps

### ✅ What's Confirmed Working

- Local media server (127.0.0.1:8080) ✓
- LAN access (192.168.0.111:8080) ✓
- Windscribe VPN connected (82.23.253.53) ✓
- Server listening on all interfaces (\*:8080) ✓
- LaunchAgents properly configured ✓

### ⏳ What Needs External Testing

- Port forward 8088 -> 8080 (requires testing from cellular/external network)
- Port forward 36555 -> 22 (SSH, same requirement)

### 🎯 Your Action Items

1. Ensure Windscribe port forwards are configured:
   - **Jellyfin** (opt-in): TCP, MacBook Air, External 8096 -> Internal 8096
   - MediaServer WebDAV backup: TCP, MacBook Air, External 8088 -> Internal 8080
   - SSH: TCP, MacBook Air, External 36555 -> Internal 22
   - Plex 32400: legacy only — remove once Jellyfin remote is preferred

2. **Disconnect and reconnect** Windscribe (critical!)

3. Test from external device (iPhone on cellular):

   ```
   http://82.23.253.53:8096/   # Jellyfin (if forward enabled)
   http://82.23.253.53:8088/   # WebDAV backup
   ```

4. If WebDAV works: Configure secondary connection in Infuse!

5. If it doesn't work: Check Windscribe app for port forward status or contact support

---

**Last Updated**: 2026-07-16
**Status**: Jellyfin primary on LAN 8096; Windscribe static Dallas `82.23.253.53`;
WebDAV backup `8088→8080`; Jellyfin remote forward documented as opt-in
