# 

> Note: The daemon reads the local credentials file when present, then uses
> 1Password if the file does not supply both values. 🚀 Installation &
> Recovery Guide

## 📥 **Fresh Installation**

### **Prerequisites:**

```bash
# Install rclone via Homebrew
brew install rclone

# Verify installation
rclone version
```

### **Quick Setup:**

1. **Copy scripts to home directory:**

   ```bash
   cp scripts/* ~/
   chmod +x ~/*.sh
   ```

2. **Run the comprehensive setup:**

   ```bash
   ~/setup-media-library.sh
   ```

3. **Follow the guided prompts for:**
   - Google Drive authorization
   - OneDrive authorization
   - Folder structure creation
   - Union remote setup

## 🔄 **Recovery from Backup**

### **Restore rclone Configuration:**

```bash
# Copy backup config
cp backup/rclone.conf.backup ~/.config/rclone/rclone.conf

# Test remotes
rclone listremotes
rclone about gdrive:
rclone about onedrive:
```

### **Refresh Authentication (if tokens expired):**

```bash
# Automated fix
~/fix-gdrive.sh

# Or manual refresh
rclone config reconnect gdrive:
rclone config reconnect onedrive:
```

## 🔧 **Individual Component Setup**

### **Google Drive Only:**

```bash
~/setup-gdrive.sh
# OR
~/fix-gdrive.sh
```

### **Alldebrid Local Server:**

```bash
~/start-alldebrid.sh  # Start
~/stop-alldebrid.sh   # Stop
```

### **Unified Cloud Server:**

```bash
~/media-server-daemon.sh
```

## 🏥 **Emergency Recovery**

### **Complete Reset:**

```bash
# Remove old config
rm -rf ~/.config/rclone/

# Reinstall from scratch
~/setup-media-library.sh
```

### **Partial Reset (Keep Google Drive):**

```bash
# Delete only OneDrive remote
rclone config delete onedrive

# Re-add OneDrive
~/setup-media-library.sh
```

## 🔍 **Verification Commands**

### **Check All Remotes:**

```bash
for remote in alldebrid gdrive onedrive media; do
  echo "=== $remote ==="
  rclone about $remote: 2>/dev/null || echo "❌ Failed"
  echo
done
```

### **Test Union Remote:**

```bash
rclone lsd media:
rclone tree media: --level 1
```

### **Verify Folder Structure:**

```bash
rclone tree gdrive:Media --level 2
rclone tree onedrive:Media --level 2
```

## 📡 **Server Management**

### **Check Running Servers:**

```bash
# Check what's using our ports
lsof -nP -iTCP:8080 -sTCP:LISTEN  # WebDAV server (stable internal port)

# Stop the WebDAV server
pkill -f "rclone serve webdav"
```

### **Server Logs:**

```bash
# Monitor server output
tail -f ~/Library/Logs/media-server.log  # LaunchAgent log
```

## 🎯 **Infuse Configuration**

### **Add Source - Alldebrid:**

```
Protocol: WebDAV
Address: webdav.debrid.it
Port: 443
HTTPS: ✅ ON
Username: [From backup config]
Password: [From backup config]
Path: /links/
```

### **Add Source - Unified Cloud:**

```bash
# First, start the server
~/media-server-daemon.sh

# Get your local IP
ipconfig getifaddr en0
```

```
Protocol: WebDAV
Address: https://YOUR_WEBDAV_HOST:8080
Username: infuse
Password: [1Password MediaServer, or credentials file if it has both values]
Path: /
```

## 🚨 **Common Issues**

### **"Remote not found" Error:**

```bash
rclone listremotes  # Check what exists
~/setup-media-library.sh  # Recreate missing remotes
```

### **Authentication Expired:**

```bash
~/fix-gdrive.sh  # Automated fix
```

### **Port Already in Use:**

```bash
lsof -nP -iTCP:8080 -sTCP:LISTEN  # Check what's using the port
pkill -f "rclone serve webdav"  # Stop the existing WebDAV server
```

### **Empty Folder in Infuse:**

```bash
# Check if content exists
rclone lsd media:
rclone ls media: | head -10

# Verify server is running
curl --resolve YOUR_WEBDAV_HOST:8080:127.0.0.1 \
  -u infuse \
  https://YOUR_WEBDAV_HOST:8080/
```

Enter the current 1Password `MediaServer` password, or the fallback file's
password if configured.

---

_💡 **Pro Tip**: Keep this documentation in sync with any configuration
changes!_
