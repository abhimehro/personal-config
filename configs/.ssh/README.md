# SSH Configuration for Cursor IDE - Complete Setup Guide

## 🎯 Overview
Your SSH configuration now dynamically handles both VPN-connected and local network scenarios for seamless Cursor IDE usage.

## 📋 Configuration Summary

### SSH Hosts Available:
- **`cursor-vpn`** - Use when Windscribe VPN is ON (connects to 100.105.30.135)
- **`cursor-local`** - Use when VPN is OFF (connects to abhis-macbook-air)
- **`cursor-mdns`** - Fallback using Bonjour (connects to Abhis-MacBook-Air.local)
- **`cursor-auto`** - Smart detection (tries local first)

### 1Password Integration:
- ✅ SSH agent properly configured
- ✅ Keys from both "Personal" and "Private" vaults enabled
- ✅ Agent located at: `~/Library/Group Containers/2BUA8C4S2C.com.1password/t/agent.sock`

## 🚀 Quick Start

### For Terminal Use:
```bash
# Make scripts executable
cd ~/.ssh
chmod +x *.sh

# Check all connection methods
./check_connections.sh

# Smart auto-connect
./smart_connect.sh

# Or connect directly:
ssh cursor-local    # When VPN is OFF
ssh cursor-vpn      # When VPN is ON
ssh cursor-mdns     # Fallback method
```

### For Cursor IDE:
1. Open Cursor IDE
2. Install Remote-SSH extension (if not already installed)
3. Press `Cmd+Shift+P` → "Remote-SSH: Connect to Host"
4. Choose one of:
   - **`cursor-local`** (when VPN is off)
   - **`cursor-vpn`** (when VPN is on)
   - **`cursor-mdns`** (fallback)

## 🔧 Setup Scripts

### Available Scripts:
- **`smart_connect.sh`** - Automatically detects and connects using best method
- **`check_connections.sh`** - Tests all connection methods
- **`setup_aliases.sh`** - Creates convenient shell aliases
- **`test_connection.sh`** - Debugging and troubleshooting

## 🌐 Network Scenarios

### Scenario 1: VPN OFF (Local Network)
- **Best option:** `ssh cursor-local`
- **Target:** `abhis-macbook-air`
- **Optimizations:** No compression (local network is fast)

### Scenario 2: VPN ON (Windscribe Connected)
- **Best option:** `ssh cursor-vpn`  
- **Target:** `100.105.30.135`
- **Optimizations:** Compression enabled, extra keepalives

### Scenario 3: mDNS/Bonjour Fallback
- **Fallback option:** `ssh cursor-mdns`
- **Target:** `Abhis-MacBook-Air.local`
- **Use when:** Hostname resolution fails

## 🛠 Troubleshooting

### If connections fail:
1. **Check network status:**
   ```bash
   ./check_connections.sh
   ```

2. **Verify SSH is enabled on target machine:**
   - System Preferences → Sharing → Remote Login ✅

3. **Test basic connectivity:**
   ```bash
   ping abhis-macbook-air
   ping Abhis-MacBook-Air.local
   ```

4. **Check 1Password SSH agent:**
   ```bash
   ssh-add -l
   ```

### Common Issues:
- **Host key verification failed:** Fixed with `StrictHostKeyChecking accept-new`
- **VPN routing issues:** Use appropriate host (`cursor-vpn` vs `cursor-local`)
- **Timeout errors:** Adjust `ConnectTimeout` in config if needed

## 🎉 Cursor IDE Integration

### Setting up in Cursor:
1. **Install Remote-SSH extension**
2. **Add SSH targets:**
   - Primary: `cursor-local` or `cursor-vpn`
   - Backup: `cursor-mdns`
3. **Connection will automatically:**
   - Use 1Password for authentication
   - Maintain persistent connections
   - Optimize for IDE usage

### Pro Tips:
- Use `cursor-local` as default in Cursor IDE
- If connection fails, try `cursor-vpn` (when VPN is on)
- Connection multiplexing keeps sessions fast
- 30-minute persist time for stable IDE experience

## 📁 File Locations
- **SSH Config:** `~/.ssh/config`
- **1Password Agent:** `~/.ssh/agent.toml`
- **Scripts:** `~/.ssh/*.sh`
- **Known Hosts:** `~/.ssh/known_hosts`

---

**Status:** ✅ Ready for use with both terminal and Cursor IDE!