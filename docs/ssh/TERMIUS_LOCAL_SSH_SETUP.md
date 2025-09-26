# Termius Remote SSH Connection Setup

## 🎯 Issue: Connection Refused Error

**Problem**: Getting "connection refused" when trying to SSH to MacBook Air
**Root Cause**: SSH server (Remote Login) is not enabled on the target MacBook

## ✅ Solution Steps

### Step 1: Enable SSH Server on MacBook Air
1. **Open System Preferences** (or System Settings on macOS Ventura+)
2. **Navigate to Sharing**
3. **Enable "Remote Login"** ✅
4. **Configure Access**:
   - Select "Only these users" and add your user account
   - Or select "All users" for broader access

### Step 2: Verify SSH Server is Running
```bash
pgrep -f sshd
# Should return process IDs if SSH server is active
```

### Step 3: Test Local SSH Connection
```bash
ssh abhimehrotra@MacBook-Air.local
# Should connect successfully or prompt for authentication
```

## 🎨 Termius Configuration

### Connection Settings for MacBook Air:
```
Name: MacBook Air Local
Hostname: MacBook-Air.local
Port: 22
Username: abhimehrotra
Authentication: SSH Key
SSH Key: ED25519 key (same as GitHub)
```

### Alternative Connection Methods:
1. **mDNS (Recommended)**: `MacBook-Air.local`
2. **Localhost**: `localhost` (same machine only)
3. **IP Address**: Find with `ifconfig | grep "inet "`

## 🔍 Troubleshooting

### Common Issues:

**1. "Connection Refused"**
- ❌ SSH server not enabled
- ✅ Enable Remote Login in System Preferences → Sharing

**2. "Permission Denied"**
- ❌ SSH key not configured or username incorrect
- ✅ Verify username matches macOS user account
- ✅ Import SSH key to Termius

**3. "Host Not Found"**
- ❌ Hostname resolution issues
- ✅ Try `MacBook-Air.local` instead of `MacBook-Air`
- ✅ Use IP address as alternative

### Verification Commands:
```bash
# Check SSH server status
pgrep -f sshd

# Test connection
ssh abhimehrotra@MacBook-Air.local

# Find local IP addresses
ifconfig | grep "inet " | grep -v 127.0.0.1
```

## 🌐 Network Scenarios

### Local Network Connection
- **Best**: `ssh abhimehrotra@MacBook-Air.local`
- **Alternative**: `ssh abhimehrotra@[IP-ADDRESS]`

### Same Machine Connection
- **Use**: `ssh abhimehrotra@localhost`
- **Port**: Default 22

### Remote Network Connection
- **Requires**: VPN or port forwarding setup
- **Security**: Ensure firewall is properly configured

## 🔐 Security Best Practices

### SSH Key Authentication
- **Use**: Same ED25519 key for both GitHub and local connections
- **Benefits**: No password required, more secure

### Firewall Configuration
- **macOS Firewall**: May need to allow SSH connections
- **Router**: Configure port forwarding if accessing remotely

### User Access Control
- **Limit**: Use "Only these users" in Remote Login settings
- **Monitor**: Check SSH logs for unauthorized access attempts

## ✅ Success Verification

After completing setup:

1. **SSH Server Running**: `pgrep -f sshd` returns process IDs
2. **Local Connection**: `ssh abhimehrotra@MacBook-Air.local` works
3. **Termius Connection**: Successfully connects without errors
4. **Authentication**: Uses SSH key without password prompt

## 📝 Notes

- **GitHub SSH vs Local SSH**: Different purposes
  - GitHub: Git operations only (no shell access)
  - Local: Full shell access to your MacBook
- **Same SSH Key**: Can be used for both GitHub and local connections
- **mDNS**: `.local` suffix enables Bonjour/mDNS resolution

---

**Status**: Ready for testing after enabling Remote Login  
**Next Step**: Enable Remote Login in System Preferences → Sharing