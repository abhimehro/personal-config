# Complete Mac Factory Reset Guide

## 🎯 Goal
Complete factory reset to eliminate ALL configurations, launch daemons, old files, and start completely fresh.

## 📦 Step 1: Essential Data Backup

### What to Backup (Essentials Only)
- **Documents** - Important files, projects, papers
- **Desktop files** - Current working files  
- **Photos** - Personal photos (if not in iCloud)
- **Downloads** - Recent important downloads
- **SSH Keys** - For GitHub/Git access
- **Browser Bookmarks** - Export from Safari/Chrome
- **Application Data** - Only critical app data

### What NOT to Backup (Clean Slate)
- ❌ Application preferences/settings
- ❌ Launch daemons or system configurations  
- ❌ Cache files or temporary data
- ❌ Old downloads or installer files
- ❌ System preferences or customizations
- ❌ Any VPN/DNS related files

## 🔄 Quick Backup Script

```bash
# Create backup directory
mkdir -p ~/Desktop/ESSENTIAL_BACKUP

# Documents and important files
cp -R ~/Documents ~/Desktop/ESSENTIAL_BACKUP/
cp -R ~/Desktop ~/Desktop/ESSENTIAL_BACKUP/Desktop_Files
cp -R ~/Downloads ~/Desktop/ESSENTIAL_BACKUP/ 2>/dev/null || true

# SSH keys (if they exist)
cp -R ~/.ssh ~/Desktop/ESSENTIAL_BACKUP/ 2>/dev/null || true

# Git config (if you use Git)
cp ~/.gitconfig ~/Desktop/ESSENTIAL_BACKUP/ 2>/dev/null || true

# Export Safari bookmarks manually:
# Safari → File → Export Bookmarks → Save to ESSENTIAL_BACKUP

echo "✅ Essential backup complete in ~/Desktop/ESSENTIAL_BACKUP"
echo "📝 Don't forget to export browser bookmarks manually!"
```

## 💾 Backup Storage Options

### Option 1: External Drive (Recommended)
- Copy `~/Desktop/ESSENTIAL_BACKUP` to external drive
- Verify files are accessible
- Safely eject drive

### Option 2: Cloud Storage  
- Upload to OneDrive, Google Drive, or iCloud Drive
- Wait for complete sync before proceeding

### Option 3: Another Mac/Computer
- AirDrop or network transfer to another device

## 🔒 Step 2: Sign Out of Everything

Before factory reset:

1. **Sign out of iCloud**:
   - System Preferences → Apple ID → Sign Out
   - Choose to keep or remove data from Mac

2. **Sign out of iTunes/App Store**:
   - iTunes → Account → Sign Out
   - App Store → Store → Sign Out

3. **Deauthorize Mac**:
   - iTunes → Account → Authorizations → Deauthorize This Computer

4. **Sign out of other accounts**:
   - Google, Microsoft, Dropbox, etc.

## 🏭 Step 3: Factory Reset Process

### Method 1: Erase Mac (macOS Monterey+)
1. **Apple Menu → System Settings**
2. **General → Transfer or Reset**  
3. **Erase All Content and Settings**
4. **Follow prompts to complete reset**

### Method 2: Recovery Mode (All macOS versions)
1. **Restart Mac and hold Command + R** during startup
2. **Wait for Recovery Mode to load**
3. **Open Disk Utility**
4. **Select your startup disk (usually "Macintosh HD")**
5. **Click Erase**
6. **Choose format: APFS (recommended)**
7. **Click Erase and confirm**
8. **Close Disk Utility**
9. **Select "Reinstall macOS"**
10. **Follow setup instructions**

## 🆕 Step 4: Fresh Setup

### Initial Setup
- **Create new user account** (can use same name)
- **Skip data migration** for completely clean start
- **Sign into Apple ID** when prompted
- **Set up basic preferences** only

### Essential Apps to Reinstall
- **Web browser** of choice
- **Basic productivity apps**
- **Only install what you actually need**

### Restore Your Data
1. **Connect backup drive or download from cloud**
2. **Copy essential files to appropriate locations**:
   - Documents → ~/Documents
   - Desktop files → ~/Desktop  
   - SSH keys → ~/.ssh (set permissions: `chmod 600 ~/.ssh/*`)
3. **Import browser bookmarks**
4. **Reinstall only essential applications**

## ✅ Benefits of Fresh Start

After factory reset:
- **No conflicting launch daemons**
- **No old configurations causing issues**
- **Fast, clean system performance**
- **Only the software you actually need**
- **No VPN/DNS complexity unless you choose it**
- **Fresh macOS with latest updates**

## 🎯 Post-Reset Philosophy

### Keep It Simple
- **Install only what you need** when you need it
- **Avoid complex system modifications**
- **Use built-in macOS features when possible**
- **Browser-based solutions** over system-level ones

### If You Want Privacy Later
- **Start with browser extensions** (uBlock Origin)
- **Use simple DNS changes** if needed
- **Choose one VPN** and let it handle everything
- **Avoid multiple overlapping privacy tools**

## 🚨 Pre-Reset Checklist

Before proceeding, ensure you have:

- [ ] **Backed up all essential data**
- [ ] **Verified backup is accessible**
- [ ] **Exported browser bookmarks**  
- [ ] **Noted down important passwords** (use password manager)
- [ ] **Signed out of all accounts**
- [ ] **Deauthorized Mac from iTunes**
- [ ] **Confirmed you're ready for complete fresh start**

## ⚡ Quick Backup Command

Run this to backup essentials:

```bash
mkdir -p ~/Desktop/ESSENTIAL_BACKUP && \
cp -R ~/Documents ~/Desktop/ESSENTIAL_BACKUP/ && \
cp -R ~/Desktop ~/Desktop/ESSENTIAL_BACKUP/Desktop_Files && \
cp -R ~/Downloads ~/Desktop/ESSENTIAL_BACKUP/ 2>/dev/null || true && \
cp -R ~/.ssh ~/Desktop/ESSENTIAL_BACKUP/ 2>/dev/null || true && \
cp ~/.gitconfig ~/Desktop/ESSENTIAL_BACKUP/ 2>/dev/null || true && \
echo "✅ Backup complete! Copy ~/Desktop/ESSENTIAL_BACKUP to external drive"
```

---

**Remember: A clean slate often fixes more problems than hours of troubleshooting. You'll have a Mac that works exactly as Apple intended!**