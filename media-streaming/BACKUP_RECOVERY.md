# 🔐 Media Streaming Backup & Recovery Guide

**Last Updated**: December 20, 2025  
**Recovery Time**: ~5 minutes

---

## 📦 What's Backed Up

| Component | Location | Type |
|-----------|----------|------|
| **rclone config** | 1Password → "Rclone Config Backup" | Secure vault |
| **WebDAV credentials** | 1Password → "Media Server WebDAV Credentials" | Secure vault |
| **Setup scripts** | `media-streaming/scripts/` | Git repository |
| **Documentation** | `media-streaming/docs/` | Git repository |

---

## 🚨 When to Use This Guide

Use this recovery process when:
- ✅ Moving to a new Mac
- ✅ After system reinstall or migration
- ✅ If cloud sync (OneDrive/iCloud) corrupts config files
- ✅ After accidental deletion of `~/.config/rclone/`
- ✅ When media server stops working after system update

---

## 🔧 Complete Recovery Process

### Step 1: Restore rclone Configuration

```bash
# Ensure config directory exists
mkdir -p ~/.config/rclone

# Restore from 1Password
op document get "Rclone Config Backup" --vault Personal \
  --output ~/.config/rclone/rclone.conf

# Set proper permissions
chmod 600 ~/.config/rclone/rclone.conf

# Verify remotes are accessible
rclone listremotes
# Expected output: gdrive:, onedrive:, media:
```

---

### Step 2: Restore WebDAV Credentials

```bash
# Create credentials directory
mkdir -p ~/.config/media-server

# Restore from 1Password
op document get "Media Server WebDAV Credentials" --vault Personal \
  --output ~/.config/media-server/credentials

# Set proper permissions
chmod 600 ~/.config/media-server/credentials

# Verify credentials were restored
cat ~/.config/media-server/credentials
# Should show: MEDIA_WEBDAV_USER and MEDIA_WEBDAV_PASS
```

---

### Step 3: Test Cloud Connections

```bash
# Test Google Drive
rclone about gdrive:

# Test OneDrive
rclone about onedrive:

# Test union remote
rclone lsd media:
# Should list: Movies, TV Shows, Documentaries, Kids, Music, 4K
```

---

### Step 4: Start Media Server

```bash
# Start WebDAV server
~/Documents/dev/personal-config/media-streaming/scripts/start-media-server.sh

# Verify server is running
lsof -nP -i:8088 | grep rclone

# Test local connection
curl -u infuse:$(grep MEDIA_WEBDAV_PASS ~/.config/media-server/credentials | cut -d"'" -f2) \
     http://localhost:8088/
```

---

### Step 5: Reconnect Infuse

Get your local IP:
```bash
ipconfig getifaddr en0
```

**Infuse Configuration:**
```
Protocol: WebDAV
Address: http://YOUR_LOCAL_IP:8088
Username: infuse
Password: [from credentials file]
Path: /
```

---

## ⚡ Quick Recovery (One Command)

For experienced users, here's a complete one-liner:

```bash
mkdir -p ~/.config/{rclone,media-server} && \
op document get "Rclone Config Backup" --vault Personal --output ~/.config/rclone/rclone.conf && \
chmod 600 ~/.config/rclone/rclone.conf && \
op document get "Media Server WebDAV Credentials" --vault Personal --output ~/.config/media-server/credentials && \
chmod 600 ~/.config/media-server/credentials && \
~/Documents/dev/personal-config/media-streaming/scripts/start-media-server.sh
```

---

## 🔍 Troubleshooting

### Issue: "rclone listremotes" shows nothing

**Solution:**
```bash
# Check if config file exists
ls -la ~/.config/rclone/rclone.conf

# If missing, restore from 1Password (see Step 1)

# Verify config is valid
rclone config show
```

---

### Issue: OAuth tokens expired

