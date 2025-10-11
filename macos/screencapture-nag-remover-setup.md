# macOS Screen Capture Nag Remover Setup

## Overview
This document describes the setup of the `screencapture-nag-remover` tool on macOS 26.0.1 (25A362) to suppress persistent screen capture permission alerts.

## System Information
- **macOS Version**: 26.0.1 (25A362) - macOS 16 Beta
- **Tool Version**: 1.3.3
- **Installation Date**: 2025-10-10
- **Shell**: Fish 4.1.2 (primary), Bash 5.3.3 (for compatibility)

## Installation Paths
- **Original Script**: `~/bin/screencapture-nag-remover`
- **Wrapper Script**: `~/bin/screencapture-nag-remover-wrapper.sh`
- **LaunchAgent**: `~/Library/LaunchAgents/screencapture-nag-remover.plist`
- **Logs**: `/private/tmp/screencapture-nag-remover-wrapper.log`
- **Target Plist**: `~/Library/Group Containers/group.com.apple.replayd/ScreenCaptureApprovals.plist`
- **Backup**: `~/Library/Group Containers/group.com.apple.replayd/ScreenCaptureApprovals.plist.bak.*`

## Full Disk Access Requirements
The following items require Full Disk Access to modify the ScreenCaptureApprovals.plist:
1. **WarpPreview** (or your terminal app) - for manual runs
2. **/bin/bash** - for LaunchAgent automated runs

### Granting Full Disk Access
1. Open System Settings → Privacy & Security → Full Disk Access
2. Click the (+) button
3. Press ⌘Cmd + ⇧Shift + G
4. Type `/bin` (for bash) or navigate to Applications (for WarpPreview)
5. Select the item and click Open
6. Enable the toggle

## How It Works
The tool modifies the `ScreenCaptureApprovals.plist` file to set nag alert dates 100 years into the future (year 2125), effectively suppressing the alerts for all approved screen capture apps.

### Apps Currently Managed (as of 2025-10-10)
- Neo Browser (ai.browser.Neo)
- Perplexity (ai.perplexity.mac)
- Sidebar (at.sidebar.Sidebar)
- uBar (ca.brawer.uBar)
- iBar (cn.better365.iBar)
- Dynamic Lake Pro (com.aviorrok.DynamicLakePro.DynamicLakePro)
- Quip (com.bzg.quip)
- Barbee (com.HyperartFlow.Barbee)
- Ice (com.jordanbaird.Ice)
- Edge Beta (com.microsoft.edgemac.Beta)
- Edge Canary (com.microsoft.edgemac.Canary)
- ChatGPT (com.openai.chat)
- Raycast (com.raycast.macos)
- ActiveDock 2 (com.sergey-gerasimenko.ActiveDock-2)
- Command-Tab Plus 2 (com.sergey-gerasimenko.Command-Tab-Plus-2)
- SuperWhisper (com.superduper.superwhisper)
- Bartender (com.surteesstudios.Bartender)
- BetterDisplay (pro.betterdisplay.BetterDisplay)

## LaunchAgent Configuration
The LaunchAgent runs every 24 hours (86400 seconds) to refresh the nag dates. This is essential for macOS 15.1+ which resets dates when apps are actively used.

### LaunchAgent Schedule
- **Interval**: Every 24 hours
- **Command**: `/bin/bash ~/bin/screencapture-nag-remover-wrapper.sh`
- **Logs**: `/private/tmp/screencapture-nag-remover-wrapper.log`

## Manual Operations

### Run Manual Update
```bash
bash ~/bin/screencapture-nag-remover-wrapper.sh
```

### Check LaunchAgent Status
```bash
launchctl list | grep screencapture-nag-remover
launchctl print gui/$(id -u)/screencapture-nag-remover.agent
```

### Manually Trigger LaunchAgent
```bash
launchctl kickstart -k gui/$(id -u)/screencapture-nag-remover.agent
```

### View LaunchAgent Logs
```bash
cat /private/tmp/screencapture-nag-remover-wrapper.log
```

### Inspect Current Plist State
```bash
plutil -p "$HOME/Library/Group Containers/group.com.apple.replayd/ScreenCaptureApprovals.plist" | head -n 50
```

### Add a New App Manually
For macOS 26 (using bundle ID):
```bash
PLIST="$HOME/Library/Group Containers/group.com.apple.replayd/ScreenCaptureApprovals.plist"
FUTURE=$(date -j -v+100y +"%Y-%m-%d %H:%M:%S +0000")
BUNDLE_ID="com.example.app"

/usr/bin/defaults write "$PLIST" "$BUNDLE_ID" -dict \
    kScreenCaptureApprovalLastAlerted -date "$FUTURE" \
    kScreenCaptureApprovalLastUsed -date "$FUTURE"

# Restart daemons
/usr/bin/killall -HUP replayd
/usr/bin/killall -u "$USER" cfprefsd
```

## Uninstall

### Remove LaunchAgent
```bash
launchctl bootout gui/$(id -u) "$HOME/Library/LaunchAgents/screencapture-nag-remover.plist"
rm "$HOME/Library/LaunchAgents/screencapture-nag-remover.plist"
```

### Remove Scripts
```bash
rm ~/bin/screencapture-nag-remover
rm ~/bin/screencapture-nag-remover-wrapper.sh
```

### Restore Original Plist (if needed)
```bash
# Find the most recent backup
ls -t "$HOME/Library/Group Containers/group.com.apple.replayd/ScreenCaptureApprovals.plist.bak."*

# Restore from backup (replace with actual backup filename)
cp "$HOME/Library/Group Containers/group.com.apple.replayd/ScreenCaptureApprovals.plist.bak.YYYYMMDD-HHMMSS" \
   "$HOME/Library/Group Containers/group.com.apple.replayd/ScreenCaptureApprovals.plist"
```

## Troubleshooting

### Permission Errors
If you see "Operation not permitted" or "Full Disk Access permissions are missing":
1. Ensure your terminal has Full Disk Access
2. Ensure /bin/bash has Full Disk Access
3. Restart the terminal after granting permissions

### LaunchAgent Not Running
```bash
# Check if loaded
launchctl list | grep screencapture

# Reload the agent
launchctl bootout gui/$(id -u) "$HOME/Library/LaunchAgents/screencapture-nag-remover.plist"
launchctl bootstrap gui/$(id -u) "$HOME/Library/LaunchAgents/screencapture-nag-remover.plist"
```

### Dates Not Updating
The wrapper script uses a manual approach that's compatible with macOS 26. If dates aren't updating:
1. Check the log file for errors
2. Verify the plist file exists and is readable
3. Run the wrapper script manually to test

## Notes for macOS 26.0.1
- The original `screencapture-nag-remover.sh` script (v1.3.3) was designed for macOS 15.x
- macOS 26 uses a similar plist structure but the script's built-in methods had compatibility issues
- A custom wrapper script (`screencapture-nag-remover-wrapper.sh`) was created to use the manual update approach that works reliably on macOS 26

## References
- Original Tool: https://github.com/gavinhungry/screencapture-nag-remover
- Version: 1.3.3
- License: Public Domain
