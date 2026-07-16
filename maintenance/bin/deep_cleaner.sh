#!/usr/bin/env bash

# Self-contained deep system cleaner - MONTHLY VERSION with incremental state tracking
set -euo pipefail

# Configuration
LOG_DIR="$HOME/Library/Logs/maintenance"
mkdir -p "$LOG_DIR"

# Allow --force to set FORCE_RUN before the monthly gate and before state checks.
for arg in "$@"; do
	if [[ $arg == "--force" ]]; then
		export FORCE_RUN=1
		break
	fi
done

# Only run on the 1st of the month or if FORCE_RUN is set
DAY_OF_MONTH=$(date +%-d) # %-d removes leading zero
if [[ $DAY_OF_MONTH -ne 1 ]] && [[ ${FORCE_RUN:-0} != "1" ]]; then
	echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] [deep_cleaner] Monthly deep cleaning skipped - only runs on 1st of month (today is $(date +%B) $(date +%d))"
	exit 0
fi

# Basic logging
log_info() {
	local ts
	ts="$(date '+%Y-%m-%d %H:%M:%S')"
	echo "$ts [INFO] [deep_cleaner] $*" | tee -a "$LOG_DIR/deep_cleaner.log"
}

log_warn() {
	local ts
	ts="$(date '+%Y-%m-%d %H:%M:%S')"
	echo "$ts [WARNING] [deep_cleaner] $*" | tee -a "$LOG_DIR/deep_cleaner.log"
}

# Preserve environment overrides before config.env may reset them.
__dry_run_override="${DRY_RUN-}"

# Load config
CONFIG_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../conf" && pwd)/config.env"
if [[ -f $CONFIG_FILE ]]; then
	source "$CONFIG_FILE" 2>/dev/null || true
fi

# Restore environment DRY_RUN override if it was set before sourcing config.
if [[ -n $__dry_run_override ]]; then
	DRY_RUN="$__dry_run_override"
fi

# Load shared state-tracking library
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$SCRIPT_DIR/../lib/state.sh" ]]; then
	# shellcheck disable=SC1091
	source "$SCRIPT_DIR/../lib/state.sh"
fi

# Get disk usage percentage
percent_used() {
	local path="${1:-/}"
	df -P "$path" | awk 'NR==2 {print $5}' | tr -d '%'
}

log_info "Deep system cleaning started"

REPORT_FILE="${LOG_DIR}/deep_clean_report-$(date +%Y%m%d-%H%M).txt"
REPORT=""
append() {
	REPORT+="$1"$'\n'
	log_info "$1"
	echo "$1"
}

append "=== DEEP SYSTEM CLEANING REPORT ==="
append "Generated: $(date)"
append ""

DISK_BEFORE=$(percent_used "/")
append "Disk usage before cleaning: ${DISK_BEFORE}%"
append ""

# Helper: return 0 if any path in the list is newer than the last run for key.
# Respects FORCE_RUN=1 via is_modified_since_last_run.
any_modified() {
	local state_key="$1"
	shift
	local p
	for p in "$@"; do
		if [[ -e $p ]] && is_modified_since_last_run "$p" "$state_key"; then
			return 0
		fi
	done
	return 1
}

# 1) Find large files and directories
if any_modified "deep_cleaner_large_files" "$HOME"; then
	append "=== LARGEST FILES AND DIRECTORIES ==="
	log_info "Scanning for large files (this may take a moment)..."
	append "Top 20 largest files over 100MB:"

	while IFS= read -r file; do
		size=$(du -h "$file" 2>/dev/null | cut -f1)
		append "  $size - $file"
	done < <(timeout 300 find "$HOME" -type f -size +100M 2>/dev/null | head -20) 2>/dev/null || log_warn "Large file scan timed out or had errors"

	append ""
	append "Top 10 largest directories in home:"
	while IFS= read -r line; do
		append "  $line"
	done < <(timeout 120 du -h "$HOME" 2>/dev/null | sort -hr | head -10) 2>/dev/null || log_warn "Directory size scan timed out or had errors"
	append ""

	state_set_last_run "deep_cleaner_large_files"
else
	append "=== LARGEST FILES AND DIRECTORIES ==="
	append "Skipped - no changes since last run"
	append ""
fi

