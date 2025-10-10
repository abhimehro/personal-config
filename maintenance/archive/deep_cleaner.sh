#!/usr/bin/env bash
source "${HOME}/Scripts/maintenance/common.sh"
log_file_init "deep_cleaner"
acquire_lock "deep_cleaner"

log_info "Deep system cleaning started"

REPORT_FILE="${LOG_DIR}/deep_clean_report-$(date +%Y%m%d-%H%M).txt"
REPORT=""
append() { REPORT+="$1"$'\n'; log_info "$1"; echo "$1"; }

append "=== DEEP SYSTEM CLEANING REPORT ==="
append "Generated: $(date)"
append ""

DISK_BEFORE=$(percent_used "/")
append "Disk usage before cleaning: ${DISK_BEFORE}%"
append ""

# 1) Find large files and directories
append "=== LARGEST FILES AND DIRECTORIES ==="
log_info "Scanning for large files (this may take a moment)..."
append "Top 20 largest files over 100MB:"
find / -type f -size +100M 2>/dev/null | head -20 | while read -r file; do
    size=$(du -h "$file" 2>/dev/null | cut -f1)
    append "  $size - $file"
done

append ""
append "Top 10 largest directories:"
du -h / 2>/dev/null | sort -hr | head -10 | while read -r line; do
    append "  $line"
done
append ""

# 2) Application remnants that CleanMyMac might miss
append "=== APPLICATION REMNANTS ANALYSIS ==="

# Check for orphaned application support files
ORPHANED_APP_SUPPORT=""
APP_SUPPORT_DIR="${HOME}/Library/Application Support"
if [[ -d "${APP_SUPPORT_DIR}" ]]; then
    log_info "Scanning Application Support for orphaned files..."
    while IFS= read -r -d '' app_dir; do
        app_name=$(basename "$app_dir")
        # Check if corresponding app exists in Applications or is a known system component
        if [[ ! -d "/Applications/${app_name}.app" ]] && [[ ! -d "/System/Applications/${app_name}.app" ]] && 
           [[ ! "$app_name" =~ ^(com\.|Adobe|Microsoft|Google|Apple|Dropbox|Slack|Zoom).*$ ]]; then
            size=$(du -sh "$app_dir" 2>/dev/null | cut -f1)
            ORPHANED_APP_SUPPORT+="  $size - $app_dir"$'\n'
        fi
    done < <(find "${APP_SUPPORT_DIR}" -maxdepth 1 -type d -not -name ".*" -print0 2>/dev/null)
fi

if [[ -n "${ORPHANED_APP_SUPPORT}" ]]; then
    append "Potentially orphaned Application Support directories:"
    append "${ORPHANED_APP_SUPPORT}"
else
    append "No obvious orphaned Application Support directories found"
fi

# Check for orphaned preference files
append ""
append "Potentially orphaned preference files:"
PREFS_DIR="${HOME}/Library/Preferences"
ORPHANED_PREFS=""
if [[ -d "${PREFS_DIR}" ]]; then
    while IFS= read -r -d '' pref_file; do
        pref_name=$(basename "$pref_file" .plist)
        # Skip known system preferences
        if [[ ! "$pref_name" =~ ^(com\.apple\.|loginwindow|systemuiserver).*$ ]] && 
           [[ ! -d "/Applications/${pref_name}.app" ]] && 
           [[ ! -d "/System/Applications/${pref_name}.app" ]]; then
            size=$(du -sh "$pref_file" 2>/dev/null | cut -f1)
            ORPHANED_PREFS+="  $size - $pref_file"$'\n'
        fi
    done < <(find "${PREFS_DIR}" -name "*.plist" -print0 2>/dev/null)
fi

if [[ -n "${ORPHANED_PREFS}" ]]; then
    append "${ORPHANED_PREFS}"
else
    append "No obvious orphaned preference files found"
fi
append ""

