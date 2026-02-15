# Migration Guide: iCloud → OneDrive Transition

**Date**: November 18, 2025  
**Reason**: Switched from iCloud backup to OneDrive continuous backup

---

## Overview

This guide documents the reconfiguration process after transitioning from iCloud-backed Desktop/Documents to OneDrive continuous backup. The transition broke path references throughout the system.

## Path Changes

### Old Structure (iCloud)
```
~/Documents/dev/               ← Old location
~/Desktop/                     ← Old location
```

### New Structure (OneDrive)
```
~/Documents/dev/               ← Active location (restored)
/Users/abhimehrotra/Library/CloudStorage/OneDrive-Personal/.Documents OneDrive/dev/  ← OneDrive sync location
```

### Solution: Dual Structure
- **Active configs**: `~/Documents/dev/personal-config` (git repo)
- **OneDrive backup**: Automatic sync via OneDrive client
- **Git remote**: github.com/abhimehro/personal-config

---

## Reconfiguration Steps Completed

### 1. Repository Setup ✅
```bash
# Cloned fresh from GitHub
cd ~/Documents/dev
git clone https://github.com/abhimehro/personal-config.git

# Added latest Control D configurations
cp -r ~/.config/controld/* ~/Documents/dev/personal-config/controld-system/
cp ~/Public/Scripts/maintenance/controld_monitor.sh ~/Documents/dev/personal-config/maintenance/
```

### 2. Control D Integration ✅
All Control D configurations from today's setup are now in the repo:
- `controld-system/ctrld.toml` - Main configuration
- `controld-system/README.md` - Comprehensive guide
- `controld-system/QUICKREF.md` - Quick reference
- `controld-system/VPN_INTEGRATION.md` - Windscribe guide
- `controld-system/UPGRADES.md` - Upgrade procedures
- `controld-system/SETUP_SUMMARY.md` - Technical details
- `controld-system/FINAL_SUMMARY.md` - Complete summary
- `controld-system/health-check.sh` - Health monitoring
- `controld-system/baseline-test.sh` - Quick validation
- `maintenance/controld_monitor.sh` - Integrated monitor

---

## Path References to Update

### Scripts/Configs That May Reference Old Paths

**Check these files for hard-coded paths**:
```bash
# Search for old path references
cd ~/Documents/dev/personal-config
grep -r "Library/CloudStorage/OneDrive" . 2>/dev/null | grep -v ".git"
grep -r "/Users/abhimehrotra/Documents/dev" . 2>/dev/null | grep -v ".git"
```

### Common Path Patterns to Fix

**Before** (broken):
```bash
/Users/abhimehrotra/Library/CloudStorage/OneDrive-Personal/.Documents OneDrive/dev/...
```

**After** (working):
```bash
~/Documents/dev/personal-config/...
# OR
${HOME}/Documents/dev/personal-config/...
```

---

## Maintenance Scripts

### Current Location
All maintenance scripts are in:
```
~/Public/Scripts/
├── maintenance/
│   ├── brew_maintenance.sh
│   ├── controld_monitor.sh          ← NEW
│   ├── health_check.sh
│   ├── quick_cleanup.sh
│   └── ...
└── run_all_maintenance.sh
```

**Status**: No path changes needed (already using `~/Public`)

### Backup Location in Repo
```
~/Documents/dev/personal-config/maintenance/
├── controld_monitor.sh              ← Backed up
└── ... (add others as needed)
```

---

## OneDrive Integration

### How It Works
1. **Active development**: `~/Documents/dev/personal-config/`
2. **Git for version control**: Push changes to GitHub
3. **OneDrive for backup**: Syncs `~/Documents/` automatically
4. **Result**: Triple redundancy (local + git + OneDrive)

### OneDrive Exclusions (if needed)
If OneDrive syncing causes issues with git:
```bash
# Exclude .git from OneDrive sync
# Settings → Backup → Manage Backup → Advanced → Exclude folders
# Add: ~/Documents/dev/personal-config/.git
```

---

## Services Requiring Path Updates

### Control D ✅
**Status**: Already configured with absolute paths
- Config: `~/.config/controld/ctrld.toml` (user directory)
- Launch daemon: `/Library/LaunchDaemons/ctrld.plist`
- No changes needed

### Maintenance System ✅
**Status**: Uses `~/Public/Scripts/`
- No changes needed
- Already integrated with Control D monitor

