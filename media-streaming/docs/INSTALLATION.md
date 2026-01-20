# 🚀 Installation & Recovery Guide

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
~/start-media-server-fast.sh
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
lsof -nP -i:8088  # Unified server
lsof -nP -i:8080  # Alldebrid server

# Stop all rclone servers
pkill -f "rclone serve"
```

### **Server Logs:**
```bash
# Monitor server output
~/start-media-server-fast.sh  # Shows live logs
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
~/start-media-server-fast.sh

# Get your local IP
ipconfig getifaddr en0
```
```
Protocol: WebDAV
Address: http://YOUR_LOCAL_IP:8088
Username: infuse
Password: [from ~/.config/media-server/credentials]
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
lsof -nP -i:8088  # Check what's using the port
pkill -f "rclone serve"  # Kill existing servers
```

### **Empty Folder in Infuse:**
```bash
# Check if content exists
rclone lsd media:
rclone ls media: | head -10

# Verify server is running
curl -u infuse:"$(grep MEDIA_WEBDAV_PASS ~/.config/media-server/credentials | cut -d"'" -f2)" http://localhost:8088/
```

---
*💡 **Pro Tip**: Keep this documentation in sync with any configuration changes!*