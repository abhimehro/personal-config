# iTerm2 SSH Configuration Guide

## 🖥️ iTerm2 Profile Setup for SSH

### **Creating SSH Profile in iTerm2:**

1. **Open iTerm2 Preferences** (`Cmd + ,`)
2. **Go to Profiles tab**
3. **Click the "+" to create new profile**
4. **Name it:** "Cursor Remote (mDNS)"

### **Command Tab Settings:**
- **Command:** `Custom Shell`
- **Send text at start:** `ssh cursor-mdns`

### **Or for Advanced SSH Profile:**
- **Command:** `Custom Shell`
- **Send text at start:** Leave empty
- **Working Directory:** `Advanced Configuration` → **Edit**

### **Advanced Configuration:**
```
Initial command: ssh cursor-mdns
Working directory: Reuse previous session's directory
```

### **Environment Variables:**
Add these key-value pairs in the Environment section:
```
LANG=en_US.UTF-8
LC_ALL=en_US.UTF-8
TERM=xterm-256color
COLORTERM=truecolor
```

### **SSH-Specific Profile (Alternative Method):**

**If you want a dedicated SSH profile:**

1. **Command tab:**
   - **Command:** `/usr/bin/ssh`
   - **Arguments:** `cursor-mdns`

2. **Terminal tab:**
   - **Terminal Type:** `xterm-256color`
   - **Character Encoding:** `UTF-8`

3. **Session tab:**
   - **When session ends:** `Close`
   - **Undo can revive session:** ✅

### **Quick Setup Commands:**

For immediate use, you can also create iTerm2 profiles via command line:

```bash
# Create a simple SSH bookmark
echo "ssh cursor-mdns" > ~/.ssh/iterm_connect.sh
chmod +x ~/.ssh/iterm_connect.sh
```

Then in iTerm2: **Profiles** → **Open Profiles** → **Edit Profiles** → **+**
- **Name:** "MacBook Remote"
- **Command:** `Custom Shell`
- **Send text at start:** `~/.ssh/iterm_connect.sh`

### **Recommended iTerm2 Settings for SSH:**

**General tab:**
- **Working Directory:** `Reuse previous session's directory`
- **Icon:** Choose an SSH/remote icon

**Colors tab:**
- Use a different color scheme to distinguish remote sessions
- Suggestion: Slightly different background color

**Session tab:**
- **Status bar enabled:** ✅
- **Add component:** `Host Name` to show you're connected remotely

### **Pro Tips for iTerm2 + SSH:**

1. **Create multiple profiles:**
   - `cursor-mdns` (primary)
   - `cursor-local` (VPN off)
   - `cursor-vpn` (if needed later)

2. **Use different color schemes** for each profile to visually distinguish

3. **Enable status bar** showing hostname so you know which machine you're on

4. **Keyboard shortcuts:**
   - Assign `Cmd+Shift+R` to open remote profile quickly

### **Files to Copy (Usually Not Needed):**

For most development work, **leave this empty**. Your SSH keys are handled by 1Password.

**Only add if you specifically need:**
```
~/.gitconfig    # Git configuration
~/.vimrc        # Vim settings
~/.tmux.conf    # Tmux configuration
```

**Note:** Don't copy sensitive files like SSH keys - 1Password handles that!

## 🎯 **Recommended Setup:**

**Simplest and most reliable:**
1. Create iTerm2 profile named "MacBook Remote"
2. Set command to: `ssh cursor-mdns`
3. Everything else: default settings
4. Assign keyboard shortcut for quick access

This gives you one-click SSH access to your MacBook with all the benefits of your optimized SSH configuration!