# 🔧 Alldebrid + Infuse Troubleshooting Guide

## ✅ **Your Confirmed Working Setup**
- **Server**: `webdav.debrid.it`
- **Port**: `443` 
- **Username**: `ZuoByo8HrnujRsDzae6s`
- **Password**: `eeeee`
- **HTTPS**: ✅ Enabled
- **Path**: `/links/`

We've confirmed these credentials work perfectly from your Mac via curl.

## 🔍 **If Infuse Still Shows "Unable to Connect"**

### **Quick Fixes:**
1. **Try again** - Temporary network issues are common
2. **Leave Path blank** initially, then add `/links/` later
3. **Check VPN** - Temporarily disable Proton VPN to test
4. **Restart Infuse** completely
5. **Check device network** - Ensure same WiFi network

### **Alternative: Use rclone WebDAV Server**
If direct connection keeps failing, use our backup method:

```bash
# Start the rclone server we set up earlier
~/start-alldebrid.sh
```

Then in Infuse:
- **Address**: `http://YOUR_MAC_IP:8080`
- **Username**: Leave blank
- **Password**: Leave blank

## 🎯 **Pro Tips**

### **Folder Organization**
When Alldebrid connection works, organize like this:
```
/links/
├── Movies/
│   └── The Matrix (1999).mkv
├── TV Shows/
│   └── Breaking Bad/
│       └── Season 01/
│           └── Breaking Bad S01E01.mkv
└── Documentaries/
    └── Planet Earth (2006).mkv
```

### **Performance Settings**
- Enable "Pre-Cache Details" ✅
- Enable "Pre-Cache Artwork" ✅  
- Enable "Smart Folders" ✅
- Auto Scan: ✅ ON

### **Your Network Details**
- **VPN**: Proton VPN (port forwarding enabled but not needed for outbound connections)
- **DNS**: Default Proton DNS
- **Firewall**: Check macOS firewall if local rclone method needed

## 🚨 **Common Issues**

**"Authentication Failed"** 
→ Double-check username/password (no extra spaces)

**"Server Unreachable"**
→ Check VPN settings or try without VPN temporarily  

**"Timeout"**
→ Try different WiFi network or mobile hotspot

**Empty Folder in Infuse**
→ Content might not be in `/links/` yet - check Alldebrid web interface

Your Mac can definitely reach the Alldebrid server, so this should work!