# 2) Application remnants that CleanMyMac might miss
APP_SUPPORT_DIR="${HOME}/Library/Application Support"
PREFS_DIR="${HOME}/Library/Preferences"
if any_modified "deep_cleaner_app_remnants" "$APP_SUPPORT_DIR" "$PREFS_DIR"; then
	append "=== APPLICATION REMNANTS ANALYSIS ==="

	# Check for orphaned application support files
	ORPHANED_APP_SUPPORT=""
	if [[ -d ${APP_SUPPORT_DIR} ]]; then
		log_info "Scanning Application Support for orphaned files..."
		while IFS= read -r -d '' app_dir; do
			# ⚡ Bolt Optimization: parameter expansion avoids process spawning
			app_name="${app_dir##*/}"
			# Check if corresponding app exists in Applications or is a known system component
			if [[ ! -d "/Applications/${app_name}.app" ]] && [[ ! -d "/System/Applications/${app_name}.app" ]] &&
				[[ ! $app_name =~ ^(com\.|Adobe|Microsoft|Google|Apple|Dropbox|Slack|Zoom).*$ ]]; then
				size=$(du -sh "$app_dir" 2>/dev/null | cut -f1)
				ORPHANED_APP_SUPPORT+="  $size - $app_dir"$'\n'
			fi
		done < <(timeout 60 find "${APP_SUPPORT_DIR}" -maxdepth 1 -type d -not -name ".*" -print0 2>/dev/null || true)
	fi

	if [[ -n ${ORPHANED_APP_SUPPORT} ]]; then
		append "Potentially orphaned Application Support directories:"
		append "${ORPHANED_APP_SUPPORT}"
	else
		append "No obvious orphaned Application Support directories found"
	fi

	# Check for orphaned preference files
	append ""
	append "Potentially orphaned preference files:"
	ORPHANED_PREFS=""
	if [[ -d ${PREFS_DIR} ]]; then
		while IFS= read -r -d '' pref_file; do
			# ⚡ Bolt Optimization: parameter expansion avoids process spawning
			pref_name="${pref_file##*/}"
			pref_name="${pref_name%.plist}"
			# Skip known system preferences
			if [[ ! $pref_name =~ ^(com\.apple\.|loginwindow|systemuiserver).*$ ]] &&
				[[ ! -d "/Applications/${pref_name}.app" ]] &&
				[[ ! -d "/System/Applications/${pref_name}.app" ]]; then
				size=$(du -sh "$pref_file" 2>/dev/null | cut -f1)
				ORPHANED_PREFS+="  $size - $pref_file"$'\n'
			fi
		done < <(timeout 30 find "${PREFS_DIR}" -name "*.plist" -print0 2>/dev/null || true)
	fi

	if [[ -n ${ORPHANED_PREFS} ]]; then
		append "${ORPHANED_PREFS}"
	else
		append "No obvious orphaned preference files found"
	fi
	append ""

	state_set_last_run "deep_cleaner_app_remnants"
else
	append "=== APPLICATION REMNANTS ANALYSIS ==="
	append "Skipped - no changes since last run"
	append ""
fi

# 3) System caches beyond user caches
SYSTEM_CACHES=(
	"/Library/Caches"
	"/System/Library/Caches"
	"/private/var/tmp"
	"/private/tmp"
	"/Users/Shared"
)
if any_modified "deep_cleaner_system_caches" "${SYSTEM_CACHES[@]}"; then
	append "=== SYSTEM-WIDE CACHE ANALYSIS ==="
	for cache_dir in "${SYSTEM_CACHES[@]}"; do
		if [[ -d $cache_dir ]] && [[ -r $cache_dir ]]; then
			cache_size=$(du -sh "$cache_dir" 2>/dev/null | cut -f1)
			append "$cache_dir: $cache_size"
		fi
	done
	append ""

	state_set_last_run "deep_cleaner_system_caches"
else
	append "=== SYSTEM-WIDE CACHE ANALYSIS ==="
	append "Skipped - no changes since last run"
	append ""
fi

# 4) Language files and unused localizations
if any_modified "deep_cleaner_localizations" "/Applications"; then
	append "=== LOCALIZATION FILES ==="
	log_info "Scanning for unused language files..."
	LANG_FILES=$(timeout 60 find /Applications -name "*.lproj" 2>/dev/null | grep -E "(Japanese|Korean|Chinese|French|German|Spanish|Italian)" | wc -l | tr -d ' ' || echo "0")
	append "Non-English localization directories found: ${LANG_FILES}"
	append "Consider using tools like Monolingual to remove unused languages"
	append ""

	state_set_last_run "deep_cleaner_localizations"
