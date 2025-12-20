# 🔐 SSH Over Windscribe VPN Port Forwarding

**Last Updated**: December 20, 2025  
**Configuration**: Windscribe Atlanta Static IP with Port Forwarding

---

## 📋 Overview

This guide configures SSH access to your Mac through **Windscribe's port forwarding** feature, allowing secure remote SSH access from anywhere.

### **Your Configuration:**
- **Atlanta Static IP**: `82.21.151.194`
- **External Port**: `36555` (Windscribe port forward)
- **Internal Port**: `22` (SSH daemon)
- **Protocol**: TCP

---

## 🚀 Quick Start

### **Test SSH Connection (Remote Access)**

From another device (phone, laptop, etc.):

```bash
# Using the cursor-vpn alias
ssh cursor-vpn

# Or directly
ssh -p 36555 abhimehrotra@82.21.151.194
```

**Requirements:**
- ✅ Mac has Windscribe VPN connected to **Atlanta**
- ✅ SSH daemon is running on your Mac
- ✅ Port forward `36555 → 22` is configured in Windscribe

---

## 🔧 SSH Configuration

Your SSH config now includes:

### **cursor-vpn** (Remote Access via Windscribe)
```ssh
Host cursor-vpn
    HostName 82.21.151.194
    Port 36555
    User abhimehrotra
```

Use this when:
- ✅ You're away from home
- ✅ Mac has Windscribe connected to Atlanta
- ✅ You want encrypted SSH through VPN tunnel

---

### **cursor-local** (Local Network)
```ssh
Host cursor-local
    HostName abhis-macbook-air.local
    Port 22
    User abhimehrotra
```

Use this when:
- ✅ You're on the same WiFi network
- ✅ Fastest performance (no VPN overhead)
- ✅ VPN is on or off (with "Allow LAN Traffic")

---

## 🧪 Testing Your Setup

### **Test 1: Verify SSH Daemon is Running**

On your Mac:
```bash
# Check if SSH is enabled
sudo systemsetup -getremotelogin

# Should show: Remote Login: On

# If not, enable it:
sudo systemsetup -setremotelogin on
```

---

### **Test 2: Test Local Access First**

From your Mac:
```bash
# Test localhost
ssh -p 22 abhimehrotra@localhost

# Test via .local domain
ssh cursor-local
```

**Expected**: Should connect successfully

---

### **Test 3: Test Remote Access (VPN Required)**

**Prerequisites:**
1. Mac has Windscribe VPN connected to **Atlanta**
2. SSH daemon is running
3. Port forward `36555 → 22` is active

**From another device (phone, laptop):**
```bash
# Test the connection
ssh -p 36555 abhimehrotra@82.21.151.194

# Or use the alias
ssh cursor-vpn
```

**Expected**: Should connect successfully

---

### **Test 4: Verify Port Forwarding is Active**

From remote device:
```bash
# Check if port is open
nc -zv 82.21.151.194 36555

# Expected output:
# Connection to 82.21.151.194 port 36555 [tcp/*] succeeded!
```

---

## 🔍 Troubleshooting

### ❌ **Connection Refused (Remote Access)**

**Symptoms:**
```
ssh: connect to host 82.21.151.194 port 36555: Connection refused
```

**Diagnosis:**
```bash
# 1. Check if VPN is connected to Atlanta
curl -s ifconfig.me
# Should show: 82.21.151.194

# 2. Check if SSH is running
sudo systemsetup -getremotelogin
# Should show: Remote Login: On

# 3. Check if port 22 is listening
lsof -nP -i:22 | grep LISTEN
# Should show: sshd listening
```

**Solutions:**
1. **VPN not connected**: Connect Windscribe to Atlanta server
2. **SSH disabled**: `sudo systemsetup -setremotelogin on`
3. **Firewall blocking**: Check macOS Firewall settings
4. **Wrong port**: Verify Windscribe port forward is `36555 → 22`

---

### ❌ **Connection Times Out**

**Symptoms:**
```
ssh: connect to host 82.21.151.194 port 36555: Operation timed out
```

**Common Causes:**
1. **Mac VPN disconnected**: Reconnect to Windscribe Atlanta
2. **Port forward not active**: Verify in Windscribe dashboard
3. **Mac is asleep**: Wake your Mac or disable sleep
4. **Firewall**: Check macOS Firewall allows SSH

**Fix:**
```bash
# Verify public IP matches Atlanta
curl -s ifconfig.me
# Must be: 82.21.151.194

# Verify port forward in Windscribe settings
# External: 36555 → Internal: 22 (TCP)
```

---

### ❌ **"Permission Denied (publickey)"**

**Symptoms:**
```
abhimehrotra@82.21.151.194: Permission denied (publickey)
```

**Solutions:**

1. **Verify 1Password SSH agent is running:**
```bash
# Check if agent socket exists
ls -la ~/Library/Group\ Containers/2BUA8C4S2C.com.1password/t/agent.sock

# Test 1Password CLI
op account list
```