**Solution:**
```bash
# Reconnect Google Drive
rclone config reconnect gdrive:

# Reconnect OneDrive
rclone config reconnect onedrive:

# Update backup in 1Password
op document edit "Rclone Config Backup" ~/.config/rclone/rclone.conf --vault Personal
```

---

### Issue: WebDAV server won't start

**Solution:**
```bash
# Kill any existing rclone processes
pkill -9 rclone

# Check if port 8088 is in use
lsof -nP -i:8088

# Restart server
~/Documents/dev/personal-config/media-streaming/scripts/start-media-server.sh
```

---

### Issue: Can't retrieve credentials from 1Password

**Solution:**
```bash
# Check if you're signed in
op account list

# If not signed in
eval $(op signin)

# List all documents to verify names
op document list --vault Personal | grep -i media

# Retrieve with exact title
op document get "Rclone Config Backup" --vault Personal
op document get "Media Server WebDAV Credentials" --vault Personal
```

---

## 🔄 Updating Backups

### After OAuth Token Refresh:
```bash
# Update rclone config in 1Password
op document edit "Rclone Config Backup" ~/.config/rclone/rclone.conf --vault Personal
```

### After Changing WebDAV Password:
```bash
# Update credentials in 1Password
op document edit "Media Server WebDAV Credentials" ~/.config/media-server/credentials --vault Personal
```

---

## 📊 Verification Checklist

After recovery, verify everything works:

- [ ] `rclone listremotes` shows: gdrive:, onedrive:, media:
- [ ] `rclone lsd media:` shows folder structure
- [ ] `lsof -nP -i:8088` shows rclone listening
- [ ] `curl http://localhost:8088/` returns authentication prompt
- [ ] Infuse can browse media library
- [ ] Can play a test video in Infuse

---

## 🛡️ Prevention: Protect Against Future Issues

### Exclude from Cloud Sync

Add these to **OneDrive/iCloud exclusions**:
```
~/.config/rclone/
~/.config/media-server/
~/Library/Application Support/MediaCache/
```

### Regular Backup Schedule

Update 1Password backups monthly or after major changes:
```bash
# Update both backups
op document edit "Rclone Config Backup" ~/.config/rclone/rclone.conf --vault Personal
op document edit "Media Server WebDAV Credentials" ~/.config/media-server/credentials --vault Personal
```

---

## 📞 Additional Resources

- **Setup Guide**: `media-streaming/README.md`
- **Troubleshooting**: `media-streaming/docs/troubleshooting.md`
- **Scripts**: `media-streaming/scripts/`
- **Alldebrid Setup**: `media-streaming/docs/alldebrid-troubleshooting.md`

---

## 🎯 1Password Backup Locations

All sensitive configurations are stored in your **Personal vault**:

| Document Name | Contains | UUID |
|--------------|----------|------|
| **Rclone Config Backup** | OAuth tokens, remote configs | opgr52y2brbsfmzzk56p4qrkzu |
| **Media Server WebDAV Credentials** | Username & password | mv76o4tmrwg2ure3jyedmlphti |

---

## 🎯 Recovery Success Criteria

You'll know recovery is complete when:
1. ✅ All rclone remotes are accessible
2. ✅ WebDAV server is running on port 8088
3. ✅ Infuse can connect and browse media
4. ✅ Can stream a test video successfully
5. ✅ LaunchAgents are loaded (if applicable)

---

**Recovery Time**: 5-10 minutes  
**Difficulty**: Easy (copy-paste commands)  
**Prerequisites**: 1Password CLI access, git repository cloned

_Last tested: December 20, 2025 - ✅ Successful recovery from OneDrive sync incident_

---

## 🔒 Security Note

**Why everything is in 1Password:**
- GitHub's push protection blocks OAuth tokens in git commits
- 1Password provides encrypted, secure storage for sensitive credentials
- Recovery is just as fast with `op document get` commands
- No risk of accidentally exposing secrets in public repositories
