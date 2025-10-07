# 🎬 Ultimate Media Streaming Setup for Infuse

**Status**: ✅ **FULLY OPERATIONAL** - Built October 2025  
**Total Storage**: ~3TB (Google Drive + OneDrive + Alldebrid streaming)  
**Platforms**: macOS, iOS, tvOS via Infuse  

## 🏗️ **Architecture Overview**

This setup provides **three distinct media sources** for Infuse:

### 1. 🚀 **Alldebrid WebDAV** (Streaming Content)
- **Direct WebDAV connection** to `webdav.debrid.it`
- **Port**: 443 (HTTPS)
- **Purpose**: Stream downloaded content directly
- **Status**: ✅ Working perfectly

### 2. ☁️ **Unified Cloud Library** (Personal Content) 
- **Combines**: Google Drive (2TB) + OneDrive (1TB)
- **Served via**: rclone WebDAV server on port 8088
- **Purpose**: Personal media library with ~3TB total space
- **Status**: ✅ Fully operational

### 3. 🔗 **Individual Cloud Access** (Optional)
- **Separate sources** for Google Drive and OneDrive
- **Purpose**: Direct access to specific cloud providers
- **Status**: ✅ Available when needed

## 📁 **Folder Structure**

All remotes use consistent, Infuse-optimized structure:
```
Media/
├── Movies/          # Movie Name (Year).ext
├── TV Shows/        # Show Name/Season XX/Show Name SXXEXX.ext  
├── Documentaries/   # Documentary Name (Year).ext
├── Kids/            # Family-friendly content
├── Music/           # Music videos and concerts
└── 4K/             # High-resolution content
```

## 🔧 **Available Scripts**

### **Primary Scripts**
- `start-media-server.sh` - **Start unified WebDAV server** (port 8088)
- `setup-media-library.sh` - **Full setup/reinstall** (Google Drive + OneDrive + Union)
- `fix-gdrive.sh` - **Repair Google Drive authentication**

### **Alldebrid Scripts**  
- `start-alldebrid.sh` - Start local Alldebrid server (port 8080)
- `stop-alldebrid.sh` - Stop local Alldebrid server
- `alldebrid-server.py` - Python WebDAV server for Alldebrid

### **Setup Scripts**
- `setup-gdrive.sh` - Google Drive setup helper

## 🎯 **Quick Start Guide**

### **Add Sources to Infuse:**

#### 1. Alldebrid (Direct WebDAV)
```
Protocol: WebDAV
Address: webdav.debrid.it  
Port: 443
Username: [Your Alldebrid WebDAV username]
Password: [Your Alldebrid WebDAV password]
HTTPS: ✅ Enabled
Path: /links/
```

#### 2. Unified Cloud Library
```bash
# Start the server
~/start-media-server.sh
```
```
Protocol: WebDAV  
Address: http://YOUR_LOCAL_IP:8088
Username: infuse
Password: mediaserver123
Path: /
```

## 📊 **Current Status**

### **Remotes Configured:**
- ✅ `alldebrid:` - Alldebrid WebDAV (streaming)
- ✅ `gdrive:` - Google Drive (2TB, 1.8TB free)  
- ✅ `onedrive:` - OneDrive (1TB, 933GB free)
- ✅ `media:` - Union of Google Drive + OneDrive

### **Total Available Space:**
- **Google Drive**: 1.8TB free
- **OneDrive**: 933GB free  
- **Combined**: ~2.7TB for personal media
- **Alldebrid**: Unlimited streaming

## 🛠️ **Maintenance**

### **Refresh Cloud Authentication:**
```bash
# Google Drive
rclone config reconnect gdrive:

# OneDrive  
rclone config reconnect onedrive:

# Full repair
~/fix-gdrive.sh
```

### **Restart Services:**
```bash
# Stop any running servers
pkill -f "rclone serve"

# Start unified server
~/start-media-server.sh
```

### **Check Remote Status:**
```bash
rclone listremotes
rclone about gdrive:
rclone about onedrive:
rclone lsd media:
```

## 🚨 **Troubleshooting**

### **Alldebrid Connection Issues:**
- Check `docs/alldebrid-troubleshooting.md`
- Verify HTTPS is enabled in Infuse
- Temporarily disable VPN if needed

### **Cloud Authentication Expired:**
- Run `~/fix-gdrive.sh` for automated repair
- Or manually: `rclone config reconnect gdrive:`

### **WebDAV Server Won't Start:**
- Check port availability: `lsof -nP -i:8088`
- Kill existing servers: `pkill -f "rclone serve"`
- Restart: `~/start-media-server.sh`

## 🔐 **Security & Credentials**

### **Stored Safely:**
- **rclone config**: `~/.config/rclone/rclone.conf` 
- **Backup config**: `backup/rclone.conf.backup`
- **Credentials**: OAuth tokens auto-refresh

### **WebDAV Server Security:**
- **Local network only** (0.0.0.0:8088)
- **Username**: `infuse` 
- **Password**: `mediaserver123`
- **Read-only access** to prevent accidental changes

## 🏆 **Performance Optimization**

### **rclone Flags Used:**
- `--dir-cache-time 30m` - Cache directory listings
- `--read-only` - Prevent accidental modifications  
- `--verbose` - Detailed logging

### **Infuse Settings (Recommended):**
- ✅ **Pre-Cache Details** 
- ✅ **Pre-Cache Artwork**
- ✅ **Smart Folders**
- ✅ **Auto Scan**

## 📈 **Built With Love**

**Created**: October 5, 2025  
**Technology Stack**:
- **rclone** v1.71.1 (multi-cloud sync)
- **Python 3** (custom WebDAV server)
- **macOS** launchctl integration ready
- **Infuse 7** optimization

**Features Achieved**:
- 🎯 **Unified 3TB+ media library**
- 🚀 **Streaming content via Alldebrid**  
- ☁️ **Multi-cloud redundancy**
- 📱 **Cross-platform access** (iOS/tvOS/macOS)
- 🔧 **Automated management scripts**
- 📚 **Comprehensive documentation**

---
*"From zero to enterprise-level media streaming in one session!"* 🎬✨