# 3) System caches beyond user caches
append "=== SYSTEM-WIDE CACHE ANALYSIS ==="
SYSTEM_CACHES=(
    "/Library/Caches"
    "/System/Library/Caches"
    "/private/var/tmp"
    "/private/tmp"
    "/Users/Shared"
)

for cache_dir in "${SYSTEM_CACHES[@]}"; do
    if [[ -d "$cache_dir" ]] && [[ -r "$cache_dir" ]]; then
        cache_size=$(du -sh "$cache_dir" 2>/dev/null | cut -f1)
        append "$cache_dir: $cache_size"
    fi
done
append ""

# 4) Language files and unused localizations
append "=== LOCALIZATION FILES ==="
log_info "Scanning for unused language files..."
LANG_FILES=$(find /Applications -name "*.lproj" 2>/dev/null | grep -E "(Japanese|Korean|Chinese|French|German|Spanish|Italian)" | wc -l | tr -d ' ')
append "Non-English localization directories found: ${LANG_FILES}"
append "Consider using tools like Monolingual to remove unused languages"
append ""

# 5) Duplicate files
append "=== DUPLICATE FILE ANALYSIS ==="
log_info "Scanning for potential duplicate files in common locations..."
COMMON_DUPE_DIRS=(
    "${HOME}/Downloads"
    "${HOME}/Desktop"
    "${HOME}/Documents"
    "${HOME}/Pictures"
)

for dir in "${COMMON_DUPE_DIRS[@]}"; do
    if [[ -d "$dir" ]]; then
        dupes=$(find "$dir" -type f -name "*copy*" -o -name "*duplicate*" -o -name "*(1)*" 2>/dev/null | wc -l | tr -d ' ')
        if (( dupes > 0 )); then
            append "Potential duplicates in $dir: $dupes files"
        fi
    fi
done
append ""

# 6) Old iOS backups and device syncs
append "=== MOBILE DEVICE BACKUPS ==="
MOBILE_BACKUP_DIR="${HOME}/Library/Application Support/MobileSync/Backup"
if [[ -d "${MOBILE_BACKUP_DIR}" ]]; then
    backup_size=$(du -sh "${MOBILE_BACKUP_DIR}" 2>/dev/null | cut -f1)
    backup_count=$(find "${MOBILE_BACKUP_DIR}" -maxdepth 1 -type d 2>/dev/null | wc -l | tr -d ' ')
    append "iOS Backups: $backup_size in $backup_count backup sets"
    append "Location: ${MOBILE_BACKUP_DIR}"
else
    append "No iOS backups found"
fi
append ""

# 7) Docker and VM images
append "=== DOCKER AND VIRTUAL MACHINE FILES ==="
DOCKER_DIR="${HOME}/Library/Containers/com.docker.docker/Data"
VM_DIRS=(
    "${HOME}/Virtual Machines.localized"
    "${HOME}/Documents/Virtual Machines"
    "${HOME}/Library/Application Support/VMware Fusion"
    "${HOME}/.docker"
)

for vm_dir in "${VM_DIRS[@]}"; do
    if [[ -d "$vm_dir" ]]; then
        vm_size=$(du -sh "$vm_dir" 2>/dev/null | cut -f1)
        append "VM/Container files in $vm_dir: $vm_size"
    fi
done
append ""

# 8) Browser profile bloat
append "=== BROWSER PROFILE ANALYSIS ==="
BROWSER_DIRS=(
    "${HOME}/Library/Application Support/Google/Chrome"
    "${HOME}/Library/Safari"
    "${HOME}/Library/Application Support/Firefox"
    "${HOME}/Library/Application Support/Microsoft Edge"
)

for browser_dir in "${BROWSER_DIRS[@]}"; do
    if [[ -d "$browser_dir" ]]; then
        browser_size=$(du -sh "$browser_dir" 2>/dev/null | cut -f1)
        browser_name=$(basename "$(dirname "$browser_dir")")
        append "$browser_name profile: $browser_size"
    fi
done
append ""