else
	append "=== LOCALIZATION FILES ==="
	append "Skipped - no changes since last run"
	append ""
fi

# 5) Duplicate files
COMMON_DUPE_DIRS=(
	"${HOME}/Downloads"
	"${HOME}/Desktop"
	"${HOME}/Documents"
	"${HOME}/Pictures"
)
if any_modified "deep_cleaner_duplicates" "${COMMON_DUPE_DIRS[@]}"; then
	append "=== DUPLICATE FILE ANALYSIS ==="
	log_info "Scanning for potential duplicate files in common locations..."
	for dir in "${COMMON_DUPE_DIRS[@]}"; do
		if [[ -d $dir ]]; then
			dupes=$(timeout 30 find "$dir" -type f \( -name "*copy*" -o -name "*duplicate*" -o -name "*(1)*" \) 2>/dev/null | wc -l | tr -d ' ' || echo "0")
			if ((dupes > 0)); then
				append "Potential duplicates in $dir: $dupes files"
			fi
		fi
	done
	append ""

	state_set_last_run "deep_cleaner_duplicates"
else
	append "=== DUPLICATE FILE ANALYSIS ==="
	append "Skipped - no changes since last run"
	append ""
fi

# 6) Old iOS backups and device syncs
MOBILE_BACKUP_DIR="${HOME}/Library/Application Support/MobileSync/Backup"
if any_modified "deep_cleaner_mobile_backups" "$MOBILE_BACKUP_DIR"; then
	append "=== MOBILE DEVICE BACKUPS ==="
	if [[ -d ${MOBILE_BACKUP_DIR} ]]; then
		backup_size=$(du -sh "${MOBILE_BACKUP_DIR}" 2>/dev/null | cut -f1)
		backup_count=$(find "${MOBILE_BACKUP_DIR}" -maxdepth 1 -type d 2>/dev/null | wc -l | tr -d ' ')
		append "iOS Backups: $backup_size in $backup_count backup sets"
		append "Location: ${MOBILE_BACKUP_DIR}"
	else
		append "No iOS backups found"
	fi
	append ""

	state_set_last_run "deep_cleaner_mobile_backups"
else
	append "=== MOBILE DEVICE BACKUPS ==="
	append "Skipped - no changes since last run"
	append ""
fi

# 7) Docker and VM images
VM_DIRS=(
	"${HOME}/Virtual Machines.localized"
	"${HOME}/Documents/Virtual Machines"
	"${HOME}/Library/Application Support/VMware Fusion"
	"${HOME}/.docker"
)
if any_modified "deep_cleaner_vms" "${VM_DIRS[@]}"; then
	append "=== DOCKER AND VIRTUAL MACHINE FILES ==="
	for vm_dir in "${VM_DIRS[@]}"; do
		if [[ -d $vm_dir ]]; then
			vm_size=$(du -sh "$vm_dir" 2>/dev/null | cut -f1)
			append "VM/Container files in $vm_dir: $vm_size"
		fi
	done
	append ""

	state_set_last_run "deep_cleaner_vms"
else
	append "=== DOCKER AND VIRTUAL MACHINE FILES ==="
	append "Skipped - no changes since last run"
	append ""
fi

# 8) Browser profile bloat
BROWSER_DIRS=(
	"${HOME}/Library/Application Support/Google/Chrome"
	"${HOME}/Library/Safari"
	"${HOME}/Library/Application Support/Firefox"
	"${HOME}/Library/Application Support/Microsoft Edge"
)
if any_modified "deep_cleaner_browser_profiles" "${BROWSER_DIRS[@]}"; then
	append "=== BROWSER PROFILE ANALYSIS ==="
	for browser_dir in "${BROWSER_DIRS[@]}"; do
		if [[ -d $browser_dir ]]; then
			browser_size=$(du -sh "$browser_dir" 2>/dev/null | cut -f1)
			# ⚡ Bolt Optimization: parameter expansion avoids 2 process spawns (dirname + basename)
			tmp="${browser_dir%/}" # Remove potential trailing slash
			parent_path="${tmp%/*}"
			browser_name="${parent_path##*/}"
			append "$browser_name profile: $browser_size"
		fi
	done
	append ""

	state_set_last_run "deep_cleaner_browser_profiles"