2. **Check SSH keys in 1Password:**
- Open 1Password
- Go to SSH keys section
- Verify your key is present and accessible

3. **Test with verbose output:**
```bash
ssh -vvv cursor-vpn
# Look for "1Password" in the output
```

---

### ❌ **Local Access Works, Remote Doesn't**

**This confirms:**
- ✅ SSH daemon is working
- ✅ Your SSH keys are correct
- ❌ Port forwarding issue

**Fix:**
```bash
# 1. Verify you're connected to Atlanta
curl -s ifconfig.me
# Must show: 82.21.151.194

# 2. Verify Windscribe port forward configuration:
# - External Port: 36555
# - Internal Port: 22
# - Device: MacBook Air
# - Protocol: TCP

# 3. Try restarting Windscribe
# Disconnect → Reconnect to Atlanta
```

---

## 🎯 **Best Practices**

### **For Remote Access:**

1. **Keep Mac awake** when you need remote access:
```bash
# Prevent sleep while plugged in
sudo pmset -c sleep 0
sudo pmset -c displaysleep 10

# Or use caffeinate to keep awake temporarily
caffeinate -d
```

2. **Auto-connect Windscribe on startup:**
- Windscribe Preferences → General → Launch on Startup
- Windscribe Preferences → General → Connect on Launch
- Connection tab → Set "Best Location" to **Atlanta**

3. **Monitor VPN connection:**
```bash
# Add to Fish config for status check
function vpn-status
    set PUBLIC_IP (curl -s ifconfig.me)
    if test "$PUBLIC_IP" = "82.21.151.194"
        echo "✅ VPN: Connected to Atlanta"
    else
        echo "❌ VPN: Not connected or wrong server"
        echo "   Current IP: $PUBLIC_IP"
    end
end
```

---

### **Security Recommendations:**

1. **Use strong SSH keys** (Ed25519):
```bash
# Generate new key (if needed)
ssh-keygen -t ed25519 -C "your-email@example.com"

# Add to 1Password
# 1Password app → SSH Keys → Add Private Key
```

2. **Keep port 36555 secret:**
- Don't share your Windscribe port forward details publicly
- It's only accessible when VPN is on, but security by obscurity helps

3. **Monitor SSH access:**
```bash
# View recent SSH logins
last | grep abhimehrotra

# View failed login attempts
sudo grep "Failed password" /var/log/system.log
```

---

## 📊 **Connection Matrix**

| Your Location | Mac Location | VPN Status | SSH Command | Notes |
|--------------|--------------|-----------|-------------|-------|
| Home WiFi | Home | OFF | `ssh cursor-local` | Fastest |
| Home WiFi | Home | ON | `ssh cursor-local` | Still fast with "Allow LAN Traffic" |
| Away | Home | Mac VPN ON | `ssh cursor-vpn` | Requires Mac VPN connected |
| Away | Away | Both ON | `ssh cursor-local` or `cursor-vpn` | Both work |

---

## 🔄 **Quick Commands**

```bash
# Connect via VPN (remote)
ssh cursor-vpn

# Connect via local network
ssh cursor-local

# Test VPN connection
curl -s ifconfig.me
# Should show: 82.21.151.194

# Check SSH daemon
sudo systemsetup -getremotelogin

# Enable SSH daemon
sudo systemsetup -setremotelogin on

# Test port forwarding
nc -zv 82.21.151.194 36555
```

---

## 🎓 **Understanding the Setup**

### **How Port Forwarding Works:**

```
[Remote Device]
    ↓
[Internet]
    ↓
[Windscribe VPN Server - Atlanta 82.21.151.194:36555]
    ↓
[Encrypted VPN Tunnel]
    ↓
[Your Mac - Port 22 SSH]
```

### **Why This is Better Than Router Port Forwarding:**

1. **Works from any location**: Mac doesn't need to be on home network
2. **More secure**: Traffic encrypted through VPN tunnel
3. **No router configuration**: Windscribe handles port forwarding
4. **Static IP included**: 82.21.151.194 is always yours
5. **Easy to disable**: Just disconnect VPN

---

## ✅ **Verification Checklist**

After setup, verify everything works:

- [ ] SSH daemon is enabled on Mac
- [ ] Windscribe VPN connected to Atlanta (82.21.151.194)
- [ ] Port forward `36555 → 22` configured in Windscribe
- [ ] "Allow LAN Traffic" enabled in Windscribe
- [ ] Local access works: `ssh cursor-local`
- [ ] Remote access works: `ssh cursor-vpn`
- [ ] 1Password SSH agent is working
- [ ] SSH keys are in 1Password

---

**🎉 Your SSH is now accessible remotely through Windscribe VPN!**

_Last tested: December 20, 2025 - ✅ Successful remote SSH via port forward_