# 9) Development environment cleanup
append "=== DEVELOPMENT ENVIRONMENT CLEANUP ==="
DEV_CACHES=(
    "${HOME}/.npm"
    "${HOME}/.yarn"
    "${HOME}/.gradle"
    "${HOME}/.m2"
    "${HOME}/.cargo"
    "${HOME}/Library/Developer/Xcode/DerivedData"
    "${HOME}/Library/Developer/CoreSimulator"
    "${HOME}/.rbenv"
    "${HOME}/.pyenv"
)

for dev_cache in "${DEV_CACHES[@]}"; do
    if [[ -d "$dev_cache" ]]; then
        cache_size=$(du -sh "$dev_cache" 2>/dev/null | cut -f1)
        cache_name=$(basename "$dev_cache")
        append "Development cache ($cache_name): $cache_size"
    fi
done
append ""

# 10) Log file analysis
append "=== LOG FILE ANALYSIS ==="
LOG_DIRS=(
    "${HOME}/Library/Logs"
    "/var/log"
    "/Library/Logs"
)

for log_dir in "${LOG_DIRS[@]}"; do
    if [[ -d "$log_dir" ]] && [[ -r "$log_dir" ]]; then
        log_size=$(du -sh "$log_dir" 2>/dev/null | cut -f1)
        old_logs=$(find "$log_dir" -name "*.log" -mtime +30 2>/dev/null | wc -l | tr -d ' ')
        append "$log_dir: $log_size ($old_logs files older than 30 days)"
    fi
done
append ""

# 11) Mail attachments and downloads
append "=== MAIL ATTACHMENTS ==="
MAIL_DOWNLOADS="${HOME}/Library/Mail/V*/MailData/Attachments"
if ls ${MAIL_DOWNLOADS} >/dev/null 2>&1; then
    mail_size=$(du -sh ${MAIL_DOWNLOADS} 2>/dev/null | cut -f1)
    append "Mail attachments: $mail_size"
else
    append "No mail attachments found"
fi
append ""

# 12) Generate cleanup recommendations
append "=== CLEANUP RECOMMENDATIONS ==="
append ""
append "🧹 Safe automated cleanups you can run:"
append "1. Clear development caches:"
append "   npm cache clean --force"
append "   pip cache purge"
append "   gem cleanup"
append "   yarn cache clean"
append ""
append "2. Clear browser caches (will log you out):"
append "   rm -rf ~/Library/Caches/com.google.Chrome/Default/Cache"
append "   rm -rf ~/Library/Caches/com.apple.Safari/Cache.db*"
append ""
append "3. Remove old iOS backups (after verifying you don't need them):"
append "   Check: System Preferences > Apple ID > iCloud > Manage > Backups"
append ""
append "⚠️  Manual review recommended:"
append "1. Review Application Support directories listed above"
append "2. Check for duplicate files in Downloads/Desktop"
append "3. Consider removing unused language packs with Monolingual"
append "4. Review old virtual machine files"
append ""
append "🔧 Advanced cleaning commands (use with caution):"
append "# Remove Adobe crash logs"
append "rm -rf ~/Library/Logs/Adobe/*"
append ""
append "# Clear Font caches (requires restart)"
append "sudo atsutil databases -remove"
append ""
append "# Clear DNS cache"
append "sudo dscacheutil -flushcache"

# Save comprehensive report
printf "%s\n" "${REPORT}" > "${REPORT_FILE}"

DISK_AFTER=$(percent_used "/")
append ""
append "Disk usage after analysis: ${DISK_AFTER}%"
append ""
append "📊 Report saved to: ${REPORT_FILE}"

log_info "Deep cleaning analysis complete"
notify "Deep Cleaner" "Analysis complete. Check report for cleanup recommendations."

echo ""
echo "🎯 Next Steps:"
echo "1. Review the report above for specific recommendations"
echo "2. Manually verify any files before deleting them"
echo "3. Use the safe cleanup commands provided"
echo "4. Consider tools like:"
echo "   - Monolingual (for language files)"
echo "   - DupeGuru (for duplicate files)"
echo "   - Disk Utility First Aid (for filesystem issues)"