else
	append "=== BROWSER PROFILE ANALYSIS ==="
	append "Skipped - no changes since last run"
	append ""
fi

# 9) Development environment cleanup
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
if any_modified "deep_cleaner_dev_caches" "${DEV_CACHES[@]}"; then
	append "=== DEVELOPMENT ENVIRONMENT CLEANUP ==="
	for dev_cache in "${DEV_CACHES[@]}"; do
		if [[ -d $dev_cache ]]; then
			cache_size=$(du -sh "$dev_cache" 2>/dev/null | cut -f1)
			# ⚡ Bolt Optimization: parameter expansion avoids process spawning
			cache_name="${dev_cache##*/}"
			append "Development cache ($cache_name): $cache_size"
		fi
	done
	append ""

	state_set_last_run "deep_cleaner_dev_caches"
else
	append "=== DEVELOPMENT ENVIRONMENT CLEANUP ==="
	append "Skipped - no changes since last run"
	append ""
fi

# 10) Log file analysis
LOG_DIRS=(
	"${HOME}/Library/Logs"
	"/var/log"
	"/Library/Logs"
)
if any_modified "deep_cleaner_logs" "${LOG_DIRS[@]}"; then
	append "=== LOG FILE ANALYSIS ==="
	for log_dir in "${LOG_DIRS[@]}"; do
		if [[ -d $log_dir ]] && [[ -r $log_dir ]]; then
			log_size=$(du -sh "$log_dir" 2>/dev/null | cut -f1)
			old_logs=$(timeout 30 find "$log_dir" -name "*.log" -mtime +30 2>/dev/null | wc -l | tr -d ' ' || echo "0")
			append "$log_dir: $log_size ($old_logs files older than 30 days)"
		fi
	done
	append ""

	state_set_last_run "deep_cleaner_logs"
else
	append "=== LOG FILE ANALYSIS ==="
	append "Skipped - no changes since last run"
	append ""
fi

# 11) Mail attachments and downloads
MAIL_DOWNLOADS="${HOME}/Library/Mail/V*/MailData/Attachments"
MAIL_DIRS=()
while IFS= read -r mail_dir; do
	[[ -n $mail_dir ]] && MAIL_DIRS+=("$mail_dir")
done < <(compgen -G "$MAIL_DOWNLOADS" 2>/dev/null || true)
if any_modified "deep_cleaner_mail_attachments" "${MAIL_DIRS[@]}"; then
	append "=== MAIL ATTACHMENTS ==="
	# shellcheck disable=SC2086  # Intentional glob expansion for Mail V* directories
	if ls $MAIL_DOWNLOADS >/dev/null 2>&1; then
		# shellcheck disable=SC2086  # Intentional glob expansion for Mail V* directories
		mail_size=$(du -sh $MAIL_DOWNLOADS 2>/dev/null | cut -f1)
		append "Mail attachments: $mail_size"
	else
		append "No mail attachments found"
	fi
	append ""

	state_set_last_run "deep_cleaner_mail_attachments"
else
	append "=== MAIL ATTACHMENTS ==="
	append "Skipped - no changes since last run"
	append ""
fi

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
printf "%s\n" "${REPORT}" >"${REPORT_FILE}"

DISK_AFTER=$(percent_used "/")
append ""
append "Disk usage after analysis: ${DISK_AFTER}%"
append ""
append "📊 Report saved to: ${REPORT_FILE}"

log_info "Deep cleaning analysis complete"

# Notification
if command -v osascript >/dev/null 2>&1; then
	osascript -e 'on run argv' -e 'display notification (item 1 of argv) with title (item 2 of argv)' -e 'end run' -- "Analysis complete. Check report for cleanup recommendations." "Deep Cleaner" 2>/dev/null || true
fi

echo ""
echo "🎯 Next Steps:"
echo "1. Review the report above for specific recommendations"
echo "2. Manually verify any files before deleting them"
echo "3. Use the safe cleanup commands provided"
echo "4. Consider tools like:"
echo "   - Monolingual (for language files)"
echo "   - DupeGuru (for duplicate files)"
echo "   - Disk Utility First Aid (for filesystem issues)"

log_info "Deep system cleaning completed successfully"
echo "Deep cleaning analysis completed successfully!"
