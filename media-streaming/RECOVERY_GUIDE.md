# Infuse Connection Recovery Guide

## 🔍 Problem Identified

**Root Cause**: Your rclone configuration file (`~/.config/rclone/rclone.conf`) is missing.

This file contains:
- Google Drive OAuth tokens and configuration
- OneDrive OAuth tokens and configuration
- Union remote configuration (combines gdrive + onedrive)
- Alldebrid WebDAV credentials

**Why Infuse Can't Connect:**
1. ❌ No rclone remotes configured → Can't access cloud storage
2. ❌ No union remote → Can't combine Google Drive + OneDrive
3. ❌ No WebDAV server → Infuse has nothing to connect to

## ✅ Solution: Reconfigure rclone

### Quick Recovery (Recommended)

Run the automated setup script:

```bash
cd ~/Documents/dev/personal-config
./media-streaming/scripts/setup-media-library.sh
```

This will guide you through:
1. **Google Drive setup** - Authorize in browser
2. **OneDrive setup** - Authorize in browser
3. **Folder structure** - Creates Media folders on both
4. **Union remote** - Combines both into "media:" remote
5. **WebDAV server** - Creates startup script

### Step-by-Step Manual Recovery

If you prefer manual setup:

#### 1. Configure Google Drive
```bash
rclone config
# Choose: n (new remote)
# Name: gdrive
# Storage: drive (Google Drive)
# Leave client_id/client_secret blank (press Enter)
# Scope: 1 (full access)
# Leave root_folder_id blank
# Service account: n
# Auto config: y (opens browser)
# Complete authorization in browser
# Team drive: n
# Save: y
```

#### 2. Configure OneDrive
```bash
rclone config
# Choose: n (new remote)
# Name: onedrive
# Storage: onedrive
# Leave client_id/client_secret blank
# Auto config: y (opens browser)
# Complete Microsoft authorization
# Account type: personal (or business)
# Save: y
```

#### 3. Create Folder Structure
```bash
# Create Media folder on Google Drive
rclone mkdir gdrive:Media

# Create Media folder on OneDrive
rclone mkdir onedrive:Media

# Create subfolders (optional, but recommended)
for folder in "Movies" "TV Shows" "Documentaries" "Kids" "Music" "4K"; do
    rclone mkdir "gdrive:Media/$folder"
    rclone mkdir "onedrive:Media/$folder"
done
```

#### 4. Create Union Remote (Critical!)
```bash
rclone config
# Choose: n (new remote)
# Name: media
# Storage: union
# Upstreams: gdrive:Media onedrive:Media
# Action policy: epall (or press Enter for default)
# Create policy: epmfs (or press Enter for default)
# Search policy: ff (or press Enter for default)
# Save: y
```

**Important**: The union remote combines both cloud providers. Make sure:
- Both `gdrive:Media` and `onedrive:Media` folders exist
- Folder structures match (or union will show empty)
- Both remotes are working (`rclone about gdrive:` and `rclone about onedrive:`)

#### 5. Verify Setup
```bash
# List all remotes
rclone listremotes

# Test Google Drive
rclone lsd gdrive:Media

# Test OneDrive
rclone lsd onedrive:Media

# Test union remote (this is what Infuse uses)
rclone lsd media:
```

#### 6. Start WebDAV Server
```bash
cd ~/Documents/dev/personal-config
./media-streaming/scripts/start-media-server.sh
```

Or manually:
```bash
rclone serve webdav media: \
    --addr 0.0.0.0:8088 \
    --user infuse \
    --pass mediaserver123 \
    --read-only \
    --verbose
```

#### 7. Configure Infuse

Get your local IP:
```bash
ipconfig getifaddr en0
# or
ipconfig getifaddr en5
```

In Infuse, add WebDAV source:
```
Protocol: WebDAV
Address: http://YOUR_LOCAL_IP:8088
Username: infuse
Password: mediaserver123
Path: /
```

## 🔧 Troubleshooting

### "Folder structure doesn't match"

If you see folders in Google Drive but not in the union:

1. **Check folder paths match exactly:**
   ```bash
   rclone lsd gdrive:Media
   rclone lsd onedrive:Media
   ```

2. **Both should have identical structure:**
   ```
   Media/
   ├── Movies/
   ├── TV Shows/
   ├── Documentaries/
   ├── Kids/
   ├── Music/
   └── 4K/
   ```

3. **If structures differ, union will only show what exists in BOTH:**
   - Union shows files/folders that exist in at least one upstream
   - But folder structure should match for best results

### "Union remote shows empty"

**Common causes:**
1. **Folder paths don't match** - Check both `gdrive:Media` and `onedrive:Media` exist
2. **One remote not working** - Test with `rclone about gdrive:` and `rclone about onedrive:`
3. **Union misconfigured** - Check with `rclone config show media`

**Fix:**
```bash
# Verify union configuration
rclone config show media

# Should show:
# [media]
# type = union
# upstreams = gdrive:Media onedrive:Media

# If wrong, recreate:
rclone config delete media
rclone config  # Create new union remote
```

### "Authentication expired"

If remotes stop working:

```bash
# Reconnect Google Drive
rclone config reconnect gdrive:

# Reconnect OneDrive
rclone config reconnect onedrive:

# Or use automated fix
./media-streaming/scripts/fix-gdrive.sh
```

### "WebDAV server won't start"

```bash
# Check if port is in use
lsof -nP -i:8088

# Kill existing servers
pkill -f "rclone serve"

# Try different port
rclone serve webdav media: --addr 0.0.0.0:8089 --user infuse --pass mediaserver123 --read-only
```

## 📋 Verification Checklist

After setup, verify everything:

- [ ] `rclone listremotes` shows: `gdrive:`, `onedrive:`, `media:`
- [ ] `rclone about gdrive:` works
- [ ] `rclone about onedrive:` works
- [ ] `rclone lsd gdrive:Media` shows folders
- [ ] `rclone lsd onedrive:Media` shows folders
- [ ] `rclone lsd media:` shows folders (union)
- [ ] WebDAV server running: `lsof -nP -i:8088 | grep rclone`
- [ ] Local test works: `curl -u infuse:mediaserver123 http://localhost:8088/`
- [ ] Infuse can connect and see folders

## 🎯 Quick Diagnostic

Run the diagnostic script anytime:

```bash
cd ~/Documents/dev/personal-config
./media-streaming/scripts/diagnose-infuse-connection.sh
```

This will check all components and tell you exactly what's wrong.

## 💡 Important Notes

1. **Folder Structure Must Match**: For the union to work properly, both Google Drive and OneDrive should have the same folder structure under `Media/`

2. **Union Policies**:
   - `action_policy = epall` - Shows files from all upstreams
   - `create_policy = epmfs` - Creates files in upstream with most free space
   - `search_policy = ff` - Searches first upstream first

3. **OAuth Tokens**: These are stored in `~/.config/rclone/rclone.conf` and auto-refresh. If they expire, use `rclone config reconnect`

4. **Backup Your Config**: After setup, backup your config:
   ```bash
   cp ~/.config/rclone/rclone.conf ~/Documents/dev/personal-config/media-streaming/configs/rclone.conf.backup
   ```

---

**Next Steps**: Run `./media-streaming/scripts/setup-media-library.sh` to restore your configuration!
