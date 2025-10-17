# macOS Configuration & Workarounds

This directory contains configuration files and documentation for macOS 26.0.1 (25A362) system customizations, particularly focused on privacy indicator management and menu bar optimization.

## Documentation

### Screen Capture Alerts - ✅ Fully Suppressible
📄 [`screencapture-nag-remover-setup.md`](./screencapture-nag-remover-setup.md)

**Status**: ✅ **Working Solution**  
**Method**: Modifies `ScreenCaptureApprovals.plist` to set nag dates 100 years in the future

- Automated LaunchAgent runs daily to maintain suppression
- Compatible with macOS 15+ and 26.0.1
- Covers 19+ apps including menu bar organizers
- Full Disk Access required for WarpPreview and /bin/bash

### Microphone Mode Indicator - 🎨 Creative Workaround
📄 [`barbee-menubar-configuration.md`](./barbee-menubar-configuration.md)

**Status**: 🎨 **Visual Solution**  
**Method**: Strategic positioning of Barbee (DynamicLake Pro) to obscure the indicator

- Cannot be truly disabled (system-level limitation)
- Barbee icon positioned over mic indicator with 200px spacers
- Orange color peeks through as intentional design accent
- Backup configuration included: [`barbee-config/Backup/`](./barbee-config/Backup/)

## Key Differences

| Feature | Screen Capture Alert | Mic Mode Indicator |
|---------|---------------------|-------------------|
| **Can be disabled?** | ✅ Yes (via plist) | ❌ No (system-rendered) |
| **Solution type** | Technical suppression | Visual obscuration |
| **Persistence** | Permanent (with LaunchAgent) | Layout-dependent |
| **Requirements** | Full Disk Access | Barbee app + configuration |
| **Effectiveness** | 100% suppression | ~95% visual hiding |

## Quick Links

### Screen Capture Setup
```bash
# Run the wrapper script manually
bash ~/bin/screencapture-nag-remover-wrapper.sh

# Check LaunchAgent status
launchctl list | grep screencapture-nag-remover

# View logs
cat /private/tmp/screencapture-nag-remover-wrapper.log
```

### Barbee Restoration
```bash
# Restore Barbee configuration (adjust date folder as needed)
cp -R ~/Documents/dev/personal-config/macos/barbee-config/Backup/Barbee_Profile_2025_10_17_17_11_05/Default.bbp \
      "$HOME/Library/Application Support/Barbee/Profiles/"
      
# Relaunch Barbee
killall "Barbee" && open -a "Barbee"
```

### Update Backups
```bash
# Update Barbee backup after changes
DATE_FOLDER="Barbee_Profile_$(date +%Y_%m_%d_%H_%M_%S)"
mkdir -p ~/Documents/dev/personal-config/macos/barbee-config/Backup/$DATE_FOLDER
cp -R "$HOME/Library/Mobile Documents/iCloud~hyperartflow~barbee/Documents/Backups/Default.bbp" \
      ~/Documents/dev/personal-config/macos/barbee-config/Backup/$DATE_FOLDER/

# Commit changes
cd ~/Documents/dev/personal-config
git add macos/barbee-config/
git commit -m "Update Barbee configuration - $DATE_FOLDER"
git push origin main
```

## System Information

- **macOS Version**: 26.0.1 (25A362) - macOS 16 Beta
- **Shell**: Fish 4.1.2
- **Terminal**: WarpPreview
- **Display**: LG 27GL850 (2560x1440 @ 144Hz)
- **Setup Date**: October 10-11, 2025

## Related Tools

### Privacy & Menu Bar Management
- **Barbee** (DynamicLake Pro): Menu bar customization and mic indicator hiding
- **Ice**: Additional menu bar organization
- **BetterDisplay**: Display management and XDR brightness
- **Lunar**: Auto-learned brightness via sensor

### Audio Tools (Trigger Mic Indicator)
- **Boom 3D**: System-wide audio enhancement
- **SpeakerAmp**: Audio amplification
- Both use mic passthrough, triggering the indicator constantly

## Apple Feedback

Both issues have been widely reported to Apple:

🔗 **Submit feedback**: https://www.apple.com/feedback/macos.html

**Key points to mention**:
- Privacy indicators are redundant (dot + large icon)
- Take excessive menu bar space (especially on notched displays)
- Impact audio professionals, musicians, and power users
- Request user toggle in System Settings

## Community Resources

- [r/MacOS on Reddit](https://www.reddit.com/r/MacOS/)
- [MacRumors Forums](https://forums.macrumors.com/)
- [Apple Community Discussions](https://discussions.apple.com/)

## Future Monitoring

Watch for these potential improvements in future macOS updates:
- System Settings toggle for mic mode indicator
- Terminal command to disable indicator
- Configuration profile option (MDM)
- Reduced indicator size or auto-hide behavior

---

**Last Updated**: October 17, 2025  
**macOS Version**: 26.0.1 (25A362)  
**Status**: Both solutions working as designed