### Shell Configs
**Locations to check**:
```bash
~/.bash_profile
~/.bashrc
~/.zshrc
~/.config/fish/config.fish
```

**What to update**: Any references to:
- Old dev paths
- iCloud-specific paths
- Hard-coded user directories

---

## Git Workflow Going Forward

### Daily Workflow
```bash
# Make changes to configs
cd ~/Documents/dev/personal-config

# Check status
git status

# Add and commit
git add .
git commit -m "Update: description of changes"

# Push to GitHub
git push origin main
```

### After System Changes
```bash
# After installing new software, updating configs, etc.
cd ~/Documents/dev/personal-config

# Copy latest configs to repo
cp ~/.config/controld/ctrld.toml controld-system/
# ... copy other modified configs ...

# Commit and push
git add .
git commit -m "Update: [describe what changed]"
git push origin main
```

---

## Recovery Procedures

### If Configs Are Lost
```bash
# Pull from GitHub
cd ~/Documents/dev
rm -rf personal-config  # If corrupted
git clone https://github.com/abhimehro/personal-config.git

# Restore Control D
cp personal-config/controld-system/ctrld.toml ~/.config/controld/
sudo ctrld service restart
~/.config/controld/health-check.sh
```

### If OneDrive Causes Issues
```bash
# Disable OneDrive backup for Documents temporarily
# Work directly from ~/Documents/dev/personal-config
# Git is the source of truth, not OneDrive
```

---

## Validation Checklist

After migration, verify:

- [ ] Repository cloned to `~/Documents/dev/personal-config` ✅
- [ ] All Control D configs added to repo ✅
- [ ] Monitor script in `maintenance/` ✅
- [ ] `git remote -v` shows correct GitHub URL
- [ ] Can commit and push changes
- [ ] Control D service running: `sudo ctrld service status`
- [ ] Maintenance scripts work: `~/Public/Scripts/run_all_maintenance.sh`
- [ ] OneDrive syncing `~/Documents/` correctly

---

## Files in Repository (After Migration)

```
personal-config/
├── controld-system/              ← NEW: Complete Control D setup
│   ├── ctrld.toml
│   ├── README.md
│   ├── QUICKREF.md
│   ├── VPN_INTEGRATION.md
│   ├── UPGRADES.md
│   ├── SETUP_SUMMARY.md
│   ├── FINAL_SUMMARY.md
│   ├── health-check.sh
│   └── baseline-test.sh
├── maintenance/
│   └── controld_monitor.sh       ← NEW: Monitoring script
├── windscribe-controld/          ← Existing VPN configs
├── configs/                      ← Shell, editor configs
├── scripts/                      ← Utility scripts
├── macos/                        ← macOS-specific configs
└── docs/                         ← Documentation
```

---

## Next Steps

### Immediate
1. ✅ Repository cloned and configured
2. ✅ Control D configs added
3. ⏭️ Commit and push changes
4. ⏭️ Verify OneDrive sync
5. ⏭️ Test git workflow

### Ongoing
- Update repo after significant system changes
- Push to GitHub weekly (or after major changes)
- Verify OneDrive backup is current
- Test restore procedure quarterly

---

## Common Issues & Solutions

### Issue: Git conflicts with OneDrive
**Solution**: OneDrive should sync files, git handles versions. If conflicts arise, git is source of truth.

### Issue: Hard-coded paths in scripts
**Solution**: Use environment variables:
```bash
REPO_ROOT="${HOME}/Documents/dev/personal-config"
```

### Issue: OneDrive sync lag
**Solution**: Force sync or work directly from `~/Documents/dev/` (OneDrive will catch up)

---

## Teaching Moment: Triple Redundancy

Your config backup strategy now has three layers:
1. **Local**: `~/Documents/dev/personal-config/` (active work)
2. **Git**: GitHub repository (version history)
3. **Cloud**: OneDrive sync (automatic backup)

**Why this works**:
- Git provides version control and rollback
- GitHub provides off-site backup and sharing
- OneDrive provides continuous backup without manual steps
- If any one fails, you have two others

**Trade-off**:
- More complex than single backup
- Requires discipline to commit changes
- Potential for sync conflicts

**Verdict**: Worth it for critical configurations ✓

---

## Maintenance

Update this guide when:
- Adding new major configurations
- Changing backup strategy
- Discovering path issues
- Setting up on new machine

**Last Updated**: November 18, 2025
