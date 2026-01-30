# Windscribe Port Forwarding - Complete Setup Guide

## 🎉 Good News: Windscribe Auto-Configures Internal IP!

After further investigation, I need to clarify how Windscribe port forwarding works:

**You DO NOT need to manually specify the VPN tunnel IP (100.125.56.240).**

When you select your **MacBook Air** as the device in Windscribe's port forwarding settings, Windscribe **automatically maps** the internal port to the correct VPN tunnel IP. The device selection is the key - Windscribe knows your device's VPN tunnel IP on their end.

---

## ✅ Correct Windscribe Port Forward Configuration

### For WebDAV (Media Server):

| Setting | Value |
|---------|-------|
| **Static IP** | 82.21.151.194 |
| **Name** | MediaServer |
| **Protocol** | **TCP** (WebDAV uses TCP only) |
| **Device** | MacBook Air (from device list) |
| **External Port** | 22650 |
| **Internal Port** | 8080 |

### For SSH:

| Setting | Value |
|---------|-------|
| **Static IP** | 82.21.151.194 |
| **Name** | SSH |
| **Protocol** | **TCP** (SSH uses TCP only) |
| **Device** | MacBook Air (from device list) |
| **External Port** | 35008 |
| **Internal Port** | 22 |

---

## 🔧 How Windscribe Port Forwarding Works

When you configure port forwarding in Windscribe:

1. You select your **device** (MacBook Air) from the list
2. Windscribe associates that device with your **VPN tunnel IP** (100.125.56.240)
3. When external traffic arrives at `82.21.151.194:22650`:
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
- Traffic to 82.21.151.194:22650 from your Mac tries to loop back through Windscribe
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
curl -u "infuse:MALARIA7bunch!katarina" http://127.0.0.1:8080/
```
Expected: HTTP 200 OK with HTML response

### Step 2: Verify LAN Access
```bash
# From another device on same WiFi (should work)
curl -u "infuse:MALARIA7bunch!katarina" http://192.168.0.111:8080/
```
Expected: HTTP 200 OK

### Step 3: Verify Windscribe Connection
```bash
# From your Mac
curl -s ifconfig.me
```
Expected: `82.21.151.194`

### Step 4: Test External Port Forward
**MUST BE DONE FROM EXTERNAL DEVICE (phone on cellular, NOT WiFi):**
```bash
curl -u "infuse:MALARIA7bunch!katarina" http://82.21.151.194:22650/
```
Expected: HTTP 200 OK with HTML response

Or simply open in mobile browser:
```
http://82.21.151.194:22650/
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

# Reconnect to VPN with static IP
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

### Secondary: Remote (82.21.151.194:22650)
⏳ **Needs external testing to confirm**

- Use when: Away from home, on cellular, traveling
- Requires Windscribe VPN connected on your Mac
- Port forward must be active and properly configured

**Both use the same credentials** (from 1Password):
- Username: `infuse`
- Password: `MALARIA7bunch!katarina`

---

## 🔐 Your SSH Configuration

**Good news**: Your SSH port forward should work the same way!

Current SSH setup (from your description):
```
External: 82.21.151.194:35008 → Internal: MacBook Air:22
```

This is correctly configured! The same principles apply:
- Windscribe maps the device to the VPN tunnel IP automatically
- External SSH access: `ssh user@82.21.151.194 -p 35008`
- Cannot be tested from your own Mac (hairpin NAT limitation)

**To test SSH externally:**
```bash
# From external device (phone, cloud server, etc.)
ssh speedybee@82.21.151.194 -p 35008
```

---

## 📋 Summary & Next Steps

### ✅ What's Confirmed Working
- Local media server (127.0.0.1:8080) ✓
- LAN access (192.168.0.111:8080) ✓
- Windscribe VPN connected (82.21.151.194) ✓
- Server listening on all interfaces (*:8080) ✓
- LaunchAgents properly configured ✓

### ⏳ What Needs External Testing
- Port forward 22650 → 8080 (requires testing from cellular/external network)
- Port forward 35008 → 22 (SSH, same requirement)

### 🎯 Your Action Items
1. Ensure Windscribe port forwards are configured:
   - MediaServer: TCP, MacBook Air, External 22650 → Internal 8080
   - SSH: TCP, MacBook Air, External 35008 → Internal 22

2. **Disconnect and reconnect** Windscribe (critical!)

3. Test from external device (iPhone on cellular):
   ```
   http://82.21.151.194:22650/
   ```

4. If it works: Configure secondary connection in Infuse!

5. If it doesn't work: Check Windscribe app for port forward status or contact support

---

**Last Updated**: January 29, 2026
**Status**: LAN connection fully operational, external connection awaiting verification
